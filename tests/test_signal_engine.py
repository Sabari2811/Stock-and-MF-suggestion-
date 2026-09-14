from app.core.models import GlobalContext, MarketRegime, StockSnapshot, Timeframe, SignalAction
from app.signals.engine import generate_signal


def snapshot():
    return StockSnapshot(
        symbol="TEST",
        exchange="NSE",
        price=100,
        volume=2_000_000,
        avg_volume=1_000_000,
        vwap=99,
        ema9=101,
        ema21=99,
        rsi14=62,
        atr14=1.2,
        sector_score=80,
        relative_strength=75,
        news_score=15,
    )


def test_bullish_intraday_generates_buy():
    context = GlobalContext(regime=MarketRegime.BULLISH)
    signal = generate_signal(snapshot(), context, Timeframe.INTRADAY)
    assert signal.action == SignalAction.BUY
    assert signal.score >= 70
    assert signal.risk.stop_loss < 100
    assert signal.risk.target_1 > 100


def test_high_risk_regime_blocks_trade():
    context = GlobalContext(regime=MarketRegime.HIGH_RISK)
    signal = generate_signal(snapshot(), context, Timeframe.INTRADAY)
    assert signal.action == SignalAction.NO_TRADE
