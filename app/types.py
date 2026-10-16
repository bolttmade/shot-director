"""Plain data types shared by the server and the engines."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class Angle:
    """Virtual camera position around the subject (matches the Qwen multi-angle LoRA vocabulary)."""

    azimuth: float = 0.0  # degrees, -180..180 (0 = front, + = camera moves to subject's right)
    elevation: float = 0.0  # degrees: -30 low .. 60 high
    distance: str = "medium"  # close | medium | wide


@dataclass
class SourceImage:
    id: str
    path: Path
    name: str
    kind: str = "upload"  # sample | upload
    depth_path: Path | None = None
    subject: tuple[float, float] = (0.5, 0.55)
    sample_id: str | None = None


@dataclass
class ShotRequest:
    source: SourceImage
    preset: dict[str, Any]
    scene: str = ""
    lens: str | None = None
    mood: str | None = None
    duration: int = 5
    resolution: str = "720p"
    seed: int = 7
    angle: Angle | None = None  # optional re-frame applied to the still first
    model: str | None = None  # Router model override
    prompt: str = ""  # filled by the server from the preset template


@dataclass
class ReframeRequest:
    source: SourceImage
    angle: Angle
    scene: str = ""
    seed: int = 7
    model: str | None = None


@dataclass
class CoverageRequest:
    source: SourceImage
    scene: str = ""
    seed: int = 7
    model: str | None = None


@dataclass
class Estimate:
    credits: float | None  # None = unknown
    usd: float | None
    seconds: float | None
    exact: bool = False  # True when it came from the provider's /estimate
    note: str = ""
    over_cap: bool = False
    cap: float | None = None

    def to_dict(self) -> dict:
        return {"credits": self.credits, "usd": self.usd, "seconds": self.seconds, "exact": self.exact, "note": self.note, "over_cap": self.over_cap, "cap": self.cap}


@dataclass
class Health:
    ok: bool
    status: str  # ready | needs_setup | disabled | unreachable
    detail: str = ""
    needs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"ok": self.ok, "status": self.status, "detail": self.detail, "needs": self.needs}


@dataclass
class Artifact:
    kind: str  # video | image
    path: Path  # absolute path inside the job output dir
    label: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Result:
    artifacts: list[Artifact]
    recipe: dict[str, Any]
    credits_used: float | None = None


Emit = Callable[[dict[str, Any]], None]
