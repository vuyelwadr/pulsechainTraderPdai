#!/usr/bin/env python3
"""Convenience CLI for running a backtest using the pDAI trading toolkit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Dict

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from pdai_trader.config import Settings
from pdai_trader.strategies.registry import list_registered_strategies, load_strategy_class
from pdai_trader.trading.backtest import BacktestEngine


def load_dataset(path: Path | None) -> pd.DataFrame:
    if path and path.exists():
        df = pd.read_csv(path)
    else:
        resolved = Settings.resolve_ohlcv_path()
        if resolved:
            df = pd.read_csv(resolved)
        else:
            fallback = Settings.DATA_DIR / "sample" / "pdai_ohlcv_sample.csv"
            df = pd.read_csv(fallback)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    if "price" not in df and "close" in df:
        df["price"] = df["close"]
    if "volume" not in df:
        df["volume"] = 0.0
    return df


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a backtest with an optional parameter override")
    parser.add_argument("--csv", type=Path, default=None, help="OHLCV CSV path (defaults to configured dataset)")
    parser.add_argument("--strategy", type=str, default="MovingAverageCrossover", help="Strategy name")
    parser.add_argument("--params-file", type=Path, help="JSON file containing parameter overrides")
    parser.add_argument(
        "--param",
        action="append",
        help="Inline parameter override in key=value form (repeatable)",
    )
    parser.add_argument("--balance", type=float, default=float(Settings.INITIAL_BALANCE), help="Starting DAI balance")
    return parser.parse_args()


def parse_inline_params(items) -> Dict[str, object]:
    overrides: Dict[str, object] = {}
    if not items:
        return overrides
    for item in items:
        if "=" not in item:
            raise ValueError(f"Invalid parameter override '{item}'. Use key=value format")
        key, value = item.split("=", 1)
        key = key.strip()
        overrides[key] = coerce_value(value.strip())
    return overrides


def coerce_value(raw: str):
    lowered = raw.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        return raw


def main() -> None:
    args = parse_args()
    dataset = load_dataset(args.csv)

    strategy_cls = load_strategy_class(args.strategy)
    defaults = dict(getattr(strategy_cls(), "parameters", {}) or {})

    if args.params_file:
        file_payload = json.loads(Path(args.params_file).read_text())
        if isinstance(file_payload, dict) and "parameters" in file_payload:
            defaults.update(file_payload["parameters"] or {})
        elif isinstance(file_payload, dict):
            defaults.update(file_payload)
        else:
            raise ValueError("Params file must be a JSON object")

    defaults.update(parse_inline_params(args.param))

    strategy = strategy_cls(defaults)
    engine = BacktestEngine(initial_balance=args.balance)
    result = engine.run_backtest(strategy, dataset)

    if result.get("error"):
        print(f"Backtest error: {result['error']}")
        return

    print("Backtest complete")
    print(f"  Strategy: {args.strategy}")
    print(f"  Data points: {result['data_points']}")
    print(f"  Final balance: {result['final_balance']:.4f} DAI")
    print(f"  Total return: {result['total_return_pct']:.2f}%")
    print(f"  Max drawdown: {result['max_drawdown_pct']:.2f}%")
    print(f"  Sharpe ratio: {result['sharpe_ratio']:.2f}")
    print(f"  Total trades: {result['total_trades']}")


if __name__ == "__main__":
    main()
