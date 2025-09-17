# PulseChain pDAI Trading Stack

End-to-end trading toolkit for PulseChain’s synthetic DAI (pDAI) routed through the liquid WPLS/DAI bridge pools. The stack mirrors the original HEX project but reorganised for clarity and equipped with a minimal optimisation pipeline so you can go from data collection → parameter tuning → backtesting with a single repository.

---

## 1. Features At A Glance

- **Modular package layout** under `src/pdai_trader/` (config, data ingestion, optimisation, strategies, reporting, trading).
- **Updated on-chain configuration** for the pDAI → WPLS → DAI route (token addresses, pool contracts, router ABI).
- **Collector CLI** that builds real OHLCV candles from PulseX swap events without synthetic padding.
- **Random-search optimiser** with JSON report output for reusable best-parameter snapshots.
- **Backtest CLI** that can ingest optimizer reports or inline overrides.
- **Sample dataset & smoke tests** to validate the toolchain offline (four 8‑hour candles covering a 1‑day sanity window).
- **Compatibility registry** so strategies copied from the HEX project continue to import via legacy paths.

---

## 2. Requirements

- Python **3.10+** (developed on 3.11).
- `pip` for dependency installation (`requirements.txt`).
- Access to at least one healthy PulseChain RPC endpoint for real data collection (public defaults are provided).

Optional (recommended):

- `python -m venv .venv` virtual environment to isolate dependencies.
- `jq` or similar JSON viewer for reading optimisation outputs.

---

## 3. Installation & Environment Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Optional: tailor runtime configuration
export RPC_URL="https://rpc.pulsechain.com"
export RPC_URLS="https://rpc.pulsechainrpc.com,https://pulsechain-rpc.publicnode.com"
```

Key environment variables (`src/pdai_trader/config.py`):

| Variable | Description | Default |
|----------|-------------|---------|
| `RPC_URL` | Primary RPC endpoint used by synchronous calls | `https://rpc.pulsechain.com` |
| `RPC_URLS` | Comma-separated list for the load balancer | curated public RPC list |
| `PDAI_ADDRESS` | pDAI token address | `0x6B175474E89094C44Da98b954EedeAC495271d0F` |
| `PDAI_WPLS_POOL` | PulseX pDAI/WPLS pool | `0xaE8429918FdBF9a5867e3243697637Dc56aa76A1` |
| `DAI_WPLS_POOL` | PulseX WPLS/DAI pool for routing | `0xE56043671df55dE5CDf8459710433C10324DE0aE` |
| `DEMO_MODE` | Toggle live-trading execution in the bot | `true` |

Feel free to persist overrides in a `.env` file – `dotenv` is loaded automatically on import.

---

## 4. Repository Structure

```
src/pdai_trader/
  config.py                    # Central settings & token metadata
  data/
    collector.py               # On-chain PulseX swap ingestion (pDAI/WPLS routed to DAI)
    handler.py                 # Dataset management & fallback cache logic
  optimization/
    __init__.py
    scoring.py                 # Composite score container
    search.py                  # Random-search optimiser producing JSON reports
  reporting/html.py            # Bokeh-ready HTML report generator (unchanged look & feel)
  strategies/
    registry.py                # Curated mapping for strategy imports
    ...                        # Full strategy catalogue copied from HEX project
  trading/
    backtest.py                # Decimal-safe, fee-aware backtest engine
    bot.py                     # CLI-friendly trading bot orchestration (live/demo)
  utils/rpc.py                 # RPC load balancer shared across components
scripts/
  collect_pdai_ohlcv.py        # Data collector CLI
  run_optimizer.py             # Optimiser CLI (random search)
  run_backtest.py              # Backtest CLI (supports optimizer outputs)
data/sample/pdai_ohlcv_sample.csv  # 4-row sample dataset (1 day, 8h cadence)
requirements.txt
pytest.ini                     # Ensures `src/` is on `PYTHONPATH`
```

---

## 5. Workflow: Collect → Optimise → Backtest

### 5.1 Collect real OHLCV data

