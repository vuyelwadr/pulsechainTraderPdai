# 🚀 PDAI Trading Bot + Data/Optimization Pipeline (PulseChain)

An end‑to‑end stack for PDAI trading on PulseChain:
- Real on‑chain data collection from PulseX (no synthetic data)
- Walk‑forward (feed‑forward) strategy optimization on a unified 2‑year dataset
- Modular strategy system + backtester and demo live trading

## 🎯 Features

- **Demo Mode Trading**: Safe testing without real money
- **Backtesting Engine**: Test strategies on historical data (OOS‑led metrics)
- **Modular Strategy System**: Easy to add/modify trading strategies
- **Real-time HTML Reports**: Interactive web-based dashboards
- **CLI & Web Interface**: Both command-line and browser access
- **Moving Average Crossover**: Built-in trend-following strategy
- **PulseX Integration**: Direct integration with PulseX DEX
- **Walk‑Forward Optimization**: OOS‑led selection with profit‑first, drawdown‑aware scoring
- **Caching for Speed**: Persistent caches for block timestamps, Sync reserves, and swap events (coverage‑aware)

## 🧭 Real‑Data Policy (No Synthetic Data)

- All prices, volumes, reserves, and candles are derived strictly from on‑chain PulseX Swap/Sync events.
- If a candle has no Sync inside its interval, reserve columns stay NaN (no forward‑fill, no interpolation).
- Backtests use real prices; “demo mode” only simulates execution without spending real funds.

## 📋 Requirements

- Python 3.8+
- PulseChain RPC access
- Dependencies in `requirements.txt`

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download the project
cd pulsechainTraderPdai

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p data html_reports data/.cache logs
```

### 2. Configuration

The `.env` file is already set up for demo mode. No additional configuration needed for testing.

### 3. Collect Real OHLCV (strict on‑chain)

The collector builds 5‑minute candles from PulseX swaps and attaches strict inside‑candle reserves from Sync events.

```bash
# 2‑year, 5‑minute dataset (recommended unified source for the optimizer)
python collectors/swap_ohlcv_collector.py \
  --days 730 --interval 5m \
  --workers 6 --chunk-size 12000 \
  --pin-rpc-per-worker \
  --log-file logs/collector_2y.log \
  --out data/pdai_ohlcv_730day_5m.csv

# Quick 1‑day sanity check
python collectors/swap_ohlcv_collector.py --days 1 --interval 5m --workers 4 --chunk-size 20000
```

Output CSV columns (optimizer‑ready):
- `timestamp, open, high, low, close, volume, reserve_pdai, reserve_wpls, block`

Performance notes:
- Persistent caches under `data/.cache/block_ts.sqlite`:
  - `block_ts` (block → timestamp), `sync_reserves` (block → reserves), `swap_events` (decoded swaps), `coverage` (skip getLogs when range fully cached).
- Re‑running overlapping windows is much faster thanks to caches. All cached values are 100% real on‑chain.

### 4. Run Backtest

```bash
# Run 30-day backtest
python bot/pdai_trading_bot.py --backtest

# Custom backtest period
python bot/pdai_trading_bot.py --backtest --days 7

# Specific strategy
python bot/pdai_trading_bot.py --backtest --strategy MovingAverageCrossover
```

### 5. Live Trading (Demo Mode)

```bash
# Start live demo trading
python bot/pdai_trading_bot.py --live

# The bot will:
# - Fetch real PDAI price data
# - Generate trading signals
# - Execute simulated trades
# - Create real-time HTML reports
```

## 📊 Web Interface

When running backtests or live trading, HTML reports are automatically generated in the `html_reports/` directory:

- **Backtests**: `backtest_[strategy]_[timestamp].html`
- **Live Trading**: `live_trading.html` (auto-refreshes)

Open these files in your browser to see:
- Portfolio performance charts
- Trading signals and execution
- Performance metrics
- Real-time updates

## 🔧 Strategies

### Moving Average Crossover (Default)

The built-in strategy uses:
- **Short MA**: 10 periods (configurable)
- **Long MA**: 30 periods (configurable)
- **Signal Logic**: Buy when short MA crosses above long MA, sell when it crosses below

### Adding Custom Strategies

1. Create a new file in `strategies/` directory
2. Inherit from `BaseStrategy` class
3. Implement `calculate_indicators()` and `generate_signals()` methods
4. Add to bot in `pdai_trading_bot.py`

Example:
```python
from strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def calculate_indicators(self, data):
        # Your indicator calculations
        return data
    
    def generate_signals(self, data):
        # Your signal generation logic
        return data
