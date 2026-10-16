"""Virtual-camera angle vocabulary: Qwen multi-angle LoRA prompts and demo-engine camera poses."""

from __future__ import annotations

import math

from .types import Angle

AZIMUTHS = {0: "front view", 45: "front-right quarter view", 90: "right side view", 135: "back-right quarter view", 180: "back view", 225: "back-left quarter view", 270: "left side view", 315: "front-left quarter view"}
ELEVATIONS = {-30: "low-angle shot", 0: "eye-level shot", 30: "elevated shot", 60: "high-angle shot"}
DISTANCES = {"close": "close-up", "medium": "medium shot", "wide": "wide shot"}


def snap_angle(a: Angle) -> Angle:
    """Snap to the 8 x 4 x 3 grid the open-weights LoRA was trained on."""
    az = round((a.azimuth % 360) / 45) * 45 % 360
    el = min(ELEVATIONS, key=lambda e: abs(e - a.elevation))
    dist = a.distance if a.distance in DISTANCES else "medium"
    return Angle(float(az), float(el), dist)


def qwen_prompt(a: Angle) -> str:
    s = snap_angle(a)
    return f"<sks> {AZIMUTHS[int(s.azimuth)]} {ELEVATIONS[int(s.elevation)]} {DISTANCES[s.distance]}"


NATURAL_AZ = {0: "straight-on", 45: "from a three-quarter angle on the right", 90: "from the right side", 135: "from behind on the right", 180: "from behind", 225: "from behind on the left", 270: "from the left side", 315: "from a three-quarter angle on the left"}
NATURAL_EL = {-30: "low camera angle looking up", 0: "camera at eye level", 30: "camera raised, looking slightly down", 60: "high camera angle looking down"}
NATURAL_DIST = {"close": "close-up framing", "medium": "medium framing", "wide": "wide framing pulled back to show more of the surroundings"}


def natural_prompt(a: Angle) -> str:
    """The same angle grid in plain English, for image-edit models that were not trained on the <sks> vocabulary (FLUX 3 via the Router)."""
    s = snap_angle(a)
    return f"{NATURAL_AZ[int(s.azimuth)]}, {NATURAL_EL[int(s.elevation)]}, {NATURAL_DIST[s.distance]}"


def describe(a: Angle) -> str:
    return qwen_prompt(a).replace("<sks> ", "")


COVERAGE: list[dict] = [
    {"id": "wide", "label": "Wide", "angle": Angle(0, 0, "wide")},
    {"id": "medium", "label": "Medium", "angle": Angle(0, 0, "medium")},
    {"id": "close", "label": "Close-up", "angle": Angle(0, 0, "close")},
    {"id": "low", "label": "Low angle", "angle": Angle(0, -30, "medium")},
    {"id": "high", "label": "High angle", "angle": Angle(0, 60, "medium")},
    {"id": "profile", "label": "Over-shoulder / profile", "angle": Angle(45, 0, "medium")},
]


def angle_to_cam(a: Angle, subject: tuple[float, float] = (0.5, 0.55)) -> dict[str, float]:
    """Pose for the *simulated* (depth-parallax) camera.

    Deliberately modest: one still cannot show the back of an object, and large parallax moves tear
    thin structures. Close-up is a pure punch-in toward the subject (no dolly) so it stays clean.
    """
    az = ((a.azimuth + 180) % 360) - 180
    theta = max(-40.0, min(40.0, az)) / 40.0
    cam: dict[str, float] = {"right": 0.7 * theta, "yaw": -3.8 * theta, "forward": 0.15 * abs(theta)}
    el = max(-30.0, min(60.0, a.elevation))
    if el < 0:
        k = el / -30.0
        cam["up"], cam["pitch"] = -0.12 * k, 2.0 * k
    else:
        k = el / 60.0
        cam["up"], cam["pitch"] = 0.3 * k, -3.5 * k
    if a.distance == "wide":
        cam["forward"] -= 0.55
    elif a.distance == "close":
        cam["zoom"] = 1.9
        sx, sy = subject
        cam["yaw"] += math.degrees((sx - 0.5) / 0.9) * 0.85
        cam["pitch"] += -math.degrees((sy - 0.5) * (9 / 16) / 0.9) * 0.85
    return cam
