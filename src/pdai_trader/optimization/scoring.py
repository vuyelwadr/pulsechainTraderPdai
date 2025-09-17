"""Lightweight scoring for backtest results."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimpleStrategyScore:
    """Encapsulates score components for easy JSON serialisation."""

    score: float
    total_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    total_trades: int
    trade_frequency_pm: float

    @classmethod
    def from_backtest(cls, *, total_return_pct: float, max_drawdown_pct: float,
                      sharpe_ratio: float, total_trades: int, duration_days: float) -> "SimpleStrategyScore":
        """Compute a composite score from backtest aggregates."""
        safe_duration = max(duration_days, 1.0)
        trade_frequency = total_trades / (safe_duration / 30.0)

        # Composite: reward return, reward risk-adjusted, penalise drawdown, penalise inactivity.
        score = (
            total_return_pct
            + sharpe_ratio * 15.0
            - max_drawdown_pct * 0.7
            + min(trade_frequency, 20.0)  # cap trade activity bonus
        )

        if total_trades == 0:
            score -= 25.0

        return cls(
            score=round(score, 4),
            total_return_pct=round(total_return_pct, 4),
            max_drawdown_pct=round(max_drawdown_pct, 4),
            sharpe_ratio=round(sharpe_ratio, 4),
            total_trades=int(total_trades),
            trade_frequency_pm=round(trade_frequency, 4),
        )
