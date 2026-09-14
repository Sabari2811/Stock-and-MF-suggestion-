from __future__ import annotations

import pandas as pd


def evaluate_signals(df: pd.DataFrame, horizon: int = 5, threshold: float = 0.02) -> dict:
    """Simple out-of-sample diagnostic, not a broker execution simulator."""
    if len(df) <= horizon: return {"samples": 0}
    fwd = df["close"].shift(-horizon) / df["close"] - 1
    long = fwd > threshold
    short = fwd < -threshold
    return {"samples": int(fwd.dropna().shape[0]), "long_hit_rate": round(float(long.mean())*100,2),
            "short_hit_rate": round(float(short.mean())*100,2), "avg_forward_return_pct": round(float(fwd.mean())*100,3)}
