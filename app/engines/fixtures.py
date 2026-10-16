"""Demo engine: no keys, no network, no GPU.

* Committed example clips (examples/outputs/) are replayed instantly with simulated progress.
* Anything else (your own upload, a move we have not pre-rendered, the angle dial) is rendered
  live with the depth-parallax virtual camera in app/vcam.py.

Everything this engine returns is a SIMULATED camera move, not generative-model output, and is
flagged `simulated: true` in its recipe and with a badge in the UI.
"""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
from pathlib import Path

from PIL import Image

from .. import angles, vcam
from ..config import ROOT
from .. import real as realmod
from ..media import encode_frames, save_jpg
from ..recipes import make_recipe, sha256_file
from ..types import Angle, Artifact, CoverageRequest, Emit, Estimate, Health, ReframeRequest, Result, ShotRequest, SourceImage
from .base import Engine

OUTPUTS = ROOT / "examples" / "outputs"
SIM_LABEL = "Demo fixture: simulated camera move, not model output"
_RENDER_LOCK = threading.Lock()
_SCENE_CACHE: dict[str, vcam.Scene] = {}

RES = {"480p": (854, 480), "720p": (1280, 720)}


def load_manifest(outputs: Path = OUTPUTS) -> dict:
    p = outputs / "manifest.json"
    return json.loads(p.read_text()) if p.is_file() else {"items": []}


def scene_for(src: SourceImage) -> vcam.Scene:
    key = f"{src.path}:{src.path.stat().st_mtime_ns}"
    if key not in _SCENE_CACHE:
        if len(_SCENE_CACHE) > 3:
            _SCENE_CACHE.pop(next(iter(_SCENE_CACHE)))
        img = Image.open(src.path)
        depth = Image.open(src.depth_path) if src.depth_path and src.depth_path.is_file() else None
        _SCENE_CACHE[key] = vcam.Scene.from_images(img, depth)
    return _SCENE_CACHE[key]


