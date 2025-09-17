#!/usr/bin/env python3
"""Run random-search optimisation across registered strategies."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Iterable

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from pdai_trader.config import Settings
from pdai_trader.optimization import StrategyOptimizer
from pdai_trader.strategies.registry import list_registered_strategies


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Optimise pDAI strategies via random search")
    parser.add_argument("--csv", type=Path, default=None, help="OHLCV CSV path")
    parser.add_argument(
        "--timeframes", type=str, default="5m,15m,1h",
        help="Comma-separated list of timeframes (e.g. 5m,15m,1h,4h)"
    )
    parser.add_argument(
        "--strategies", type=str, default=None,
        help="Comma-separated strategy names. Defaults to all registered strategies."
    )
    parser.add_argument("--trials", type=int, default=25, help="Random trials per strategy/timeframe")
    parser.add_argument("--seed", type=int, default=0, help="Random seed for reproducibility")
    parser.add_argument("--out", type=Path, default=None, help="Optional output directory for reports")
    return parser.parse_args()


def load_dataset(path: Path | None) -> pd.DataFrame:
    if path and path.exists():
        return pd.read_csv(path)

    resolved = Settings.resolve_ohlcv_path()
    if resolved:
        return pd.read_csv(resolved)

    fallback = Settings.DATA_DIR / "sample" / "pdai_ohlcv_sample.csv"
    if fallback.exists():
        return pd.read_csv(fallback)

    raise FileNotFoundError(
        "No OHLCV dataset located. Provide --csv or drop a file in data/"
    )


def normalise_list(value: str | None) -> Iterable[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> None:
    args = parse_args()
    frame = load_dataset(args.csv)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)

    strat_names = list_registered_strategies().keys()
    if args.strategies:
        supplied = normalise_list(args.strategies)
        strat_names = supplied

    timeframes = normalise_list(args.timeframes)
    if not timeframes:
        timeframes = ["5m"]

    optimizer = StrategyOptimizer(frame, random_seed=args.seed, output_root=args.out)
    results = optimizer.optimise(strategies=strat_names, timeframes=timeframes, trials=args.trials)

    summary = {
        "generated_at": optimizer.output_root.name,
        "results": [item.to_dict() for item in results],
        "report_root": str(optimizer.output_root),
    }
    summary_path = optimizer.output_root / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))

    print(f"Optimizer completed. Summary: {summary_path}")
    for result in results:
        print(
            f" - {result.strategy_name} @ {result.timeframe}: score={result.score.score:.2f}"
            f" | trades={result.score.total_trades} | params={result.best_parameters}"
        )


if __name__ == "__main__":
    main()
