# PulseChain pDAI Trading Stack

Cleaner re-imagining of the original HEX trading toolkit, adapted for the pDAI ⇄ WPLS ⇄ DAI routing path on PulseChain.

## Highlights

- Modular package layout under `src/pdai_trader/` (data collection, trading core, strategies, reporting).
- Updated configuration for the pDAI token (`0x6B1754…d0F`) with WPLS/DAI bridge liquidity pools.
- Reused strategy catalogue with a simplified default (EMA crossover) ready to extend.
- Sample 1-day OHLCV dataset (`data/sample/pdai_ohlcv_sample.csv`) for quick smoke tests.
- CLI utilities for data collection and ad-hoc backtesting under `scripts/`.
- Pytest smoke tests that exercise the backtester five times on the 4-row sample dataset and verify 8h resampling.

## Project Layout

```
src/pdai_trader/
  config.py              # Central settings & token metadata
  data/
    collector.py         # On-chain PulseX swap ingestion (pDAI/WPLS routed to DAI)
    handler.py           # Price fetching & dataset management helpers
  reporting/html.py      # Lightweight HTML report builder (Bokeh-ready)
  strategies/            # Full strategy catalogue copied from HEX project
  trading/
    backtest.py          # Decimal-safe backtest engine
    bot.py               # CLI-friendly trading bot orchestration
  utils/rpc.py           # RPC load balancer reused from original stack
scripts/
  collect_pdai_ohlcv.py  # CLI for real OHLCV collection
  run_backtest.py        # Convenience backtest entry point
data/sample/pdai_ohlcv_sample.csv  # 4-row, ~1 day 8h cadence sample
```

## Quick Start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Optional: export RPC_URLS to override defaults in src/pdai_trader/config.py

# Smoke backtest on bundled sample data
python scripts/run_backtest.py

# Attempt a short 1-day / 8h OHLCV pull (writes to data/pdai_ohlcv_export.csv)
python scripts/collect_pdai_ohlcv.py --days 1 --interval 8H
```

## Running Tests

Tests rely on the bundled 4-row OHLCV sample; they do not hit live RPC endpoints.

```bash
pytest -q
```

The smoke suite performs:

1. Five consecutive runs of the `BacktestEngine` using the EMA crossover strategy to ensure deterministic outputs.
2. An 8-hour resample check of the sample dataset (matching the "1 day / 8h" sanity test request).

## Notes

- Real data collection still depends on live PulseChain RPC endpoints. Ensure the defaults in `Settings.RPC_URLS` are reachable or override with `RPC_URLS`.
- HTML generation keeps the same look-and-feel but with pDAI nomenclature and updated field names.
- Strategy JSON/catalogue files from the original project are preserved for continuity; they will operate on the new asset pair.
# pulsechainTraderPdai
