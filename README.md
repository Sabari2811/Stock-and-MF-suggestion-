# Indian Stock Intelligence

NSE/BSE-oriented stock research and monitoring application. Mutual-fund portfolio management is intentionally excluded from this phase.

## Included
- Streamlit live-monitoring dashboard
- Intraday and swing scanners
- BUY / SELL / WATCH signals and NO-TRADE-safe architecture
- Entry zone, stop-loss and two targets
- VWAP, EMA9/EMA21, RSI, ATR, relative volume and breakout logic
- Liquid-stock starter universe
- Global market snapshot (US, Asia, crude, gold, USD/INR)
- Google News RSS context and basic headline classification
- Replaceable data-provider architecture for broker/API integration
- FastAPI foundation
- Signal evaluation diagnostics
- Automated tests and GitHub Actions CI

## Run locally (Windows PowerShell)
```powershell
git clone https://github.com/Sabari2811/Stock-and-MF-suggestion-.git
cd Stock-and-MF-suggestion-
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Then open **http://localhost:8501**.

## Data note
The default adapter uses Yahoo Finance public data and Google News RSS for research/monitoring. Public feeds are not execution-grade. For broker-grade real-time NSE/BSE quotes, candles, volume and order-book data, implement a provider adapter using an authorized market-data/broker API and its credentials; the signal/scanner layers do not need to change.

## Validation
```powershell
pytest -q
```

The application does not claim guaranteed or “perfect” trades. It ranks evidence and can return WATCH/no-trade when conditions are weak. Validate live data quality, spread, latency, slippage, corporate actions and costs before using signals for real money.

## Scope
This phase is **stocks only**. Mutual-fund portfolio management will be added separately after the stock engine is validated.
