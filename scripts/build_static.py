#!/usr/bin/env python3
"""Build the static, backend-free demo (a free static Hugging Face Space) into `space/`.

    python scripts/build_static.py                 # writes ./space/ (git-ignored), checks the size budget
    python scripts/build_static.py --out /tmp/x --limit 2     # quick build with two clips (tests)

What goes in: `static_site/` (index.html, app.js, style.css: plain HTML/JS, no CDN, no bundler), `data.json` (inputs, presets, real-clip
notes with honest labels, credits, ratings and request ids), `media/` (stills, small depth maps, web copies of the real clips, the six real
alley coverage stills) and a Space `README.md` header (sdk: static, license: mit). Nothing else: no keys, no server, no model.

The clips are re-encoded to at most 720p H.264 without audio to stay small (they are the same real outputs; this is a size
transcode, stated on the page). Everything the page shows as REAL comes from examples/real/*.recipe.json.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BUDGET_MB = 25.0       # hard limit from the brief (total media + site)
TARGET_MB = 22.0       # builder tries to land under this
INPUT_IDS = ["alley", "forest-cabin", "retro-diner", "coast-lighthouse"]
SPACE_REPO = "BoltTmade/shot-director"
SPACE_README = """---
title: Shot Director
emoji: 🎬
colorFrom: yellow
colorTo: gray
sdk: static
app_file: index.html
pinned: false
license: mit
short_description: Free previs, then one real render (static demo)
---

# Shot Director (static demo)

Free previs in your browser (simulated, amber), then the **real** model renders (green): MiniMax H3, Grok Imagine 1.5 lite,
FLUX 3 Video and FLUX 3 Image via the Comfy Router, and two LTX-2.3 clips from Comfy Cloud. This Space is a backend-free replay of the
repo's gallery plus an optional "run it yourself" panel that calls api.comfy.org straight from your browser with a key you paste
(held in memory only).

