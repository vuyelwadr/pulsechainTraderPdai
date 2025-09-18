"""Aggregation helpers for optimisation runs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from .search import StrategySearchResult


def _results_to_dataframe(results: Sequence[StrategySearchResult]) -> pd.DataFrame:
    rows = []
    for res in results:
        rows.append(
            {
                "strategy": res.strategy_name,
                "timeframe": res.timeframe,
                "trials": res.trials,
                "score": res.score.score,
                "total_return_pct": res.score.total_return_pct,
                "max_drawdown_pct": res.score.max_drawdown_pct,
                "sharpe_ratio": res.score.sharpe_ratio,
                "total_trades": res.score.total_trades,
                "trade_frequency_pm": res.score.trade_frequency_pm,
                "buy_hold_return_pct": res.buy_hold_return_pct,
                "parameters": json.dumps(res.best_parameters, sort_keys=True),
                "report_path": res.report_path or "",
            }
        )
    return pd.DataFrame(rows)


def write_run_artifacts(results: Sequence[StrategySearchResult], run_dir: Path) -> None:
    """Persist CSV summaries for a single optimiser run."""

    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    if not results:
        return

    df = _results_to_dataframe(results)
    if df.empty:
        return

    df_sorted = df.sort_values(by="score", ascending=False, na_position="last")
    df_sorted.to_csv(run_dir / "run_results.csv", index=False)

    # Pick best configuration per strategy across all tested timeframes
    best = df_sorted.sort_values(by="score", ascending=False, na_position="last")
    best = best.groupby("strategy", as_index=False).first()
    best.to_csv(run_dir / "run_best_per_strategy.csv", index=False)


def update_global_aggregate(reports_root: Path) -> Path | None:
    """Rebuild the top-level report aggregate across all runs."""

    reports_root = Path(reports_root)
    reports_root.mkdir(parents=True, exist_ok=True)

    rows: list[pd.DataFrame] = []
    for run_dir in sorted(p for p in reports_root.iterdir() if p.is_dir()):
        csv_path = run_dir / "run_results.csv"
        if not csv_path.exists():
            continue
        df = pd.read_csv(csv_path)
        df.insert(0, "run_dir", run_dir.name)
        rows.append(df)

    if not rows:
        return None

    combo = pd.concat(rows, ignore_index=True)
    if "score" in combo.columns:
        combo = combo.sort_values(by="score", ascending=False, na_position="last")

    out_path = reports_root / "report_aggregate.csv"
    combo.to_csv(out_path, index=False)
    return out_path