```bash
# 1-day scrape aggregated into 5-minute candles (writes CSV + cache)
python scripts/collect_pdai_ohlcv.py \
  --days 1 \
  --interval 5m \
  --volume-asset pDAI \
  --out data/pdai_ohlcv_1d_5m.csv

# Switch to 8-hour candles for quick smoke runs
python scripts/collect_pdai_ohlcv.py --days 1 --interval 8H
```

**Outputs**

- CSV at the path you provide (`--out`, default `data/pdai_ohlcv_export.csv`).
- Cache entries under `data/.cache/` (block timestamps, WPLS/DAI quotes, swap coverage) so subsequent runs accelerate.

### 5.2 Optimise strategy parameters

```bash
python scripts/run_optimizer.py \
  --csv data/pdai_ohlcv_1d_5m.csv \
  --strategies MovingAverageCrossover,BollingerBandsStrategy \
  --timeframes 5m,15m,1h \
  --trials 40 \
  --seed 1337

# Output:
# Optimizer completed. Summary: reports/optimizer_YYYYmmdd_HHMMSS/summary.json
#  - MovingAverageCrossover @ 5m: score=... | trades=... | params={...}
```

Each `{strategy}_{timeframe}.json` file contains the selected parameter set, score breakdown, and buy‑and‑hold reference. Re-run with more trials or different timeframes using the same CSV to iterate quickly.

### 5.3 Backtest with chosen parameters

```bash
# Using a report produced by the optimiser
python scripts/run_backtest.py \
  --csv data/pdai_ohlcv_1d_5m.csv \
  --strategy MovingAverageCrossover \
  --params-file reports/optimizer_YYYYmmdd_HHMMSS/MovingAverageCrossover_5m.json

# Ad hoc override (no optimiser file needed)
python scripts/run_backtest.py \
  --strategy MovingAverageCrossover \
  --param short_period=8 --param long_period=21 --param min_strength=0.4

# Basic run on the bundled sample dataset
python scripts/run_backtest.py
```

Outputs include final balance, total return, drawdown, and Sharpe ratio printed to stdout. For HTML visualisations, wire the results into `pdai_trader.reporting.html.HTMLGenerator`, which mirrors the HEX project capability.

---

## 6. Additional Capabilities

- **Live/Demo trading loop** – `pdai_trader/trading/bot.py` retains the original architecture. Run `python -m pdai_trader.trading.bot --live` (demo only) after configuring RPC access.
- **Strategy catalogue** – All prior HEX strategies are included; the compatibility registry allows existing manifest files to continue referencing `strategies.*` imports.
- **Extensibility** – Drop new strategies under `src/pdai_trader/strategies/custom/` and register them via `register_strategy()` to include them in optimiser runs.

---

## 7. Testing & Verification

```bash
python -m pytest -q
```

The smoke suite covers:

1. Deterministic backtest execution (five consecutive runs on the sample dataset).
2. 8-hour resampling sanity check (ensures collector output aggregates cleanly).
3. Mini optimiser execution to confirm score generation and report files.

---

## 8. Troubleshooting & Tips

| Issue | Likely Cause | Suggested Fix |
|-------|--------------|---------------|
| `RPC` timeouts during collection | Public endpoints throttling | Set `RPC_URLS` to private endpoints or reduce the `--interval` window size |
| Optimiser produces `No trades were executed` | Dataset too short for sampled MA periods | Increase trials, adjust bounds (see `StrategyOptimizer._squeeze_period_like_parameters`), or supply longer CSV |
| Backtest complains about missing `price` column | CSV lacks `price` values | Ensure collector output is used (it writes both `close` & `price`) |
| HTML report missing | Bokeh not installed or HTML directory unwritable | `pip install bokeh` and confirm write permissions |

**Pro tip:** version-control the generated `reports/optimizer_*` directory when you discover a parameter set you want to reuse in production.

---

## 9. Next Steps

- Swap in longer historical windows (e.g., `--days 30`) to begin walk-forward tests.
- Add new strategies to `registry.py` and benchmark them via the optimiser.
- Integrate optimiser outputs into your deployment scripts for automated strategy rotation.

Happy trading!
