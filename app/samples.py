"""Sample inputs shipped in examples/inputs/ (procedurally generated, CC0)."""

from __future__ import annotations

import json
from pathlib import Path

from .config import ROOT
from .types import SourceImage

INPUTS = ROOT / "examples" / "inputs"


def list_samples(inputs: Path = INPUTS) -> list[dict]:
    out = []
    for p in sorted(inputs.glob("*.json")):
        out.append(json.loads(p.read_text()))
    return out


def sample_source(sample_id: str, inputs: Path = INPUTS) -> SourceImage:
    meta_path = inputs / f"{sample_id}.json"
    if not meta_path.is_file() or "/" in sample_id or ".." in sample_id:
        raise KeyError(sample_id)
    meta = json.loads(meta_path.read_text())
    return SourceImage(
        id=f"sample:{sample_id}",
        path=inputs / meta["file"],
        name=meta["title"],
        kind="sample",
        depth_path=(inputs / meta["depth"]) if meta.get("depth") else None,
        subject=tuple(meta.get("subject", (0.5, 0.55))),  # type: ignore[arg-type]
        sample_id=sample_id,
    )
