"""pDAI trading toolkit built for PulseChain."""

from importlib import import_module
import sys

__all__ = [
    "config",
]

# Preserve legacy absolute imports such as ``import strategies`` that exist
# inside the copied strategy catalogue by aliasing to the new package.
_strategies_module = import_module("pdai_trader.strategies")
sys.modules.setdefault("strategies", _strategies_module)
