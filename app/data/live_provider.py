from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

import pandas as pd
import yfinance as yf


class YahooLiveProvider:
    """Public Yahoo Finance adapter for research/local monitoring.

    Symbols use Yahoo Finance suffixes: .NS for NSE and .BO for BSE.
    The provider is isolated so a licensed broker/vendor feed can replace it.
    """

    def history(self, symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
        df = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False)
        if df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df.rename(columns={c: c.lower() for c in df.columns})

    def quote(self, symbol: str) -> dict:
        ticker = yf.Ticker(symbol)
        try:
            info = ticker.fast_info
            price = float(info.get("last_price") or 0)
            prev = float(info.get("previous_close") or 0)
        except Exception:
            hist = self.history(symbol, period="5d", interval="1d")
            if hist.empty:
                return {"symbol": symbol, "price": 0.0, "change_pct": 0.0}
            price = float(hist["close"].iloc[-1])
            prev = float(hist["close"].iloc[-2]) if len(hist) > 1 else price
        return {
            "symbol": symbol,
            "price": price,
            "change_pct": ((price / prev) - 1) * 100 if prev else 0.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def scan(self, symbols: Iterable[str], period: str = "3mo", interval: str = "1d") -> dict[str, pd.DataFrame]:
        return {s: self.history(s, period=period, interval=interval) for s in symbols}
