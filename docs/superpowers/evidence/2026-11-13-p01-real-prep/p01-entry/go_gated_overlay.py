"""Package shim for the p01 entry's real-chain stage-b argv.

The gated supervisor uses relative imports against its sibling PRODUCT
modules (batch_execution, readonly_batch, resource_watch, snapshots, …).
The image ships that package; this overlay only replaces the supervisor
module itself. The shim registers a namespace-style parent package whose
search path chains the bound lib directory FIRST and the installed product
package second, so `from .batch_execution import …` resolves to the real
product module while `go_gated_supervisor` comes from this directory —
byte-for-byte the v14 delivery contract.
"""
import importlib.util
import os
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG = "_xrg_p01_lib"


def _product_paths():
    try:
        import xiangrugu_datamgmt as prod
        return [os.path.dirname(os.path.abspath(prod.__file__))]
    except ImportError:
        return []


if _PKG not in sys.modules:
    mod = types.ModuleType(_PKG)
    mod.__path__ = [_HERE] + _product_paths()
    mod.__package__ = _PKG
    sys.modules[_PKG] = mod

_spec = importlib.util.spec_from_file_location(
    f"{_PKG}.go_gated_supervisor",
    os.path.join(_HERE, "go_gated_supervisor.py"))
if _spec is None or _spec.loader is None:
    raise ImportError("go_gated_supervisor_unloadable")
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)

# Hand over exactly like `python -m <module>` would.
raise SystemExit(_mod.main())
