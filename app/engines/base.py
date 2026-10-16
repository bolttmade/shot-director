"""The Engine interface every backend implements.

One UI, one preset format, four interchangeable backends:

    demo    replays/simulates with no keys and no network   (app/engines/fixtures.py)
    open    ComfyUI workflows via comfy-sdk -> comfy-api-proxy on your GPU (app/engines/workflow.py)
    cloud   the same workflow adapter pointed at Comfy Cloud / an API deployment
    router  partner models via Comfy Router, `client.models.*`   (app/engines/router.py)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..types import CoverageRequest, Emit, Estimate, Health, ReframeRequest, Result, ShotRequest


class Engine(ABC):
    id: str = "base"
    label: str = "Base"
    description: str = ""
    kind: str = "demo"  # demo | open | cloud | router
    partner: bool = False  # uses partner (API) models -> NOT eligible for "open weights only"
    simulated: bool = False

    @abstractmethod
    def health(self) -> Health:
        """Cheap readiness check. Must not spend credits."""

    @abstractmethod
    def estimate(self, what: str, req: ShotRequest | ReframeRequest | CoverageRequest) -> Estimate:
        """Cost/time estimate *before* running. `what` is shot | reframe | coverage."""

    @abstractmethod
    def run_shot(self, req: ShotRequest, emit: Emit, out_dir: Path) -> Result:
        """Animate the source still with the preset's camera move -> one video."""

    @abstractmethod
    def reframe(self, req: ReframeRequest, emit: Emit, out_dir: Path) -> Result:
        """Re-shoot the still from another virtual camera angle -> one image."""

    @abstractmethod
    def coverage(self, req: CoverageRequest, emit: Emit, out_dir: Path) -> Result:
        """Six coverage stills (wide, medium, close-up, low, high, profile)."""

    def info(self) -> dict:
        h = self.health()
        return {"id": self.id, "label": self.label, "description": self.description, "kind": self.kind, "partner": self.partner, "simulated": self.simulated, "health": h.to_dict()}
