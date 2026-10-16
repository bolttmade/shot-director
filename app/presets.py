"""Camera-move presets: plain JSON files in presets/, validated against presets/_schema.json."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .config import ROOT

PRESETS_DIR = ROOT / "presets"


class PresetError(ValueError):
    pass


@lru_cache(maxsize=4)
def _validator(schema_path: str) -> Draft202012Validator:
    return Draft202012Validator(json.loads(Path(schema_path).read_text()))


def validate_preset(data: dict[str, Any], presets_dir: Path = PRESETS_DIR) -> None:
    """Raise PresetError with every problem found (path + message)."""
    v = _validator(str(presets_dir / "_schema.json"))
    errs = sorted(v.iter_errors(data), key=lambda e: list(e.path))
    if errs:
        raise PresetError("; ".join(f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errs))
    keys = data["virtual_camera"]["keys"]
    ts = [k["t"] for k in keys]
    if ts != sorted(ts) or ts[0] != 0 or ts[-1] != 1:
        raise PresetError("virtual_camera.keys must be sorted by t, start at t=0 and end at t=1")


def load_presets(presets_dir: Path = PRESETS_DIR) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for p in sorted(presets_dir.glob("*.json")):
        if p.name.startswith("_"):
            continue
        data = json.loads(p.read_text())
        try:
            validate_preset(data, presets_dir)
        except PresetError as e:
            raise PresetError(f"{p.name}: {e}") from e
        if data["id"] != p.stem:
            raise PresetError(f"{p.name}: id '{data['id']}' must match the file name")
        out[data["id"]] = data
    return out


def load_options(presets_dir: Path = PRESETS_DIR) -> dict[str, Any]:
    return json.loads((presets_dir / "_options.json").read_text())


def build_prompt(preset: dict[str, Any], *, scene: str = "", lens: str | None = None, mood: str | None = None, options: dict[str, Any] | None = None) -> str:
    """Fill the preset's prompt template. Empty slots collapse cleanly."""
    options = options or load_options()
    lens_t = next((o["text"] for o in options["lens"] if o["id"] == lens), "") if lens else ""
    mood_t = next((o["text"] for o in options["mood"] if o["id"] == mood), "") if mood else ""
    scene_t = scene.strip().rstrip(".") + "." if scene.strip() else ""
    text = preset["prompt_template"].format(scene=scene_t, lens=lens_t, mood=mood_t)
    return " ".join(text.split())