class FixturesEngine(Engine):
    id = "demo"
    label = "Demo (fixtures)"
    description = "No keys, no GPU. Replays committed examples and renders a simulated depth-parallax camera. Not model output."
    kind = "demo"
    simulated = True

    def __init__(self, outputs: Path = OUTPUTS, fps: int = 24, real_dir: Path | None = None):
        self.outputs = outputs
        self.real_dir = real_dir or (Path(os.environ["REAL_DIR"]) if os.environ.get("REAL_DIR") else outputs.parent / "real")
        self.fps = fps

    # ------------------------------------------------------------------ meta
    def health(self) -> Health:
        return Health(True, "ready", "Always available. Simulated camera moves only.")

    def estimate(self, what, req) -> Estimate:
        secs = {"shot": 4 + 0.6 * getattr(req, "duration", 3), "reframe": 1.5, "coverage": 4}.get(what, 3)
        return Estimate(credits=0.0, usd=0.0, seconds=secs, exact=True, note="Free. Simulated parallax render on this machine.")

    def _lookup(self, kind: str, sample_id: str | None, preset_id: str | None = None) -> dict | None:
        if not sample_id:
            return None
        for it in load_manifest(self.outputs)["items"]:
            if it["kind"] == kind and it.get("input") == sample_id and (preset_id is None or it.get("preset") == preset_id):
                return it
        return None

    # ------------------------------------------------------------------ shot
    def run_shot(self, req: ShotRequest, emit: Emit, out_dir: Path) -> Result:
        out_dir.mkdir(parents=True, exist_ok=True)
        pid = req.preset["id"]
        src_hash = sha256_file(req.source.path)
        plain = req.angle is None and not req.scene.strip()  # replays only match the unmodified preset
        real_clip = realmod.find(req.source.sample_id, pid, self.real_dir) if plain else None
        hit = self._lookup("clip", req.source.sample_id, pid) if plain and not real_clip else None
        if real_clip:  # a REAL model output beats a simulated one for the same input + preset
            badge = real_clip.badge
            emit({"type": "status", "status": "queued", "message": f"Found a real clip for this input + move ({badge}). Replaying it: it was generated earlier, not now."})
            for i in range(1, 7):
                emit({"type": "progress", "value": i / 6, "message": "Replaying real clip from examples/real/"})
                time.sleep(0.12)
            dst = out_dir / f"{pid}.mp4"
            shutil.copyfile(real_clip.path, dst)
            recipe = {**real_clip.effective_recipe(), "replayed_from": f"real/{real_clip.path.name}", "simulated": False}
            return Result([Artifact("video", dst, f"{req.preset['name']} (real)", {"simulated": False, "real": True, "label": badge})], recipe, 0.0)
        emit({"type": "status", "status": "queued", "message": "Demo engine: preparing simulated shot"})
        if hit:
            src = self.outputs / hit["file"]
            for i in range(1, 11):
                emit({"type": "progress", "value": i / 10, "message": "Replaying committed example clip"})
                time.sleep(0.18)
            dst = out_dir / f"{pid}.mp4"
            shutil.copyfile(src, dst)
            recipe = json.loads((self.outputs / hit["recipe"]).read_text()) if hit.get("recipe") else {}
            recipe.update({"replayed_from": hit["file"], "simulated": True})
            return Result([Artifact("video", dst, f"{req.preset['name']} (simulated)", {"simulated": True, "label": SIM_LABEL})], recipe, 0.0)
        # live render
        w, h = RES.get(req.resolution, RES["720p"])
        if req.resolution == "720p" and not req.source.sample_id:
            w, h = RES["480p"]  # keep uploads snappy; the UI says so
        n = max(2, int(req.duration)) * self.fps
        path = vcam.CameraPath.from_spec(req.preset["virtual_camera"])
        with _RENDER_LOCK:
            scene = scene_for(req.source)
            base = out_dir / f"{pid}.mp4"
            t0 = time.time()

            def tick(i: int, total: int) -> None:
                if i % 4 == 0 or i == total:
                    emit({"type": "progress", "value": 0.02 + 0.93 * i / total, "message": f"Rendering simulated camera path ({i}/{total} frames)", "step": i, "steps": total})

            cam_path = path
            if req.angle is not None:
                base_cam = angles.angle_to_cam(req.angle, req.source.subject)
                cam_path = _offset_path(path, base_cam)
            emit({"type": "status", "status": "running"})
            frames = vcam.frames(scene, cam_path, n, w, h, on_frame=tick)
            encode_frames(frames, base, width=w, height=h, fps=self.fps)
        recipe = make_recipe(kind="shot", engine="demo", model="vcam-depth-parallax", source_name=req.source.name, source_sha256=src_hash, preset_id=pid, prompt=req.prompt, negative=req.preset.get("negative", ""), seed=req.seed, params={"duration": req.duration, "resolution": f"{w}x{h}", "fps": self.fps, "angle": vars(req.angle) if req.angle else None, "render_seconds": round(time.time() - t0, 1)}, simulated=True, credits_used=0.0)
        return Result([Artifact("video", base, f"{req.preset['name']} (simulated)", {"simulated": True, "label": SIM_LABEL})], recipe, 0.0)

    # ------------------------------------------------------------------ reframe
    def reframe(self, req: ReframeRequest, emit: Emit, out_dir: Path) -> Result:
        out_dir.mkdir(parents=True, exist_ok=True)
        emit({"type": "status", "status": "running", "message": "Demo engine: simulated angle change"})
        with _RENDER_LOCK:
            scene = scene_for(req.source)
            cam = angles.angle_to_cam(req.angle, req.source.subject)
            arr = vcam.render(scene, cam, 1280, 720)
        emit({"type": "progress", "value": 0.9})
        dst = save_jpg(arr, out_dir / "reframe.jpg")
        recipe = make_recipe(kind="reframe", engine="demo", model="vcam-depth-parallax", source_name=req.source.name, source_sha256=sha256_file(req.source.path), prompt=angles.qwen_prompt(req.angle), seed=req.seed, params={"angle": vars(req.angle), "simulated_clamp_deg": 40}, simulated=True, credits_used=0.0)
        return Result([Artifact("image", dst, angles.describe(req.angle), {"simulated": True, "label": SIM_LABEL})], recipe, 0.0)

    # ------------------------------------------------------------------ coverage
    def coverage(self, req: CoverageRequest, emit: Emit, out_dir: Path) -> Result:
        out_dir.mkdir(parents=True, exist_ok=True)
        emit({"type": "status", "status": "running", "message": "Demo engine: simulated coverage"})
        hit = self._lookup("coverage", req.source.sample_id)
        arts: list[Artifact] = []
        if hit and hit.get("files"):
            for i, f in enumerate(hit["files"]):
                dst = out_dir / Path(f["file"]).name
                shutil.copyfile(self.outputs / f["file"], dst)
                arts.append(Artifact("image", dst, f["label"], {"simulated": True, "shot": f["id"], "label": SIM_LABEL}))
                emit({"type": "progress", "value": (i + 1) / 6, "message": f"Coverage: {f['label']}"})
                time.sleep(0.12)
        else:
            with _RENDER_LOCK:
                scene = scene_for(req.source)
                for i, shot in enumerate(angles.COVERAGE):
                    cam = angles.angle_to_cam(shot["angle"], req.source.subject)
                    dst = save_jpg(vcam.render(scene, cam, 1280, 720), out_dir / f"coverage-{shot['id']}.jpg")
                    arts.append(Artifact("image", dst, shot["label"], {"simulated": True, "shot": shot["id"], "label": SIM_LABEL}))
                    emit({"type": "progress", "value": (i + 1) / 6, "message": f"Coverage: {shot['label']}"})
        recipe = make_recipe(kind="coverage", engine="demo", model="vcam-depth-parallax", source_name=req.source.name, source_sha256=sha256_file(req.source.path), seed=req.seed, params={"shots": [s["id"] for s in angles.COVERAGE]}, simulated=True, credits_used=0.0)
        return Result(arts, recipe, 0.0)


def _offset_path(path: vcam.CameraPath, base: dict[str, float]) -> vcam.CameraPath:
    """Apply a re-frame pose underneath a camera move (the move is relative to the new angle)."""
    keys = []
    for k in path.keys:
        nk = dict(k)
        for ch in ("right", "up", "forward", "yaw", "pitch", "roll"):
            nk[ch] = nk.get(ch, 0.0) + base.get(ch, 0.0)
        nk["zoom"] = nk.get("zoom", 1.0) * base.get("zoom", 1.0)
        keys.append(nk)
    return vcam.CameraPath(keys=keys, ease=path.ease, shake=path.shake, motion_blur=path.motion_blur, rack=path.rack, seed=path.seed)
