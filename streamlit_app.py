from __future__ import annotations

import os
import time

import pandas as pd
import streamlit as st

from app.data.indstocks_provider import INDStocksProvider
from app.data.live_provider import YahooLiveProvider
from app.data.universe import NSE_LIQUID
from app.market.context import global_snapshot, market_regime
from app.news.context import google_news, classify_headline
from app.scanners.scanner import rank_stock

st.set_page_config(page_title="Indian Stock Intelligence", page_icon="📈", layout="wide")
st.title("📈 Indian Stock Intelligence")
st.caption("Intraday + swing research dashboard | NSE/BSE-oriented | analytical signals, not guaranteed returns")

with st.sidebar:
    st.header("Scanner")
    mode = st.radio("Mode", ["Intraday", "Swing"])
    exchange = st.selectbox("Universe", ["NSE", "BSE", "NSE+BSE"], index=0)
    refresh = st.number_input("Refresh seconds", min_value=15, max_value=3600, value=60, step=15)
    max_stocks = st.slider("Stocks to scan", 5, 100, 25)
    auto = st.checkbox("Auto refresh", value=False)

    ind_token_configured = bool(os.getenv("INDSTOCKS_TOKEN"))
    if ind_token_configured:
        st.success("INDstocks live market data: configured")
    else:
        st.warning("INDSTOCKS_TOKEN not configured — using Yahoo research data")
        st.caption("Set INDSTOCKS_TOKEN in your local environment to use your INDstocks/INDmoney feed.")

provider_name = "INDstocks" if ind_token_configured else "Yahoo"
provider = INDStocksProvider() if ind_token_configured else YahooLiveProvider()


@st.cache_data(ttl=60, show_spinner=False)
def get_market(selected_provider: str):
    p = INDStocksProvider() if selected_provider == "INDstocks" else YahooLiveProvider()
    return global_snapshot(p)


@st.cache_data(ttl=300, show_spinner=False)
def get_universe(selected_provider: str, selected_exchange: str, limit: int):
    if selected_provider != "INDstocks":
        return NSE_LIQUID[:limit]
    p = INDStocksProvider()
    if selected_exchange == "NSE+BSE":
        half = max(5, limit // 2)
        return (p.top_liquid_symbols(half, "NSE") + p.top_liquid_symbols(limit - half, "BSE"))[:limit]
    return p.top_liquid_symbols(limit, selected_exchange)


@st.cache_data(ttl=45, show_spinner=False)
def scan(symbols, selected_mode, selected_provider):
    rows = []
    errors = []
    if selected_provider == "INDstocks":
        period = "7d" if selected_mode == "Intraday" else "1y"
        interval = "15minute" if selected_mode == "Intraday" else "1day"
        p = INDStocksProvider()
    else:
        period = "3mo" if selected_mode == "Intraday" else "1y"
        interval = "15m" if selected_mode == "Intraday" else "1d"
        p = YahooLiveProvider()

    for s in symbols:
        try:
            df = p.history(s, period=period, interval=interval)
            r = rank_stock(s, df, "intraday" if selected_mode == "Intraday" else "swing")
            if r:
                rows.append(r)
            else:
                errors.append(f"{s}: insufficient/no candles")
        except Exception as exc:
            errors.append(f"{s}: {type(exc).__name__}: {exc}")
    return pd.DataFrame(rows), errors


market = get_market(provider_name)
regime = market_regime(market)

c1, c2, c3 = st.columns(3)
c1.metric("Market regime", regime)
if not market.empty:
    nifty = market[market.name == "NIFTY 50"]
    vix = market[market.name == "INDIA VIX"]
    c2.metric("NIFTY 50", f"{nifty.price.iloc[0]:,.2f}" if len(nifty) else "—", f"{nifty.change_pct.iloc[0]:.2f}%" if len(nifty) else None)
    c3.metric("India VIX", f"{vix.price.iloc[0]:.2f}" if len(vix) else "—", f"{vix.change_pct.iloc[0]:.2f}%" if len(vix) else None)

st.subheader(f"{mode} scanner")
symbols = get_universe(provider_name, exchange, max_stocks)
results, scan_errors = scan(tuple(symbols), mode, provider_name)
if results.empty:
    st.warning("No candidates returned. Check the diagnostics below for provider errors.")
    if scan_errors:
        with st.expander("Scanner diagnostics", expanded=True):
            st.code("\n".join(scan_errors[:12]))
else:
    buys = results[results.signal == "BUY"].sort_values("score", ascending=False)
    sells = results[results.signal == "SELL"].sort_values("score")
    watches = results[results.signal == "WATCH"].sort_values("score", ascending=False)
    a, b, c = st.columns(3)
    a.metric("BUY", len(buys))
    b.metric("SELL", len(sells))
    c.metric("WATCH", len(watches))
    st.dataframe(results.sort_values("score", ascending=False), use_container_width=True, hide_index=True)
    if scan_errors:
        with st.expander(f"Skipped symbols ({len(scan_errors)})"):
            st.code("\n".join(scan_errors[:30]))

st.subheader("🌎 Global market context")
if market.empty:
    st.info("Market context unavailable right now. Stock scanning uses the configured market-data provider independently.")
else:
    st.dataframe(market.sort_values("change_pct", ascending=False), use_container_width=True, hide_index=True)

st.subheader("📰 Global / Indian news")
news = google_news("India stock market NSE sectors global markets", 12)
if news:
    st.dataframe(
        pd.DataFrame([{**n, "impact": classify_headline(n["title"])} for n in news])[["published", "impact", "title", "link"]],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("News feed unavailable right now.")

st.subheader("⚠️ Risk controls")
st.write("Signals are ranked research outputs. Validate liquidity, spread, corporate actions, news and execution conditions before trading. Never treat the score as a guarantee.")

if auto:
    time.sleep(refresh)
    st.rerun()
