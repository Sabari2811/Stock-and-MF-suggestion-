from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field


class SignalAction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    ACCUMULATE = "ACCUMULATE"
    WATCH = "WATCH"
    NO_TRADE = "NO_TRADE"


class Timeframe(StrEnum):
    INTRADAY = "INTRADAY"
    SWING = "SWING"


class MarketRegime(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    HIGH_RISK = "HIGH_RISK"


class Quote(BaseModel):
    symbol: str
    exchange: str
    last_price: float
    volume: float = 0
    traded_value: float = 0
    timestamp: datetime


class StockSnapshot(BaseModel):
    symbol: str
    exchange: str
    price: float
    previous_close: float | None = None
    volume: float = 0
    avg_volume: float | None = None
    high: float | None = None
    low: float | None = None
    vwap: float | None = None
    ema9: float | None = None
    ema21: float | None = None
    rsi14: float | None = None
    atr14: float | None = None
    sector: str | None = None
    sector_score: float = 50
    market_score: float = 50
    relative_strength: float = 50
    news_score: float = 0


class RiskPlan(BaseModel):
    entry_low: float | None = None
    entry_high: float | None = None
    stop_loss: float | None = None
    target_1: float | None = None
    target_2: float | None = None
    risk_reward: float | None = None


class Signal(BaseModel):
    symbol: str
    exchange: str
    timeframe: Timeframe
    action: SignalAction
    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=100)
    risk: RiskPlan = RiskPlan()
    reasons: list[str] = Field(default_factory=list)
    invalidation: list[str] = Field(default_factory=list)
    generated_at: datetime


class GlobalContext(BaseModel):
    nifty_change_pct: float = 0
    banknifty_change_pct: float = 0
    india_vix: float | None = None
    us_market_bias: float = 0
    asia_market_bias: float = 0
    crude_bias: float = 0
    usd_inr_bias: float = 0
    news_bias: float = 0
    regime: MarketRegime = MarketRegime.NEUTRAL


class SectorSnapshot(BaseModel):
    sector: str
    score: float = Field(ge=0, le=100)
    change_pct: float = 0
    volume_ratio: float = 1
    news_bias: float = 0
