from __future__ import annotations

import pandas as pd
import yfinance as yf

from app.data.universe import GLOBAL


def _yahoo_snapshot() -> pd.DataFrame:
    rows = []
    for ticker, name in GLOBAL.items():
        try:
            h = yf.download(ticker, period="5d", interval="1d", auto_adjust=False, progress=False)
            if isinstance(h.columns, pd.MultiIndex):
                h.columns = h.columns.get_level_values(0)
            h = h.dropna()
            if len(h) >= 2:
                p, q = float(h.close.iloc[-1]), float(h.close.iloc[-2])
                rows.append({"name": name, "ticker": ticker, "price": p, "change_pct": (p / q - 1) * 100})
        except Exception:
            continue
    return pd.DataFrame(rows)


def global_snapshot(provider=None) -> pd.DataFrame:
    """Combine provider-native Indian indices with optional global Yahoo data."""
    rows = []
    if provider is not None and hasattr(provider, "index_snapshot"):
        try:
            indian = provider.index_snapshot()
            if not indian.empty:
                rows.extend(indian.to_dict("records"))
        except Exception:
            pass

    yahoo = _yahoo_snapshot()
    if not yahoo.empty:
        existing = {r["name"] for r in rows}
        rows.extend(r for r in yahoo.to_dict("records") if r["name"] not in existing)
    return pd.DataFrame(rows)


def market_regime(snapshot: pd.DataFrame) -> str:
    if snapshot.empty or "NIFTY 50" not in set(snapshot.name):
        return "UNKNOWN"
    n = float(snapshot[snapshot.name == "NIFTY 50"].iloc[0].change_pct)
    return "BULLISH" if n > 0.5 else "BEARISH" if n < -0.5 else "NEUTRAL"
