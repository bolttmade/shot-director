"""Engine registry + auto-detection."""

from __future__ import annotations

from ..config import get_settings
from .base import Engine
from .fixtures import FixturesEngine
from .router import RouterEngine
from .workflow import WorkflowEngine

__all__ = ["Engine", "build_engines", "default_engine_id"]


def build_engines() -> dict[str, Engine]:
    return {e.id: e for e in (FixturesEngine(), WorkflowEngine("open"), WorkflowEngine("cloud"), RouterEngine())}


def default_engine_id(engines: dict[str, Engine]) -> str:
    """DEMO=1 forces demo. Otherwise: open weights > cloud/deployment > router > demo (first one that is ready)."""
    if get_settings().demo:
        return "demo"
    for eid in ("open", "cloud", "router"):
        if engines[eid].health().ok:
            return eid
    return "demo"
