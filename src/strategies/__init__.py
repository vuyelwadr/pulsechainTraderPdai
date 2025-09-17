"""Compatibility shim to support legacy imports like ``import strategies``."""
from importlib import import_module
from pathlib import Path
import sys

_real_pkg = import_module("pdai_trader.strategies")

# Mirror submodule search path so ``strategies.foo`` resolves against the
# implementation inside ``pdai_trader.strategies``.
__path__ = [str(Path(__file__).resolve().parent.parent / "pdai_trader" / "strategies")]

# Re-export common attributes.
__all__ = getattr(_real_pkg, "__all__", [])
for name in __all__:
    globals()[name] = getattr(_real_pkg, name)

# Ensure fully-qualified submodule imports share the same module objects.
for module_name, module in list(sys.modules.items()):
    if module_name.startswith("pdai_trader.strategies"):
        alias = module_name.replace("pdai_trader.", "")
        sys.modules.setdefault(alias, module)
