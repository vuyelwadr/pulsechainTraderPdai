#!/usr/bin/env python3
"""Convenience CLI for running a backtest using the pDAI trading bot stack."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from pdai_trader.config import Settings
from pdai_trader.strategies.ma_crossover import MovingAverageCrossover
from pdai_trader.trading.backtest import BacktestEngine


def load_default_dataset(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    if "price" not in frame and "close" in frame:
        frame["price"] = frame["close"]
    return frame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a simple pDAI backtest")
    parser.add_argument("--csv", type=Path, default=None, help="Optional OHLCV CSV override")
    parser.add_argument("--short", type=int, default=5, help="Short MA period")
    parser.add_argument("--long", type=int, default=13, help="Long MA period")
    parser.add_argument("--balance", type=float, default=float(Settings.INITIAL_BALANCE), help="Starting DAI balance")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    dataset_path = args.csv or Settings.resolve_ohlcv_path()
    if not dataset_path:
        dataset_path = Settings.DATA_DIR / "sample" / "pdai_ohlcv_sample.csv"

    frame = load_default_dataset(Path(dataset_path))
    engine = BacktestEngine(initial_balance=args.balance)
    strategy = MovingAverageCrossover({
        "short_period": args.short,
        "long_period": args.long,
        "min_strength": 0.0,
    })

    results = engine.run_backtest(strategy, frame)
    if "error" in results:
        print(f"Backtest error: {results['error']}")
        return

    print("Backtest complete")
    print(f"  Data points: {results['data_points']}")
    print(f"  Final balance: {results['final_balance']:.4f} DAI")
    print(f"  Total trades: {results['total_trades']}")


if __name__ == "__main__":
    main()