Source, honest status, credit log and process: https://github.com/bolttmade/shot-director
"""


def _ffmpeg() -> str:
    return shutil.which("ffmpeg") or "ffmpeg"


def transcode(src: Path, dst: Path, crf: int) -> None:
    vf = "scale='min(1280,iw)':-2:flags=lanczos,fps=24,format=yuv420p"
    subprocess.run([_ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-an", "-vf", vf, "-c:v", "libx264", "-preset", "slow", "-crf", str(crf),
                    "-movflags", "+faststart", "-map_metadata", "-1", str(dst)], check=True)


def dir_mb(p: Path) -> float:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e6


def build(out: Path, limit: int | None = None) -> dict:
    import numpy as np
    from PIL import Image

    from app.vcam import pseudo_depth

    if out.exists():
        shutil.rmtree(out)
    media = out / "media"
    (media / "stills").mkdir(parents=True)
    (media / "depth").mkdir()
    (media / "clips").mkdir()
    (media / "coverage").mkdir()
    for f in ("index.html", "app.js", "style.css"):
        shutil.copy2(ROOT / "static_site" / f, out / f)
    (out / "README.md").write_text(SPACE_README)

    # ---- inputs: still + depth map
    inputs = []
    for iid in INPUT_IDS:
        meta = json.loads((ROOT / "examples" / "inputs" / f"{iid}.json").read_text())
        im = Image.open(ROOT / "examples" / "inputs" / meta["file"]).convert("RGB")
        im.thumbnail((1280, 720), Image.LANCZOS)
        im.save(media / "stills" / f"{iid}.jpg", "JPEG", quality=82, optimize=True)
        dpath = ROOT / "examples" / "inputs" / f"{iid}_depth.png"
        if dpath.exists():
            d = Image.open(dpath).convert("L")
            kind = "hand-made"
        else:
            arr = pseudo_depth(im)
            d = Image.fromarray((np.clip(arr, 0, 1) * 255).astype("uint8"), "L")
            kind = "heuristic"
        d = d.resize((480, 270), Image.BILINEAR)
        d.save(media / "depth" / f"{iid}.png", optimize=True)
        inputs.append({"id": iid, "title": meta["title"], "blurb": meta["blurb"].replace(" Input for the real Router clips.", ""), "scene": meta["blurb"].replace(" Input for the real Router clips.", ""),
                       "still": f"media/stills/{iid}.jpg", "depth": f"media/depth/{iid}.png", "depth_kind": kind})
    titles = {i["id"]: i["title"] for i in inputs}

    # ---- presets (what the in-browser camera needs, plus the prompt template for the optional own-key run)
    presets = []
    for f in sorted((ROOT / "presets").glob("*.json")):
        if f.name.startswith("_"):
            continue
        p = json.loads(f.read_text())
        presets.append({k: p[k] for k in ("id", "name", "category", "description", "prompt_template", "virtual_camera")})
    pnames = {p["id"]: p["name"] for p in presets}

    # ---- real clips (web copies) with their honest notes
    from app import real as realmod
    clips_src = sorted(realmod.scan(ROOT / "examples" / "real"), key=lambda c: c.path.name)
    if limit:
        clips_src = clips_src[:limit]
    crf = 28
    clips: list[dict] = []
    for attempt in range(4):
        shutil.rmtree(media / "clips"); (media / "clips").mkdir()
        for c in clips_src:
            transcode(c.path, media / "clips" / c.path.name, crf)
        if limit or dir_mb(out) <= TARGET_MB:
            break
        crf += 3
    for c in clips_src:
        rec = json.loads(c.recipe_path.read_text()) if c.recipe_path and c.recipe_path.exists() else {}
        n = rec.get("notes", {}) if isinstance(rec.get("notes"), dict) else {}
        clips.append({
            "id": c.path.stem, "input": c.input, "input_title": titles.get(c.input, c.input), "preset": c.preset, "preset_name": pnames.get(c.preset, c.preset), "variant": c.variant,
            "file": f"media/clips/{c.path.name}", "model_label": n.get("model_label") or realmod.DEFAULT_MODEL_LABEL, "platform": n.get("platform") or realmod.DEFAULT_PLATFORM,
            "badge": c.badge, "credits_used": rec.get("credits_used"), "credits_label": n.get("credits_label"), "rating": n.get("rating"), "request_id": n.get("router_request_id"),
            "quality": n.get("quality") or rec.get("quality"), "verdict": n.get("quality_verdict"), "prompt": rec.get("prompt") or n.get("prompt"), "date": n.get("date") or rec.get("run_date"),
            "simulated": False,
        })
    # ---- coverage
    cov = []
    cdir = ROOT / "examples" / "real" / "coverage" / "alley"
    for cid, label in (("wide", "Wide"), ("medium", "Medium"), ("close", "Close-up"), ("low", "Low angle"), ("high", "High angle"), ("profile", "Profile")):
        im = Image.open(cdir / f"coverage-{cid}.jpg").convert("RGB")
        im.thumbnail((960, 540), Image.LANCZOS)
        im.save(media / "coverage" / f"{cid}.jpg", "JPEG", quality=80, optimize=True)
        cov.append({"id": cid, "label": label, "file": f"media/coverage/{cid}.jpg"})
    data = {"schema": "shot-director/static@1", "space": SPACE_REPO, "inputs": inputs, "presets": presets, "clips": clips, "coverage": cov,
            "note": "Real clips are unedited model output (web copies re-encoded smaller, no audio). Previs is simulated in the browser."}
    (out / "data.json").write_text(json.dumps(data, indent=1) + "\n")
    stats = {"total_mb": round(dir_mb(out), 2), "clips": len(clips), "crf": crf}
    if stats["total_mb"] > BUDGET_MB:
        raise SystemExit(f"static build is {stats['total_mb']} MB, over the {BUDGET_MB} MB budget")
    return stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=ROOT / "space")
    ap.add_argument("--limit", type=int, default=None, help="only the first N clips (fast test builds)")
    a = ap.parse_args(argv)
    stats = build(a.out, a.limit)
    print(f"built {a.out}: {stats['total_mb']} MB, {stats['clips']} clips (crf {stats['crf']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
