from __future__ import annotations

import io
import os
from datetime import datetime, timedelta, timezone
from typing import Iterable

import pandas as pd
import requests

BASE_URL = "https://api.indstocks.com"


class INDStocksProvider:
    """INDstocks/INDmoney market-data adapter.

    The access token is read only from the local INDSTOCKS_TOKEN environment
    variable. It is never stored in the repository or exposed by the UI.
    """

    def __init__(self, token: str | None = None, timeout: int = 20):
        self.token = token or os.getenv("INDSTOCKS_TOKEN")
        self.timeout = timeout
        if not self.token:
            raise RuntimeError("INDSTOCKS_TOKEN is not configured")
        self._instruments: pd.DataFrame | None = None

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": self.token, "Accept": "application/json"}

    def _get(self, path: str, params: dict | None = None) -> requests.Response:
        response = requests.get(
            f"{BASE_URL}{path}",
            headers=self.headers,
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response

    def instruments(self) -> pd.DataFrame:
        if self._instruments is not None:
            return self._instruments
        response = self._get("/market/instruments", {"source": "equity"})
        df = pd.read_csv(io.BytesIO(response.content), dtype=str)
        for col in ("EXCH", "TRADING_SYMBOL", "SECURITY_ID", "SYMBOL_NAME"):
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str).str.strip()
        self._instruments = df
        return df

    def resolve_symbol(self, symbol: str) -> tuple[str, str, str]:
        """Return exchange, security id and scrip-code for an NSE/BSE symbol."""
        exchange = "BSE" if symbol.upper().endswith(".BO") else "NSE"
        base = symbol.rsplit(".", 1)[0].upper()
        df = self.instruments()
        rows = df[(df["EXCH"].str.upper() == exchange)]
        match = rows[rows["TRADING_SYMBOL"].str.upper() == base]
        if match.empty and "SYMBOL_NAME" in rows.columns:
            match = rows[rows["SYMBOL_NAME"].str.upper() == base]
        if match.empty:
            raise KeyError(f"Instrument not found: {exchange}:{base}")
        security_id = str(match.iloc[0]["SECURITY_ID"])
        return exchange, security_id, f"{exchange}_{security_id}"

    @staticmethod
    def _window(interval: str) -> tuple[datetime, datetime]:
        now = datetime.now(timezone.utc)
        days = 7 if interval != "1day" else 365
        return now - timedelta(days=days), now

    def history(self, symbol: str, period: str = "6mo", interval: str = "1day") -> pd.DataFrame:
        # INDstocks limits each intraday request to 7 days and daily requests to 1 year.
        if interval not in {"1minute", "2minute", "3minute", "4minute", "5minute", "10minute", "15minute", "30minute", "60minute", "120minute", "180minute", "240minute", "1day", "1week", "1month"}:
            raise ValueError(f"Unsupported INDstocks interval: {interval}")
        _, _, scrip_code = self.resolve_symbol(symbol)
        start, end = self._window(interval)
        params = {
            "scrip-codes": scrip_code,
            "start_time": int(start.timestamp() * 1000),
            "end_time": int(end.timestamp() * 1000),
        }
        payload = self._get(f"/market/historical/{interval}", params).json()
        candles = payload.get("data", {}).get(scrip_code, {}).get("candles") or []
        if not candles:
            return pd.DataFrame()
        df = pd.DataFrame(candles).rename(columns={"ts": "timestamp", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df.set_index("timestamp")[["open", "high", "low", "close", "volume"]].dropna(subset=["close"])

    def quote(self, symbol: str) -> dict:
        _, _, scrip_code = self.resolve_symbol(symbol)
        payload = self._get("/market/quotes/full", {"scrip-codes": scrip_code}).json()
        data = payload.get("data", {}).get(scrip_code, {})
        return {
            "symbol": symbol,
            "price": float(data.get("live_price") or 0),
            "change_pct": float(data.get("day_change_percentage") or 0),
            "volume": float(data.get("volume") or 0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def scan(self, symbols: Iterable[str], period: str = "3mo", interval: str = "1day") -> dict[str, pd.DataFrame]:
        return {s: self.history(s, period=period, interval=interval) for s in symbols}
