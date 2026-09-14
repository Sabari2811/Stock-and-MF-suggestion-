from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.models import Timeframe
from app.data.demo_provider import DemoContextProvider, DemoMarketProvider
from app.signals.engine import generate_signal

app = FastAPI(title="Stock Intelligence Engine", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

market = DemoMarketProvider()
context_provider = DemoContextProvider()


@app.get("/health")
def health():
    return {"status": "ok", "service": "stock-intelligence"}


@app.get("/api/v1/market/context")
def market_context():
    return context_provider.get_context()


@app.get("/api/v1/market/sectors")
def sectors():
    return list(context_provider.get_sectors())


@app.get("/api/v1/signals/{timeframe}")
def signals(timeframe: Timeframe, exchange: str = "NSE"):
    context = context_provider.get_context()
    snapshots = market.get_snapshots(market.list_symbols(exchange), exchange, timeframe.value)
    results = [generate_signal(s, context, timeframe) for s in snapshots]
    return sorted(results, key=lambda x: x.score, reverse=True)


@app.get("/")
def root():
    return {
        "name": "Stock Intelligence Engine",
        "phase": "Phase 1 - Stocks",
        "endpoints": [
            "/health",
            "/api/v1/market/context",
            "/api/v1/market/sectors",
            "/api/v1/signals/INTRADAY",
            "/api/v1/signals/SWING",
        ],
    }
