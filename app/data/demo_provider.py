from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from app.core.models import GlobalContext, MarketRegime, SectorSnapshot, StockSnapshot


class DemoMarketProvider:
    """Deterministic provider used for local development before live APIs are configured."""

    symbols = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "SBIN", "TATASTEEL"]

    def list_symbols(self, exchange: str) -> Sequence[str]:
        return self.symbols

    def get_snapshots(self, symbols: Sequence[str], exchange: str, timeframe: str) -> Sequence[StockSnapshot]:
        base = {
            "RELIANCE": 1420,
            "HDFCBANK": 980,
            "ICICIBANK": 1450,
            "INFY": 1650,
            "TCS": 3100,
            "SBIN": 890,
            "TATASTEEL": 180,
        }
        sector = {
            "RELIANCE": ("Energy", 76),
            "HDFCBANK": ("Banks", 71),
            "ICICIBANK": ("Banks", 79),
            "INFY": ("IT", 64),
            "TCS": ("IT", 61),
            "SBIN": ("Banks", 73),
            "TATASTEEL": ("Metals", 43),
        }
        out: list[StockSnapshot] = []
        for symbol in symbols:
            price = float(base.get(symbol, 100))
            sec, sec_score = sector.get(symbol, ("Other", 50))
            out.append(
                StockSnapshot(
                    symbol=symbol,
                    exchange=exchange,
                    price=price,
                    previous_close=price * 0.992,
                    volume=2_000_000,
                    avg_volume=1_000_000,
                    high=price * 1.015,
                    low=price * 0.985,
                    vwap=price * 0.998,
                    ema9=price * 1.003,
                    ema21=price * 0.997,
                    rsi14=62,
                    atr14=price * 0.012,
                    sector=sec,
                    sector_score=sec_score,
                    market_score=70,
                    relative_strength=72,
                    news_score=10,
                )
            )
        return out


class DemoContextProvider:
    def get_context(self) -> GlobalContext:
        return GlobalContext(
            nifty_change_pct=0.35,
            banknifty_change_pct=0.55,
            india_vix=13.8,
            us_market_bias=0.4,
            asia_market_bias=0.2,
            crude_bias=-0.1,
            usd_inr_bias=0.0,
            news_bias=0.15,
            regime=MarketRegime.BULLISH,
        )

    def get_sectors(self) -> Sequence[SectorSnapshot]:
        return [
            SectorSnapshot(sector="Banks", score=79, change_pct=0.8, volume_ratio=1.5),
            SectorSnapshot(sector="Energy", score=76, change_pct=0.6, volume_ratio=1.4),
            SectorSnapshot(sector="Metals", score=43, change_pct=-0.7, volume_ratio=1.2),
        ]