```

## ⚙️ Configuration Options

Edit `.env` file to customize:

```bash
# Strategy Parameters
MA_SHORT_PERIOD=10        # Short moving average period
MA_LONG_PERIOD=30         # Long moving average period

# Trading Parameters
INITIAL_BALANCE=1000      # Starting balance in DAI
MAX_TRADE_AMOUNT_PCT=0.5  # Max % of balance per trade
SLIPPAGE_TOLERANCE=0.05   # 5% slippage tolerance

# Data Settings
BACKTEST_DAYS=30          # Default backtest period
DATA_FETCH_INTERVAL=60    # Price update interval (seconds)
```

## 📈 Understanding Results

### Backtest Metrics

- **Total Return**: Overall profit/loss percentage
- **Win Rate**: Percentage of profitable trades
- **Sharpe Ratio**: Risk-adjusted return (higher is better)
- **Max Drawdown**: Largest peak-to-trough decline
- **Profit Factor**: Ratio of gross profit to gross loss

### Signal Strength

All strategies return signal strength (0.0 to 1.0):
- **0.6+**: Execute trade
- **0.8+**: Strong signal
- **Below 0.6**: Hold position

## 🛡️ Safety Features

- **Demo Mode Only**: No real money at risk
- **Slippage Protection**: Built-in price impact simulation
- **Position Sizing**: Configurable trade amounts
- **Error Handling**: Robust error recovery
- **Data Validation**: Price and signal validation

## 🔍 Monitoring

### CLI Output
```
Price: 0.00001234 DAI, Signal: buy, Strength: 0.75
DEMO BUY: 4567.8901 PDAI at 0.00001234 DAI
```

### HTML Dashboard
- Real-time price updates
- Portfolio value tracking
- Trade execution history
- Strategy performance metrics

## 📁 Project Structure

```
pulsechainTraderPdai/
├── pdai_trading_bot.py      # Main bot class
├── config.py               # Configuration and constants
├── data_handler.py         # Price data management
├── backtest_engine.py      # Backtesting system
├── html_generator.py       # HTML report generation
├── strategies/
│   ├── base_strategy.py    # Strategy base class
│   └── ma_crossover.py     # Moving average strategy
├── data/                   # Collected data + caches
│   ├── pdai_ohlcv_730day_5m.csv         # Unified 2‑year 5m OHLCV (recommended source)
│   └── .cache/
│       └── block_ts.sqlite             # SQLite caches (block_ts, sync_reserves, swap_events, coverage)
├── src/
│   └── pipelines/
│       └── runner.py                   # Multi‑stage walk‑forward optimizer (OOS‑led)
├── scripts/
│   └── aggregate.py                    # Aggregator (CSV + MD leaderboards)
├── html_reports/           # Generated HTML reports
├── .env                    # Configuration file
└── requirements.txt        # Python dependencies
```

## 🎛️ Command Line Options (Bot)

```bash
# Backtest mode
python bot/pdai_trading_bot.py --backtest [--days N] [--strategy NAME]

# Live trading mode  
python bot/pdai_trading_bot.py --live [--demo]

# Status check
python bot/pdai_trading_bot.py

# Help
python bot/pdai_trading_bot.py --help
```

## 🧪 Optimization Pipeline (Walk‑Forward Defaults)

The optimizer always uses the unified 2‑year file. “Stage” controls how many winners to keep and report output paths — not the dataset.

- Timeframes (always): `5min, 15min, 30min, 1h, 4h, 8h, 16h, 1d`
- Objective (default): Utility `U = Return / (1 + λ · DD^p)` (profit‑led, drawdown‑aware)
- OOS‑led selection: mean OOS utility across walk‑forward folds

Walk‑forward per stage (recency‑biased windows):
- Stage 30d: last 90d window; folds train 45d → OOS 15d, step 15d
- Stage 90d: last 270d window; folds train 120d → OOS 30d, step 30d
- Stage 1y: last 365d window; folds train 180d → OOS 30d, step 30d

Run examples:
```bash
# Stage 90d: keep top 40 strategies by OOS score
python -m optimization.runner \
  --stage 90d --top-n2 40 \
  --strategies-file strategies_all.json \
  --workers 12 --calls 60

