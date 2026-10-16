"""Real (non-simulated) example clips dropped into examples/real/.

A clip is detected by its file name:  <input-id>__<preset-id>.mp4   (e.g. alley__dolly-in.mp4)
with optional siblings:
    <name>.json          free-form notes written by the human who ran it (model, template, seed, ...)
    <name>.recipe.json   written by scripts/import_real.py (validated, probed, provenance stamped)

The Demo engine prefers a real clip over a simulated one for the same input + preset, and the UI
badges it in a different colour. Nothing here ever fabricates provenance: a clip that was dropped in
without running the importer is still shown as real (the human put it there) but its recipe says
"not imported".
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import ROOT

REAL_DIR = ROOT / "examples" / "real"
NAME_RE = re.compile(r"^(?P<input>[a-z0-9]+(?:-[a-z0-9]+)*)__(?P<preset>[a-z0-9]+(?:-[a-z0-9]+)*)(?:__(?P<variant>[a-z0-9]+(?:-[a-z0-9]+)*))?\.mp4$")
DEFAULT_MODEL_LABEL = "LTX-2.3"
DEFAULT_PLATFORM = "Comfy Cloud"
PROVENANCE = "real LTX-2.3 output via Comfy Cloud web UI"


def parse_name(name: str) -> tuple[str, str] | None:
    """(input, preset) for `<input>__<preset>.mp4` and for `<input>__<preset>__<variant>.mp4` (see parse_variant)."""
    m = NAME_RE.match(name)
    return (m["input"], m["preset"]) if m else None


def parse_variant(name: str) -> str | None:
    """Optional third part of the file name, e.g. `router-grok-imagine-1-5-lite`. A variant clip is an extra real clip for
    the same input + move made by a different model; the Demo engine never substitutes it for a plain clip."""
    m = NAME_RE.match(name)
    return m["variant"] if m else None


def _load_json(p: Path) -> dict[str, Any]:
    try:
        d = json.loads(p.read_text())
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def badge_text(notes: dict[str, Any] | None = None) -> str:
    """Badge shown in the UI. `notes.badge` replaces the default; `notes.quality` (an honest verdict, e.g.
    'partial: rises but also pushes forward') is appended so it is never separated from the clip."""
    n = notes or {}
    base = n.get("badge") or f"Real {n.get('model_label') or DEFAULT_MODEL_LABEL} output ({n.get('platform') or DEFAULT_PLATFORM})"
    return f"{base} · {n['quality']}" if n.get("quality") else base


@dataclass
class RealClip:
    input: str
    preset: str
    path: Path
    notes: dict[str, Any] = field(default_factory=dict)
    recipe: dict[str, Any] = field(default_factory=dict)
    imported: bool = False
    variant: str | None = None

    @property
    def id(self) -> str:
        return f"{self.input}__{self.preset}" + (f"__{self.variant}" if self.variant else "")

    @property
    def badge(self) -> str:
        return self.recipe.get("badge") or badge_text(self.notes)

    @property
    def recipe_path(self) -> Path:
        return self.path.with_suffix(".recipe.json")

    def effective_recipe(self) -> dict[str, Any]:
        if self.recipe:
            return {**self.recipe, "simulated": False}
        return {
            "schema": "shot-director/recipe@1",
            "kind": "shot",
            "engine": self.notes.get("engine") or "comfy-cloud-web",
            "model": self.notes.get("model") or DEFAULT_MODEL_LABEL,
            "simulated": False,
            "provenance": PROVENANCE + " (dropped into examples/real/ but NOT yet imported with scripts/import_real.py: unvalidated)",
            "badge": self.badge,
            "preset": self.preset,
            "notes": self.notes,
        }


def scan(real_dir: Path = REAL_DIR) -> list[RealClip]:
    out: list[RealClip] = []
    if not real_dir.is_dir():
        return out
    for p in sorted(real_dir.glob("*.mp4")):
        parsed = parse_name(p.name)
        if not parsed or p.stat().st_size == 0:
            continue
        rp = p.with_suffix(".recipe.json")
        out.append(RealClip(parsed[0], parsed[1], p, _load_json(p.with_suffix(".json")), _load_json(rp), rp.is_file(), parse_variant(p.name)))
    return out


def find(input_id: str | None, preset_id: str, real_dir: Path = REAL_DIR) -> RealClip | None:
    if not input_id:
        return None
    for c in scan(real_dir):
        if c.input == input_id and c.preset == preset_id and not c.variant:  # variant clips are gallery-only
            return c
    return None


def recipe_for_path(path: Path, real_dir: Path = REAL_DIR) -> dict[str, Any] | None:
    """If `path` is a real clip, return its (effective) recipe; else None."""
    try:
        path = path.resolve()
        if real_dir.resolve() not in path.parents:
            return None
    except OSError:
        return None
    parsed = parse_name(path.name)
    if not parsed:
        return None
    for c in scan(real_dir):
        if c.path.resolve() == path:
            return c.effective_recipe()
    return None
