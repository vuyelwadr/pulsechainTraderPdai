"""Strategy registry and helpers for dynamic loading."""
from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path
from typing import Dict, Type

from pdai_trader.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

# Curated registry of battle-tested strategies that we know import cleanly. The
# full catalogue from ``all_strategies.json`` is layered on below so the
# optimiser can explore the broader library without manual edits.
_STRATEGY_REGISTRY: Dict[str, str] = {
    "MovingAverageCrossover": "pdai_trader.strategies.ma_crossover:MovingAverageCrossover",
    "BollingerBandsStrategy": "pdai_trader.strategies.bollinger_bands_strategy:BollingerBandsStrategy",
    "RSIStrategy": "pdai_trader.strategies.rsi_strategy:RSIStrategy",
    "MACDStrategy": "pdai_trader.strategies.macd_strategy:MACDStrategy",
    "SupertrendStrategy": "pdai_trader.strategies.supertrend_strategy:SupertrendStrategy",
    "ParabolicSARStrategy": "pdai_trader.strategies.parabolic_sar_strategy:ParabolicSARStrategy",
    "MomentumRegimeV3Fusion": "pdai_trader.strategies.momentum_regime_v3_fusion:MomentumRegimeV3Fusion",
}


def _load_catalogue() -> None:
    """Augment the registry with the generated strategy catalogue."""

    catalog_path = Path(__file__).with_name("all_strategies.json")
    if not catalog_path.exists():
        return

    try:
        payload = json.loads(catalog_path.read_text())
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.debug("Failed to load strategy catalogue %s: %s", catalog_path, exc)
        return

    for entry in payload:
        name = entry.get("name")
        module = entry.get("module")
        if not name or not module:
            continue
        target = f"{module}:{name}"

        # Keep manual overrides intact, but extend everything else.
        _STRATEGY_REGISTRY.setdefault(name, target)


_load_catalogue()


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