# Full 3‑stage run (top‑N per stage)
python -m optimization.runner \
  --top-n1 60 --top-n2 40 --top-n3 5 \
  --workers 12 --calls 60

# Gather all strategies and launch the full multi-objective marathon in background
python - <<'PY'
import json
from optimization.runner import collect_strategies
json.dump(collect_strategies(), open('strategies_all.json','w'))
PY

nohup python optimization/runner.py \
  --stage all \
  --strategies-file strategies_all.json \
  --calls 180 \
  --workers 0 \
  --objectives mar,utility,cps,profit_biased,cps_v2,cps_v2_profit_biased \
  --out-dir reports/full_optimizer_run \
  > logs/full_optimizer_run.log 2>&1 &

tail -f logs/full_optimizer_run.log   # monitor progress (Ctrl+C to stop tail)
```

Outputs under `reports/optimizer_pipeline_<ts>_[stage]/`:
- Per strategy/timeframe JSON: includes `folds` (IS/OOS ranges + scores), `selected_params`, final `score` (mean OOS utility)
- `stage_aggregate.csv`: objective‑aware columns (objective, score, utility, pdr, draws, trades)
- `stage_best.csv`: best timeframe per strategy
- `stage_report.md`: human‑readable leaderboards (Top by OOS score, Top by total return, Top by CPS for legacy)

Tip: `--calls` is per fold; runtime ≈ strategies × timeframes × folds × calls. Use lower calls (e.g., 10–30) for quick triage; increase for deeper stages.

## 📊 Token Information

- **PDAI Contract**: `0x2b591e99afE9f32eAA6214f7B7629768c40Eeb39`
- **WPLS Contract**: `0xA1077a294dDE1B09bB078844df40758a5D0f9a27`
- **DAI Contract**: `0xefD766cCb38EaF1dfd701853BFCe31359239F305`
- **PulseX Router**: `0x165C3410fC91EF562C50559f7d2289fEbed552d9`
- **Trading Route**: PDAI → WPLS → DAI (uses PDAI/WPLS + WPLS/DAI pools)

## ⚠️ Disclaimers

- **Educational Purpose**: This bot is for learning and testing only
- **Demo Mode**: No real trading occurs - all trades are simulated
- **No Guarantees**: Past performance doesn't predict future results
- **Risk Warning**: Cryptocurrency trading involves significant risk
- **DYOR**: Do your own research before any real trading

## 🐛 Troubleshooting

### Connection Issues
- Check RPC_URL in `.env`
- Verify internet connection
- Try alternative RPC endpoints

### Data Issues (Collector)
- NaN reserves: strict “inside‑candle only” means no Sync occurred in that 5m window (real‑only). This is expected for some candles.
- Re‑runs slow? The first run builds caches. Overlapping runs are much faster thanks to `data/.cache/block_ts.sqlite`.
- To rebuild fully: remove `data/.cache/` (will re‑fetch on‑chain data).

### Strategy Issues
- Review strategy parameters in `.env`
- Check minimum signal strength settings
- Validate indicator calculations

## 🧠 Notes & Future Enhancements

- OOS‑led selection aims for higher realized returns (lower drawdowns and better Calmar) than single‑window tuning.
- Optional next steps:
- Use reserves in backtests for real AMM impact (x·y=k) — the dataset now exposes `reserve_pdai` and `reserve_dai` columns.
  - Add strategy rotation (top‑3 OOS leaders) with a handover threshold to avoid churn.
  - Add Parquet caches for event/candle stores to shrink disk size further while keeping speed.
- [ ] API endpoints

---

**Happy Trading! 🎯**

Remember: This is demo mode only. Always test thoroughly before considering any real trading.




  Quick checklist

  - Dependencies: pip install scikit-optimize pandas numpy
  - Data: ensure data/pdai_ohlcv_30day_5m.csv exists (the runner will fall back to Config.resolve_ohlcv_path() if needed).
  - CPU: adjust --workers to your cores (defaults to 12).

  Run Stage 1 (30d only)

  - python -m optimization.runner --stage 30d --top-n1 60
  - Writes to reports/optimizer_pipeline_<timestamp>_30d/stage1_30d/
  - Selected strategies: stage1_30d/summary.json (key “top”)

  Run Stage 2 using Stage 1’s output

  - python -m optimization.runner --stage 90d --top-n2 20 --from-summary reports/optimizer_pipeline_<ts>_30d/stage1_30d/summary.json

  Notes

  - Uses full GP Bayesian optimizer + CPS scoring.
  - Tunes each strategy’s real parameters (strategy-specific ranges via the new registry).
  - Candlestick patterns are marked unused and won’t run.
  - You can customize: --timeframes 5min,15min,30min,1h,2h,4h,8h,16h,1d, --calls 80, --out-dir path.

  If you want, I can kick off the 30‑day run now or tune workers/calls for your machine.


(base) ruwodda@Vuyelwas-MacBook-Pro pulsechainTraderPdai % python collectors/swap_ohlcv_collector.py --days 365 --interval 5m --workers 6 --chunk-size 12000 --pin-rpc-per-worker --log-file logs/collector_1y_w6c12000pin.log --out data/pdai_ohlcv_365day_5m.csv
Connected. Pair: 0x19BB45a7270177e303DEe6eAA6F5Ad700812bA98
token0=0x2b591e99afE9f32eAA6214f7B7629768c40Eeb39 token1=0xA1077a294dDE1B09bB078844df40758a5D0f9a27
PDAI=0x2b591e99afE9f32eAA6214f7B7629768c40Eeb39 (dec 8), WPLS=0xA1077a294dDE1B09bB078844df40758a5D0f9a27 (dec 18)
Collecting swaps from 2024-09-13 01:18:47.042732+00:00 to 2025-09-13 01:18:47.042732+00:00 at interval 5m ...
Chunks: 5/258 | rows: 4,204 | elapsed: 0.8m | eta: 38.9m
Chunks: 10/258 | rows: 11,967 | elapsed: 1.8m | eta: 43.9m
Chunks: 15/258 | rows: 24,829 | elapsed: 2.9m | eta: 47.6m
Chunks: 20/258 | rows: 36,784 | elapsed: 4.0m | eta: 47.8m
Chunks: 25/258 | rows: 49,623 | elapsed: 4.7m | eta: 43.7m
Chunks: 30/258 | rows: 59,284 | elapsed: 5.7m | eta: 43.3m
Chunks: 35/258 | rows: 67,808 | elapsed: 6.6m | eta: 42.0m
Chunks: 40/258 | rows: 79,004 | elapsed: 7.6m | eta: 41.5m
Chunks: 45/258 | rows: 89,597 | elapsed: 8.8m | eta: 41.5m
Chunks: 50/258 | rows: 102,221 | elapsed: 9.8m | eta: 40.6m
Chunks: 55/258 | rows: 113,214 | elapsed: 10.4m | eta: 38.2m
Chunks: 60/258 | rows: 124,654 | elapsed: 11.8m | eta: 38.9m
Chunks: 65/258 | rows: 136,819 | elapsed: 13.3m | eta: 39.4m
Chunks: 70/258 | rows: 154,002 | elapsed: 14.9m | eta: 40.1m
Chunks: 75/258 | rows: 166,425 | elapsed: 16.1m | eta: 39.3m
Chunks: 80/258 | rows: 175,956 | elapsed: 17.1m | eta: 38.1m
Chunks: 85/258 | rows: 184,627 | elapsed: 17.2m | eta: 35.1m
Chunks: 90/258 | rows: 191,411 | elapsed: 18.1m | eta: 33.9m
Chunks: 95/258 | rows: 197,937 | elapsed: 18.8m | eta: 32.2m
Chunks: 100/258 | rows: 205,658 | elapsed: 19.8m | eta: 31.3m
Chunks: 105/258 | rows: 220,682 | elapsed: 21.7m | eta: 31.6m
Chunks: 110/258 | rows: 239,695 | elapsed: 23.2m | eta: 31.2m
Chunks: 115/258 | rows: 253,089 | elapsed: 23.9m | eta: 29.7m
Chunks: 120/258 | rows: 265,020 | elapsed: 24.7m | eta: 28.4m
Chunks: 125/258 | rows: 277,469 | elapsed: 25.8m | eta: 27.4m
Chunks: 130/258 | rows: 289,722 | elapsed: 27.0m | eta: 26.6m
Chunks: 135/258 | rows: 302,310 | elapsed: 28.7m | eta: 26.1m
Chunks: 140/258 | rows: 315,931 | elapsed: 29.9m | eta: 25.2m
Chunks: 145/258 | rows: 328,229 | elapsed: 30.7m | eta: 23.9m
Chunks: 150/258 | rows: 336,091 | elapsed: 31.6m | eta: 22.8m
Chunks: 155/258 | rows: 345,940 | elapsed: 32.8m | eta: 21.8m
Chunks: 160/258 | rows: 359,833 | elapsed: 34.0m | eta: 20.8m
Chunks: 165/258 | rows: 369,508 | elapsed: 35.3m | eta: 19.9m
Chunks: 170/258 | rows: 381,821 | elapsed: 36.4m | eta: 18.8m
Chunks: 175/258 | rows: 391,197 | elapsed: 37.5m | eta: 17.8m
Chunks: 180/258 | rows: 400,773 | elapsed: 37.9m | eta: 16.4m
Chunks: 185/258 | rows: 407,586 | elapsed: 38.6m | eta: 15.2m
Chunks: 190/258 | rows: 415,090 | elapsed: 39.3m | eta: 14.1m
Chunks: 195/258 | rows: 421,684 | elapsed: 40.0m | eta: 12.9m
Chunks: 200/258 | rows: 429,359 | elapsed: 40.7m | eta: 11.8m
Chunks: 205/258 | rows: 438,189 | elapsed: 41.4m | eta: 10.7m
Chunks: 210/258 | rows: 448,172 | elapsed: 42.6m | eta: 9.7m
Chunks: 215/258 | rows: 459,934 | elapsed: 43.6m | eta: 8.7m
Chunks: 220/258 | rows: 476,237 | elapsed: 45.2m | eta: 7.8m
Chunks: 225/258 | rows: 495,050 | elapsed: 47.5m | eta: 7.0m
Chunks: 230/258 | rows: 515,754 | elapsed: 49.2m | eta: 6.0m
Chunks: 235/258 | rows: 531,898 | elapsed: 49.8m | eta: 4.9m
Chunks: 240/258 | rows: 546,133 | elapsed: 51.8m | eta: 3.9m
Chunks: 245/258 | rows: 558,462 | elapsed: 52.8m | eta: 2.8m
Chunks: 250/258 | rows: 573,309 | elapsed: 54.1m | eta: 1.7m
Chunks: 255/258 | rows: 584,343 | elapsed: 55.3m | eta: 0.7m
Chunks: 258/258 | rows: 597,503 | elapsed: 56.2m | eta: 0.0m
/Users/ruwodda/Documents/Personal/Repos/trading/pulsechainTraderPdai/swap_ohlcv_collector.py:552: FutureWarning: 'T' is deprecated and will be removed in a future version, please use 'min' instead.
  o = df.resample(pandas_freq).agg(
Built 82395 candles in 3371.45s. Preview:
                                 open        high         low       close         volume
timestamp                                                                               
2024-09-13 01:20:00+00:00  136.649855  136.649855  136.649855  136.649855    2192.331754
2024-09-13 01:25:00+00:00  137.439985  137.439985  137.439985  137.439985    1873.500529
2024-09-13 01:30:00+00:00  137.612021  137.819346  137.099710  137.105371   12335.447394
2024-09-13 01:35:00+00:00  137.095340  137.095340  136.914768  136.914768    9448.781400
2024-09-13 01:40:00+00:00  136.746439  137.634388  136.600698  137.634388   27800.451684
2024-09-13 01:45:00+00:00  137.194320  137.194320  137.157790  137.157790    1980.153832
2024-09-13 01:50:00+00:00  137.115166  137.115166  137.115166  137.115166     365.108365
2024-09-13 01:55:00+00:00  137.094519  137.949219  137.094519  137.949219    2672.066697
2024-09-13 02:00:00+00:00  137.951714  137.951714  137.143609  137.143609     619.037951
2024-09-13 02:05:00+00:00  139.724240  139.724240  137.438814  137.438814  182336.490211
Saved OHLCV to data/pdai_ohlcv_365day_5m.csv
(base) ruwodda@Vuyelwas-MacBook-Pro pulsechainTraderPdai % 


 python -m optimization.aggregate reports/optimizer_pipeline_20250913_010816_90d/stage2_90d

 python -m optimization.runner --stage 1y --top-n3 1 --strategies-file top10.json --workers 12 --calls 80

 python -m optimization.runner --stage 90d --top-n2 20 --workers 12 --calls 80

 python -m optimization.runner --stage 90d --top-n2 20 --strategies-file strategies_all.json --workers 12 --calls 80
 python -m optimization.runner --stage 90d --top-n2 40 --strategies-file strategies_all.json --workers 12 --calls 10
 python -m optimization.runner --stage 30d --top-n2 40 --strategies-file strategies_all.json --workers 12 --calls 1



 python swap_ohlcv_collector.py --days 1 --interval 5m --workers 6 --chunk-size 12000 --pin-rpc-per-worker 



  Concrete Runs (only these two strategies)

  - Create a list file refined_strats.json:
      - ["GridTradingStrategy","DCAStrategy"]
  - Stage 1 (30d, CPS table filled for inspection)
      - python -m optimization.runner --stage 30d --objective cps --strategies-file refined_strats.json --workers 24 --calls 60
  - Stage 1 (30d, Utility for selection)
      - python -m optimization.runner --stage 30d --objective utility --strategies-file refined_strats.json --workers 24 --calls 60
  - Stage 2 (90d) and Stage 3 (1y) using Stage 1’s summary
      - python -m optimization.runner --stage 90d --objective utility --from-summary reports/optimizer_pipeline_<ts>_30d/stage1_30d/summary.json --workers 24 --calls 80
      - python -m optimization.runner --stage 1y  --objective utility --from-summary reports/optimizer_pipeline_<ts>_90d/stage2_90d/summary.json --workers 24 --calls 100
  - Re‑aggregate per stage for dashboards and CSVs
      - python -m optimization.aggregate reports/optimizer_pipeline_<ts>/stage1_30d
      - python -m optimization.aggregate reports/optimizer_pipeline_<ts>/stage2_90d
      - python -m optimization.aggregate reports/optimizer_pipeline_<ts>/stage3_1y


        How to run your request in one command

  - Put your shortlist in refined_strats.json (e.g., ["GridTradingStrategy","DCAStrategy","AdaptiveGridTrendStrategy","VolatilityTargetedDCAStrategy"]).
  - Then run all stages for all 3 objectives with 180 calls each:
      - python -m optimization.runner --stage all --strategies-file refined_strats.json --workers 16 --calls 180 --objectives "mar,utility,cps"
  - If you only want Stage 30d for all three objectives:
      - python -m optimization.runner --stage 30d --strategies-file refined_strats.json --workers 16 --calls 180 --objectives "mar,utility,cps"

python -m optimization.runner --stage all --strategies-file refined_strats.json --workers 16 --calls 180 --objectives "mar,utility,cps,profit_biased"

python -m optimization.runner --stage 30d --strategies-file refined_strats.json --workers 16 --calls 1 --objectives "mar,utility,cps,profit_biased"

 python -m optimization.runner --stage all --strategies-file refined_strats.json --workers 16 --calls 180 --objectives "mar,utility,cps,profit_biased"

-  python -m optimization.runner --stage all --strategies-file strategies_all.json --calls 180 --objectives "mar,utility,cps,profit_biased"


-  python -m optimization.runner --stage all --strategies-file top_strats.json --calls 240 --objectives "mar"python -m optimization.runner --stage all --strategies-file top_strats.json --calls 240 --objectives "mar"


 python collectors/swap_ohlcv_collector.py --days 1 --interval 8h --workers 6 --chunk-size 12000 --pin-rpc-per-worker --log-file logs/collector_1y_w6c12000pin.log --out data/pdai_ohlcv_tst.csv


  python scripts/top_strategy_backtest.py \
    --reports-dir reports \
    --data-path data/pdai_ohlcv_dai_730day_5m.csv \
    --max-backtests 300