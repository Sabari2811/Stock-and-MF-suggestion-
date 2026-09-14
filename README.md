# Stock & MF Suggestion Engine

A modular Indian equity intelligence application for NSE/BSE stock scanning, intraday and swing setups, market/sector context, risk-defined signals, news context, backtesting, and later mutual-fund portfolio management.

## Phase 1

This repository currently starts from an empty base and Phase 1 focuses on stocks only:

- Intraday scanner
- Swing scanner
- Market regime
- Sector strength
- Liquidity / volume ranking
- Technical setup detection
- Risk/reward and entry/SL/target engine
- News/global-market context provider layer
- Signal scoring
- Paper/live-monitoring dashboard foundation
- Testable provider architecture

Mutual-fund portfolio management is intentionally reserved for a later phase.

## Architecture

```text
app/
  api/            API routes and application services
  core/           configuration and shared models
  data/           provider interfaces and market data adapters
  market/         market regime and index context
  sectors/        sector ranking and rotation
  news/           news/event provider interfaces
  technical/      indicators and price-structure analytics
  signals/        intraday/swing signal engines
  risk/           position sizing, stop and target calculations
  scanners/       universe filtering and ranking
  backtest/       replay and evaluation framework
  dashboard/      dashboard models/UI entrypoint
  tests/          automated tests

infra/             deployment and environment templates
scripts/           local development scripts
```

## Principle

The engine is designed to be selective. `NO_TRADE` is a first-class outcome; the system must not manufacture signals when market, setup, or risk conditions are weak.

## Disclaimer

Signals are analytical outputs, not guaranteed investment advice or returns. Live data quality, execution, slippage, latency, and provider limits materially affect results.
