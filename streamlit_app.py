from __future__ import annotations

import time
import pandas as pd
import streamlit as st

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
    refresh = st.number_input("Refresh seconds", min_value=15, max_value=3600, value=60, step=15)
    max_stocks = st.slider("Stocks to scan", 5, len(NSE_LIQUID), min(25, len(NSE_LIQUID)))
    auto = st.checkbox("Auto refresh", value=False)
    st.info("Public Yahoo data is suitable for research/monitoring. Replace the provider with your broker feed for execution-grade live data.")

provider = YahooLiveProvider()

@st.cache_data(ttl=45, show_spinner=False)
def get_market():
    return global_snapshot()

@st.cache_data(ttl=45, show_spinner=False)
def scan(symbols, selected_mode):
    rows=[]
    period = "3mo" if selected_mode == "Intraday" else "1y"
    interval = "15m" if selected_mode == "Intraday" else "1d"
    for s in symbols:
        try:
            df=provider.history(s, period=period, interval=interval)
            r=rank_stock(s, df, "intraday" if selected_mode=="Intraday" else "swing")
            if r: rows.append(r)
        except Exception:
            continue
    return pd.DataFrame(rows)

market = get_market()
regime = market_regime(market)

c1,c2,c3 = st.columns(3)
c1.metric("Market regime", regime)
if not market.empty:
    nifty = market[market.name=="NIFTY 50"]
    vix = market[market.name=="INDIA VIX"]
    c2.metric("NIFTY 50", f"{nifty.price.iloc[0]:,.2f}" if len(nifty) else "—", f"{nifty.change_pct.iloc[0]:.2f}%" if len(nifty) else None)
    c3.metric("India VIX", f"{vix.price.iloc[0]:.2f}" if len(vix) else "—", f"{vix.change_pct.iloc[0]:.2f}%" if len(vix) else None)

st.subheader(f"{mode} scanner")
results = scan(tuple(NSE_LIQUID[:max_stocks]), mode)
if results.empty:
    st.warning("No candidates returned. Check internet connectivity/data availability.")
else:
    buys = results[results.signal=="BUY"].sort_values("score", ascending=False)
    sells = results[results.signal=="SELL"].sort_values("score")
    watches = results[results.signal=="WATCH"].sort_values("score", ascending=False)
    a,b,c = st.columns(3)
    a.metric("BUY", len(buys)); b.metric("SELL", len(sells)); c.metric("WATCH", len(watches))
    st.dataframe(results.sort_values("score", ascending=False), use_container_width=True, hide_index=True)

st.subheader("🌎 Global market context")
if market.empty: st.info("Global snapshot unavailable right now.")
else: st.dataframe(market.sort_values("change_pct", ascending=False), use_container_width=True, hide_index=True)

st.subheader("📰 Global / Indian news")
news = google_news("India stock market NSE sectors global markets", 12)
if news:
    st.dataframe(pd.DataFrame([{**n, "impact": classify_headline(n["title"])} for n in news])[['published','impact','title','link']], use_container_width=True, hide_index=True)
else: st.info("News feed unavailable right now.")

st.subheader("⚠️ Risk controls")
st.write("Signals are ranked research outputs. Validate liquidity, spread, corporate actions, news and execution conditions before trading. Never treat the score as a guarantee.")

if auto:
    time.sleep(refresh)
    st.rerun()
