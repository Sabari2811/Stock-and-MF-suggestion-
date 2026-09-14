from __future__ import annotations

import pandas as pd

from app.signals.engine import SignalEngine
from app.technical.indicators import atr, ema, rsi, vwap


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    x["ema9"] = ema(x["close"], 9)
    x["ema21"] = ema(x["close"], 21)
    x["rsi"] = rsi(x["close"], 14)
    x["atr"] = atr(x, 14)
    x["vwap"] = vwap(x)
    x["vol_avg"] = x["volume"].rolling(20).mean()
    x["rel_volume"] = x["volume"] / x["vol_avg"]
    x["ret_20"] = x["close"].pct_change(20) * 100
    x["high_20"] = x["high"].rolling(20).max().shift(1)
    x["low_20"] = x["low"].rolling(20).min().shift(1)
    return x


def rank_stock(symbol: str, df: pd.DataFrame, mode: str = "intraday") -> dict | None:
    if df.empty or len(df) < 30:
        return None
    x = enrich(df).dropna()
    if x.empty:
        return None
    last = x.iloc[-1]
    prev = x.iloc[-2]
    momentum = float(max(-1, min(1, last.ret_20 / 15)))
    trend = 1.0 if last.close > last.ema9 > last.ema21 else (-1.0 if last.close < last.ema9 < last.ema21 else 0.0)
    volume = float(max(-1, min(1, (last.rel_volume - 1) / 2)))
    vwap_bias = 1.0 if last.close > last.vwap else -1.0
    breakout = 1.0 if last.close > last.high_20 else (-1.0 if last.close < last.low_20 else 0.0)
    rsi_bias = 0.0 if 45 <= last.rsi <= 65 else (1.0 if last.rsi > 65 else -1.0)
    if mode == "intraday":
        score = 50 + 18*trend + 12*volume + 10*vwap_bias + 7*breakout + 3*rsi_bias
    else:
        score = 50 + 25*trend + 10*volume + 10*momentum + 8*breakout + 2*rsi_bias
    score = max(0, min(100, score))
    side = "BUY" if score >= 70 else "SELL" if score <= 30 else "WATCH"
    price, a = float(last.close), float(last.atr)
    if side == "BUY":
        entry_low, entry_high = price * .997, price * 1.003
        sl = price - 1.5*a
        t1, t2 = price + 2*a, price + 3*a
    elif side == "SELL":
        entry_low, entry_high = price * .997, price * 1.003
        sl = price + 1.5*a
        t1, t2 = price - 2*a, price - 3*a
    else:
        entry_low = entry_high = sl = t1 = t2 = None
    return {"symbol": symbol, "mode": mode, "signal": side, "score": round(score,1),
            "price": round(price,2), "entry_low": round(entry_low,2) if entry_low else None,
            "entry_high": round(entry_high,2) if entry_high else None, "sl": round(sl,2) if sl else None,
            "target1": round(t1,2) if t1 else None, "target2": round(t2,2) if t2 else None,
            "rsi": round(float(last.rsi),1), "rel_volume": round(float(last.rel_volume),2),
            "trend": round(trend,1), "vwap_bias": round(vwap_bias,1), "breakout": round(breakout,1)}
