from __future__ import annotations

import yfinance as yf
import pandas as pd

from app.data.universe import GLOBAL


def global_snapshot() -> pd.DataFrame:
    rows = []
    for ticker, name in GLOBAL.items():
        try:
            h = yf.download(ticker, period="5d", interval="1d", auto_adjust=False, progress=False)
            if isinstance(h.columns, pd.MultiIndex): h.columns = h.columns.get_level_values(0)
            h = h.dropna()
            if len(h) >= 2:
                p, q = float(h.close.iloc[-1]), float(h.close.iloc[-2])
                rows.append({"name": name, "ticker": ticker, "price": p, "change_pct": (p/q-1)*100})
        except Exception:
            continue
    return pd.DataFrame(rows)


def market_regime(snapshot: pd.DataFrame) -> str:
    if snapshot.empty or "NIFTY 50" not in set(snapshot.name): return "UNKNOWN"
    n = snapshot[snapshot.name == "NIFTY 50"].iloc[0].change_pct
    return "BULLISH" if n > 0.5 else "BEARISH" if n < -0.5 else "NEUTRAL"
