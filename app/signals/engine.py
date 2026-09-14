from __future__ import annotations

from datetime import datetime, timezone

from app.core.models import GlobalContext, MarketRegime, RiskPlan, Signal, SignalAction, StockSnapshot, Timeframe


def _market_factor(context: GlobalContext) -> float:
    if context.regime == MarketRegime.BULLISH:
        return 80
    if context.regime == MarketRegime.BEARISH:
        return 25
    if context.regime == MarketRegime.HIGH_RISK:
        return 35
    return 50


def _technical_score(s: StockSnapshot) -> float:
    score = 50.0
    if s.price > (s.vwap or s.price):
        score += 10
    else:
        score -= 10
    if s.ema9 is not None and s.ema21 is not None:
        score += 10 if s.ema9 > s.ema21 else -10
    if s.rsi14 is not None:
        if 55 <= s.rsi14 <= 72:
            score += 10
        elif s.rsi14 > 78:
            score -= 5
        elif s.rsi14 < 40:
            score -= 10
    if s.avg_volume and s.volume > s.avg_volume * 1.5:
        score += 10
    return max(0, min(100, score))


def _risk_plan(s: StockSnapshot, side: SignalAction) -> RiskPlan:
    atr = s.atr14 or max(s.price * 0.01, 0.01)
    if side in (SignalAction.BUY, SignalAction.ACCUMULATE):
        sl = s.price - 1.25 * atr
        return RiskPlan(
            entry_low=s.price - 0.25 * atr,
            entry_high=s.price + 0.10 * atr,
            stop_loss=sl,
            target_1=s.price + 1.5 * atr,
            target_2=s.price + 2.5 * atr,
            risk_reward=2.0,
        )
    if side == SignalAction.SELL:
        sl = s.price + 1.25 * atr
        return RiskPlan(
            entry_low=s.price - 0.10 * atr,
            entry_high=s.price + 0.25 * atr,
            stop_loss=sl,
            target_1=s.price - 1.5 * atr,
            target_2=s.price - 2.5 * atr,
            risk_reward=2.0,
        )
    return RiskPlan()


def generate_signal(snapshot: StockSnapshot, context: GlobalContext, timeframe: Timeframe) -> Signal:
    tech = _technical_score(snapshot)
    market = _market_factor(context)
    raw = (
        0.30 * tech
        + 0.20 * snapshot.sector_score
        + 0.15 * snapshot.relative_strength
        + 0.15 * market
        + 0.10 * (50 + snapshot.news_score)
        + 0.10 * (100 if snapshot.avg_volume and snapshot.volume > snapshot.avg_volume else 50)
    )
    score = max(0, min(100, raw))

    bullish = tech >= 65 and snapshot.sector_score >= 60 and snapshot.relative_strength >= 55
    bearish = tech <= 35 and snapshot.sector_score <= 45 and snapshot.relative_strength <= 45

    if context.regime == MarketRegime.HIGH_RISK:
        action = SignalAction.NO_TRADE
        reasons = ["High-risk market regime: no fresh directional trade unless confirmation improves."]
    elif timeframe == Timeframe.INTRADAY and bullish and score >= 70:
        action = SignalAction.BUY
        reasons = ["Intraday momentum setup passes the composite score threshold."]
    elif timeframe == Timeframe.INTRADAY and bearish and score <= 40:
        action = SignalAction.SELL
        reasons = ["Intraday downside setup passes the composite score threshold."]
    elif timeframe == Timeframe.SWING and bullish and score >= 72:
        action = SignalAction.ACCUMULATE if score < 82 else SignalAction.BUY
        reasons = ["Swing trend/sector/relative-strength setup is constructive."]
    elif timeframe == Timeframe.SWING and bearish and score <= 38:
        action = SignalAction.SELL
        reasons = ["Swing trend and relative-strength conditions are weak."]
    else:
        action = SignalAction.WATCH
        reasons = ["Setup is not strong enough for a fresh trade; wait for confirmation."]

    if snapshot.vwap is not None:
        reasons.append("VWAP relationship included in technical score.")
    if snapshot.avg_volume and snapshot.volume > snapshot.avg_volume * 1.5:
        reasons.append("Relative volume expansion detected.")
    if snapshot.sector_score >= 70:
        reasons.append("Sector strength is supportive.")
    if snapshot.news_score > 20:
        reasons.append("News context is positive.")
    elif snapshot.news_score < -20:
        reasons.append("News context is negative.")

    risk = _risk_plan(snapshot, action)
    return Signal(
        symbol=snapshot.symbol,
        exchange=snapshot.exchange,
        timeframe=timeframe,
        action=action,
        score=round(score, 2),
        confidence=round(max(0, min(100, score * 0.9)), 2),
        risk=risk,
        reasons=reasons,
        invalidation=["Invalidate if price breaks the defined stop-loss or setup assumptions materially change."],
        generated_at=datetime.now(timezone.utc),
    )
