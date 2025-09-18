"""Random-search based optimizer suitable for the pDAI stack."""
from __future__ import annotations

import json
import math
import random
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from pandas.tseries.frequencies import to_offset

from pdai_trader.config import Settings
from pdai_trader.optimization.scoring import SimpleStrategyScore
from pdai_trader.strategies.base_strategy import BaseStrategy
from pdai_trader.strategies.registry import list_registered_strategies, load_strategy_class
from pdai_trader.trading.backtest import BacktestEngine


@dataclass
class StrategySearchResult:
    """Container returned for every strategy/timeframe combination."""

    strategy_name: str
    timeframe: str
    trials: int
    best_parameters: Dict[str, Any]
    score: SimpleStrategyScore
    buy_hold_return_pct: float
    report_path: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["score"] = asdict(self.score)
        return payload


class StrategyOptimizer:
    """Run random-search optimisation across strategies and timeframes."""

    def __init__(
        self,
        data: pd.DataFrame,
        *,
        random_seed: Optional[int] = None,
        output_root: Path | None = None,
    ) -> None:
        if data.empty:
            raise ValueError("Optimizer requires a non-empty OHLCV dataframe")
        self.base_data = data.copy()
        self.base_data["timestamp"] = pd.to_datetime(self.base_data["timestamp"], utc=True)
        self.base_data = self.base_data.set_index("timestamp").sort_index()
        self.engine = BacktestEngine()
        self.rng = random.Random(random_seed or 0)
        if output_root:
            self.output_root = Path(output_root)
        else:
            self.output_root = Path("reports") / f"optimizer_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self.output_root = self.output_root.resolve()
        self.output_root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def optimise(
        self,
        *,
        strategies: Optional[Iterable[str]] = None,
        timeframes: Iterable[str] = ("5m", "15m", "1h"),
        trials: int = 25,
    ) -> List[StrategySearchResult]:
        results: List[StrategySearchResult] = []
        available = strategies or list_registered_strategies().keys()

        for strategy_name in available:
            strategy_cls = load_strategy_class(strategy_name)
            for timeframe in timeframes:
                outcome = self._optimise_single(strategy_cls, timeframe=timeframe, trials=trials)
                if outcome:
                    results.append(outcome)
        return results

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _optimise_single(
        self,
        strategy_cls: type[BaseStrategy],
        *,
        timeframe: str,
        trials: int,
    ) -> Optional[StrategySearchResult]:
        timeframe = timeframe.strip()
        resampled = self._resample_to_timeframe(timeframe)
        if resampled.empty:
            return None

        buy_hold_return = self._buy_hold_return(resampled)
        default_instance = strategy_cls()
        default_params = dict(getattr(default_instance, "parameters", {}) or {})
        param_space = strategy_cls.parameter_space()
        best_score: Optional[SimpleStrategyScore] = None
        best_params: Dict[str, Any] = {}

        max_window = max(len(resampled) - 2, 2)

        for _ in range(trials):
            candidate = self._sample_parameters(default_params, param_space)
            candidate = self._squeeze_period_like_parameters(candidate, max_window)
            strategy = strategy_cls(candidate)
            result = self.engine.run_backtest(strategy, resampled.reset_index())
            if result.get("error") and result["error"] != "No trades were executed":
                continue
            score = SimpleStrategyScore.from_backtest(
                total_return_pct=result.get("total_return_pct", 0.0),
                max_drawdown_pct=result.get("max_drawdown_pct", 0.0),
                sharpe_ratio=result.get("sharpe_ratio", 0.0),
                total_trades=result.get("total_trades", 0),
                duration_days=max(result.get("duration_days", 0), 1),
            )
            if not best_score or score.score > best_score.score:
                best_score = score
                best_params = candidate

        if not best_score:
            return None

        report_file = self._write_single_result(
            strategy_name=strategy_cls.__name__,
            timeframe=timeframe,
            parameters=best_params,
            score=best_score,
            buy_hold_return_pct=buy_hold_return,
        )

        return StrategySearchResult(
            strategy_name=strategy_cls.__name__,
            timeframe=timeframe,
            trials=trials,
            best_parameters=best_params,
            score=best_score,
            buy_hold_return_pct=round(buy_hold_return, 4),
            report_path=str(report_file) if report_file else None,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _resample_to_timeframe(self, timeframe: str) -> pd.DataFrame:
        try:
            offset = to_offset(self._normalise_timeframe(timeframe))
        except ValueError as exc:
            raise ValueError(f"Unsupported timeframe '{timeframe}': {exc}")

        grouped = self.base_data.resample(offset).agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "price": "last",
                "volume": "sum",
            }
        ).dropna(subset=["close"])
        grouped["price"] = grouped["price"].fillna(grouped["close"])
        grouped = grouped.reset_index()
        grouped.rename(columns={"index": "timestamp"}, inplace=True)
        return grouped

    def _buy_hold_return(self, df: pd.DataFrame) -> float:
        if df.empty:
            return 0.0
        start = float(df.iloc[0]["close"])
        end = float(df.iloc[-1]["close"])
        if start == 0:
            return 0.0
        return (end - start) / start * 100.0

    def _sample_parameters(self, defaults: Dict[str, Any], space: Dict[str, Tuple[Any, Any]]) -> Dict[str, Any]:
        candidate = dict(defaults)
        for key, bounds in (space or {}).items():
            lo, hi = bounds
            if isinstance(lo, bool) or isinstance(hi, bool):
                candidate[key] = self.rng.choice([False, True])
                continue
            if self._is_int_like(lo) and self._is_int_like(hi):
                candidate[key] = self.rng.randint(int(round(lo)), int(round(hi)))
            else:
                candidate[key] = self.rng.uniform(float(lo), float(hi))
        return candidate

    def _squeeze_period_like_parameters(self, params: Dict[str, Any], max_window: int) -> Dict[str, Any]:
        if max_window < 2:
            return params
        adjusted = dict(params)
        for key, value in params.items():
            if not isinstance(value, (int, float)):
                continue
            lowered = key.lower()
            if any(tok in lowered for tok in ("period", "window", "length")):
                adjusted[key] = int(max(2, min(int(round(value)), max_window)))
        return adjusted

    @staticmethod
    def _is_int_like(value: Any) -> bool:
        if isinstance(value, bool):
            return False
        if isinstance(value, int):
            return True
        if isinstance(value, float):
            return value.is_integer()
        return False

    @staticmethod
    def _normalise_timeframe(value: str) -> str:
        value = value.strip().lower()
        if value.endswith("min"):
            return value
        if value.endswith("m"):
            # pandas de-preferenced the bare "m" alias; normalise to minutes.
            return f"{value[:-1]}min"
        if value.endswith("h"):
            return value
        if value.endswith("d"):
            return value
        raise ValueError(f"Unrecognised timeframe '{value}'")

    def _write_single_result(
        self,
        *,
        strategy_name: str,
        timeframe: str,
        parameters: Dict[str, Any],
        score: SimpleStrategyScore,
        buy_hold_return_pct: float,
    ) -> Path:
        payload = {
            "strategy": strategy_name,
            "timeframe": timeframe,
            "parameters": parameters,
            "score": asdict(score),
            "buy_hold_return_pct": buy_hold_return_pct,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        file_path = self.output_root / f"{strategy_name}_{timeframe}.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(payload, indent=2))
        return file_path
