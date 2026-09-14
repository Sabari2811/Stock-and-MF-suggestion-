from __future__ import annotations

import io
import os
from datetime import datetime, timedelta, timezone
from typing import Iterable

import pandas as pd
import requests

BASE_URL = "https://api.indstocks.com"
# The API documents support for up to 1000 quote instruments, but very large
# query strings can exceed HTTP/server URL limits. Keep REST quote batches
# deliberately small so the dynamic universe works reliably on Windows and
# through proxies as well.
QUOTE_BATCH_SIZE = 100


class INDStocksProvider:
    """INDstocks/INDmoney market-data adapter."""

    def __init__(self, token: str | None = None, timeout: int = 20):
        self.token = token or os.getenv("INDSTOCKS_TOKEN")
        self.timeout = timeout
        if not self.token:
            raise RuntimeError("INDSTOCKS_TOKEN is not configured")
        self._instruments: pd.DataFrame | None = None
        self._index_instruments: pd.DataFrame | None = None

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
        for col in ("EXCH", "TRADING_SYMBOL", "SECURITY_ID", "SYMBOL_NAME", "SERIES"):
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str).str.strip()
        self._instruments = df
        return df

    def index_instruments(self) -> pd.DataFrame:
        """Load the three-column INDstocks index master."""
        if self._index_instruments is not None:
            return self._index_instruments
        response = self._get("/market/instruments", {"source": "index"})
        df = pd.read_csv(io.BytesIO(response.content), dtype=str)
        if len(df.columns) < 3:
            raise RuntimeError("Unexpected INDstocks index master format")
        df = df.iloc[:, :3].copy()
        df.columns = ["EXCH", "INDEX_NAME", "SECURITY_ID"]
        for col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
        self._index_instruments = df
        return df

    def resolve_symbol(self, symbol: str) -> tuple[str, str, str]:
        exchange = "BSE" if symbol.upper().endswith(".BO") else "NSE"
        base = symbol.rsplit(".", 1)[0].upper()
        df = self.instruments()
        rows = df[df["EXCH"].str.upper() == exchange]
        match = rows[rows["TRADING_SYMBOL"].str.upper() == base]
        if match.empty and "SYMBOL_NAME" in rows.columns:
            match = rows[rows["SYMBOL_NAME"].str.upper() == base]
        if match.empty:
            raise KeyError(f"Instrument not found: {exchange}:{base}")
        security_id = str(match.iloc[0]["SECURITY_ID"])
        return exchange, security_id, f"{exchange}_{security_id}"

    def equity_symbols(self, exchange: str = "NSE") -> list[str]:
        """Build the equity universe from the live provider master."""
        df = self.instruments()
        rows = df[df["EXCH"].str.upper() == exchange.upper()].copy()
        if "SERIES" in rows.columns:
            rows = rows[rows["SERIES"].str.upper().eq("EQ")]
        rows = rows[rows["TRADING_SYMBOL"].str.len() > 0]
        return [
            f"{s}.{exchange.upper()}"
            for s in rows["TRADING_SYMBOL"].drop_duplicates().tolist()
        ]

    def quote_many(self, symbols: Iterable[str]) -> pd.DataFrame:
        """Fetch full quotes in URL-safe batches.

        INDstocks documents a maximum of 1000 instruments for this endpoint,
        but sending hundreds/thousands of identifiers in one GET request can
        exceed the practical URL limit of a local proxy/server. Batching at
        100 keeps the request comfortably below those limits.
        """
        resolved = []
        for symbol in symbols:
            try:
                exchange, security_id, code = self.resolve_symbol(symbol)
                resolved.append((symbol, exchange, security_id, code))
            except Exception:
                continue

        rows: list[dict] = []
        for start in range(0, len(resolved), QUOTE_BATCH_SIZE):
            batch = resolved[start : start + QUOTE_BATCH_SIZE]
            codes = ",".join(item[3] for item in batch)
            payload = self._get(
                "/market/quotes/full", {"scrip-codes": codes}
            ).json()
            data = payload.get("data", {}) or {}
            for symbol, exchange, security_id, code in batch:
                q = data.get(code, {}) or {}
                price = float(q.get("live_price") or 0)
                volume = float(q.get("volume") or 0)
                rows.append(
                    {
                        "symbol": symbol,
                        "exchange": exchange,
                        "security_id": security_id,
                        "price": price,
                        "volume": volume,
                        "traded_value": price * volume,
                        "change_pct": float(q.get("day_change_percentage") or 0),
                    }
                )
        return pd.DataFrame(rows)

    def top_liquid_symbols(self, limit: int = 100, exchange: str = "NSE") -> list[str]:
        """Rank the live equity universe by traded value."""
        quotes = self.quote_many(self.equity_symbols(exchange))
        if quotes.empty:
            return []
        quotes = quotes[quotes["price"] > 0]
        return (
            quotes.sort_values(
                ["traded_value", "change_pct"], ascending=[False, False]
            )
            .head(limit)["symbol"]
            .tolist()
        )

    @staticmethod
    def _window(interval: str) -> tuple[datetime, datetime]:
        now = datetime.now(timezone.utc)
        days = 7 if interval not in {"1day", "1week", "1month"} else 365
        return now - timedelta(days=days), now

    def history(self, symbol: str, period: str = "6mo", interval: str = "1day") -> pd.DataFrame:
        valid = {
            "1minute", "2minute", "3minute", "4minute", "5minute",
            "10minute", "15minute", "30minute", "60minute", "120minute",
            "180minute", "240minute", "1day", "1week", "1month",
        }
        if interval not in valid:
            raise ValueError(f"Unsupported INDstocks interval: {interval}")
        _, _, scrip_code = self.resolve_symbol(symbol)
        start, end = self._window(interval)
        payload = self._get(
            f"/market/historical/{interval}",
            {
                "scrip-codes": scrip_code,
                "start_time": int(start.timestamp() * 1000),
                "end_time": int(end.timestamp() * 1000),
            },
        ).json()
        candles = payload.get("data", {}).get(scrip_code, {}).get("candles") or []
        if not candles:
            return pd.DataFrame()
        df = pd.DataFrame(candles).rename(
            columns={
                "ts": "timestamp",
                "o": "open",
                "h": "high",
                "l": "low",
                "c": "close",
                "v": "volume",
            }
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return (
            df.set_index("timestamp")[["open", "high", "low", "close", "volume"]]
            .dropna(subset=["close"])
        )

    def quote(self, symbol: str) -> dict:
        quotes = self.quote_many([symbol])
        return quotes.iloc[0].to_dict() if not quotes.empty else {}

    def index_snapshot(
        self, names: Iterable[str] = ("NIFTY 50", "NIFTY BANK", "INDIA VIX")
    ) -> pd.DataFrame:
        """Fetch current Indian index values using the INDstocks index master."""
        master = self.index_instruments()
        wanted = {n.upper(): n for n in names}
        matches = master[master["INDEX_NAME"].str.upper().isin(wanted)]
        if matches.empty:
            return pd.DataFrame()
        codes = ",".join(f"{r.EXCH}_{r.SECURITY_ID}" for r in matches.itertuples())
        payload = self._get("/market/quotes/full", {"scrip-codes": codes}).json()
        rows = []
        for r in matches.itertuples():
            code = f"{r.EXCH}_{r.SECURITY_ID}"
            q = payload.get("data", {}).get(code, {}) or {}
            if q:
                rows.append(
                    {
                        "name": wanted.get(
                            str(r.INDEX_NAME).upper(), str(r.INDEX_NAME)
                        ),
                        "ticker": code,
                        "price": float(q.get("live_price") or 0),
                        "change_pct": float(q.get("day_change_percentage") or 0),
                    }
                )
        return pd.DataFrame(rows)

    def scan(
        self, symbols: Iterable[str], period: str = "3mo", interval: str = "1day"
    ) -> dict[str, pd.DataFrame]:
        return {s: self.history(s, period=period, interval=interval) for s in symbols}
