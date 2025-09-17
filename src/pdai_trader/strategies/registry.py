"""Strategy registry and helpers for dynamic loading."""
from __future__ import annotations

import importlib
from typing import Dict, Type

from pdai_trader.strategies.base_strategy import BaseStrategy

# Curated registry of battle-tested strategies that import cleanly without the
# original project's heavier dependencies. Extend as needed.
_STRATEGY_REGISTRY: Dict[str, str] = {
    "MovingAverageCrossover": "pdai_trader.strategies.ma_crossover:MovingAverageCrossover",
    "BollingerBandsStrategy": "pdai_trader.strategies.bollinger_bands_strategy:BollingerBandsStrategy",
    "RSIStrategy": "pdai_trader.strategies.rsi_strategy:RSIStrategy",
    "MACDStrategy": "pdai_trader.strategies.macd_strategy:MACDStrategy",
    "SupertrendStrategy": "pdai_trader.strategies.supertrend_strategy:SupertrendStrategy",
    "ParabolicSARStrategy": "pdai_trader.strategies.parabolic_sar_strategy:ParabolicSARStrategy",
    "MomentumRegimeV3Fusion": "pdai_trader.strategies.momentum_regime_v3_fusion:MomentumRegimeV3Fusion",
}


def list_registered_strategies() -> Dict[str, str]:
    """Return mapping of available strategy names to import targets."""
    return dict(_STRATEGY_REGISTRY)


def register_strategy(name: str, import_path: str) -> None:
    """Allow runtime registration of additional strategies."""
    _STRATEGY_REGISTRY[name] = import_path


def load_strategy_class(name: str) -> Type[BaseStrategy]:
    """Resolve a strategy class by name.

    Args:
        name: Case-sensitive strategy key from the registry. Case-insensitive
              lookup is attempted for convenience.

    Returns:
        Strategy subclass ready for instantiation.

    Raises:
        KeyError: If the strategy name is unknown.
        ImportError: If the strategy module cannot be imported.
        AttributeError: If the expected class is not present in the module.
    """
    if name in _STRATEGY_REGISTRY:
        target = _STRATEGY_REGISTRY[name]
    else:
        # Attempt case-insensitive match
        lowered = {k.lower(): k for k in _STRATEGY_REGISTRY.keys()}
        canonical = lowered.get(name.lower())
        if not canonical:
            raise KeyError(f"Strategy '{name}' is not registered")
        target = _STRATEGY_REGISTRY[canonical]
        name = canonical

    module_path, class_name = target.split(":")
    module = importlib.import_module(module_path)
    strategy_cls = getattr(module, class_name)
    if not issubclass(strategy_cls, BaseStrategy):
        raise TypeError(f"{class_name} is not a BaseStrategy subclass")
    return strategy_cls
