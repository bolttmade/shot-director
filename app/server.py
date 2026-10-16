"""Shot Director API + static UI.   `DEMO=1 python -m app.server`  ->  http://127.0.0.1:8000"""

from __future__ import annotations

import asyncio
import io
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

from . import __version__, angles
from . import real as realmod
from .config import ROOT, get_settings
from .engines import build_engines, default_engine_id
from .errors import EngineError
from .jobs import Job, JobStore
from .media import ffmpeg_bin
from .presets import build_prompt, load_options, load_presets
from .recipes import make_recipe, sha256_file
from .samples import list_samples, sample_source
from .stitch import StitchError, stitch
from .types import Angle, Artifact, CoverageRequest, ReframeRequest, Result, ShotRequest, SourceImage

MAX_UPLOAD = 15 * 1024 * 1024
CREDIT_ENGINES = {"router", "cloud"}


class AngleIn(BaseModel):
    azimuth: float = Field(0, ge=-180, le=360)
    elevation: float = Field(0, ge=-30, le=60)
    distance: str = Field("medium", pattern="^(close|medium|wide)$")

    def to_angle(self) -> Angle:
        return Angle(self.azimuth, self.elevation, self.distance)


class ShotIn(BaseModel):
    source_id: str
    preset_id: str
    engine: str = "demo"
    scene: str = Field("", max_length=400)
    lens: str | None = None
    mood: str | None = None
    duration: int = Field(5, ge=2, le=10)
    resolution: str = Field("720p", pattern="^(480p|720p)$")
    seed: int = Field(7, ge=0, le=2**32 - 1)
    angle: AngleIn | None = None
    model: str | None = Field(None, max_length=120)
    confirm_cost: bool = False


class ReframeIn(BaseModel):
    source_id: str
    engine: str = "demo"
    angle: AngleIn
    scene: str = Field("", max_length=400)
    seed: int = Field(7, ge=0, le=2**32 - 1)
    model: str | None = None
    confirm_cost: bool = False


class CoverageIn(BaseModel):
    source_id: str
    engine: str = "demo"
    scene: str = Field("", max_length=400)
    seed: int = Field(7, ge=0, le=2**32 - 1)
    model: str | None = None
    confirm_cost: bool = False


class AdoptIn(BaseModel):
    url: str


class SequenceIn(BaseModel):
    clips: list[str] = Field(min_length=1, max_length=12)
    crossfade: float = Field(0.4, ge=0, le=1.5)
    aspect: str | None = Field(None, pattern="^(16:9|9:16)$")
    labels: bool = False  # burn a "REAL · model · platform" / "SIMULATED" label into every clip


class ReelIn(BaseModel):
    clips: list[str] = Field(min_length=1, max_length=12)
    crossfade: float = Field(0.4, ge=0, le=1.5)
    aspects: list[str] = Field(["16:9", "9:16"], min_length=1, max_length=2)


def create_app() -> FastAPI:
    S = get_settings()
    S.outputs_dir.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="Shot Director", version=__version__)
    engines = build_engines()
    presets = load_presets(S.presets_dir)
    options = load_options(S.presets_dir)
    store = JobStore()
    jobs_dir = S.outputs_dir / "jobs"
    uploads = S.outputs_dir / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ helpers
    def url_for(path: Path) -> str:
        p = path.resolve()
        for root, prefix in ((S.outputs_dir.resolve(), "/outputs"), (S.examples_dir.resolve(), "/examples")):
            try:
                return f"{prefix}/{p.relative_to(root).as_posix()}"
            except ValueError:
                continue
        raise ValueError("path outside served roots")

    def path_for(url: str) -> Path:
        m = re.match(r"^/(outputs|examples)/(.+)$", url.split("?")[0])
        if not m:
            raise HTTPException(400, "Clip URLs must start with /outputs/ or /examples/")
        root = (S.outputs_dir if m.group(1) == "outputs" else S.examples_dir).resolve()
        p = (root / m.group(2)).resolve()
        if root not in p.parents or not p.is_file():
            raise HTTPException(404, f"Clip not found: {url}")
        return p

    def resolve_source(source_id: str) -> SourceImage:
        kind, _, key = source_id.partition(":")
        if kind == "sample":
            try:
                return sample_source(key)
            except KeyError:
                raise HTTPException(404, "Unknown sample") from None
        if kind == "upload" and re.fullmatch(r"[0-9a-f]{12}", key):
            p = uploads / f"{key}.jpg"
            if p.is_file():
                return SourceImage(id=source_id, path=p, name="your upload", kind="upload")
        raise HTTPException(404, "Unknown source. Upload an image or pick a sample.")

    def engine_for(eid: str, confirm: bool):
        eng = engines.get(eid)
        if not eng:
            raise HTTPException(404, f"Unknown engine '{eid}'")
        if S.demo and eid != "demo":
            raise HTTPException(409, "DEMO=1 is set: only the Demo engine is available. Unset DEMO to use others.")
        h = eng.health()
        if not h.ok:
            raise HTTPException(412, {"code": "not_ready", "message": f"{eng.label} is not ready: {h.detail}", "hint": "See the engine panel for setup steps.", "needs": h.needs})
        if eid in CREDIT_ENGINES and not confirm:
            raise HTTPException(409, {"code": "confirm_cost", "message": "This engine spends credits. Confirm the estimate first.", "hint": "Send confirm_cost=true after showing the estimate."})
        return eng

    def to_payload(res: Result, job: Job) -> dict[str, Any]:
        arts = []
        for a in res.artifacts:
            arts.append({**a.meta, "kind": a.kind, "url": url_for(a.path), "label": a.label})
        out_dir = res.artifacts[0].path.parent if res.artifacts else jobs_dir / job.id
        (out_dir / "recipe.json").write_text(json.dumps(res.recipe, indent=2))
        is_real = any(a.meta.get("real") for a in res.artifacts)
        return {"artifacts": arts, "recipe": res.recipe, "recipe_url": url_for(out_dir / "recipe.json"), "credits_used": res.credits_used, "simulated": bool(res.recipe.get("simulated")), "real": is_real, "badge": res.recipe.get("badge") if is_real else None}

    def shot_request(b: ShotIn) -> ShotRequest:
        preset = presets.get(b.preset_id)
        if not preset:
            raise HTTPException(404, "Unknown camera move")
        return ShotRequest(source=resolve_source(b.source_id), preset=preset, scene=b.scene, lens=b.lens, mood=b.mood, duration=b.duration, resolution=b.resolution, seed=b.seed, angle=b.angle.to_angle() if b.angle else None, model=b.model, prompt=build_prompt(preset, scene=b.scene, lens=b.lens, mood=b.mood, options=options))

    # ------------------------------------------------------------------ meta
    @app.get("/api/config")
    def config() -> dict:
        try:
            ffmpeg_bin()
            ff = True
        except RuntimeError:
            ff = False
        return {"version": __version__, "demo": S.demo, "ffmpeg": ff, "max_credits_per_run": S.max_credits_per_run, "repo_url": S.repo_url, "badge": "Demo fixture: simulated camera move, not model output", "options": options}

    @app.get("/api/engines")
    def list_engines() -> dict:
        out = []
        for e in engines.values():
            info = e.info()
            if S.demo and e.id != "demo":
                info["health"] = {"ok": False, "status": "disabled", "detail": "Disabled while DEMO=1.", "needs": []}
            if hasattr(e, "models"):
                info["models"] = e.models()  # type: ignore[attr-defined]
            out.append(info)
        return {"default": default_engine_id(engines), "engines": out}

    @app.get("/api/presets")
    def list_presets() -> dict:
        return {"presets": [{k: v for k, v in p.items() if k != "$schema"} | {"thumb": f"/examples/presets/{p['id']}.mp4"} for p in presets.values()], "options": options}

    @app.get("/api/samples")
    def samples() -> dict:
        out = []
        for m in list_samples(S.examples_dir / "inputs"):
            out.append({**m, "id": f"sample:{m['id']}", "sample_id": m["id"], "url": f"/examples/inputs/{m['file']}"})
        return {"samples": out}

    @app.get("/api/gallery")
    def gallery() -> dict:
        mf = S.examples_dir / "outputs" / "manifest.json"
        data = json.loads(mf.read_text()) if mf.is_file() else {"items": []}
        for it in data["items"]:
            it["simulated"] = True  # everything in the committed manifest is a simulated placeholder
            if "file" in it:
                it["url"] = f"/examples/outputs/{it['file']}"
            for f in it.get("files", []):
                f["url"] = f"/examples/outputs/{f['file']}"
        real_items = []
        for c in realmod.scan(S.real_dir):
            real_items.append({"id": c.id, "kind": "clip", "input": c.input, "preset": c.preset, "variant": c.variant, "url": f"/examples/real/{c.path.name}", "recipe_url": f"/examples/real/{c.recipe_path.name}" if c.imported else None, "simulated": False, "real": True, "badge": c.badge, "imported": c.imported, "model_label": c.notes.get("model_label") or realmod.DEFAULT_MODEL_LABEL, "platform": c.notes.get("platform") or realmod.DEFAULT_PLATFORM, "rating": c.notes.get("rating"), "credits_used": c.notes.get("credits_used"), "credits_label": c.notes.get("credits_label")})
        real_items.sort(key=lambda i: (-(i["rating"] or 0), i["id"]))  # best-rated real clips first
        data["items"] = real_items + data["items"]  # real clips first
        data["badges"] = {"simulated": "Demo fixture: simulated camera move, not model output"}
        return data

    @app.get("/api/angle")
    def angle_info(azimuth: float = 0, elevation: float = 0, distance: str = "medium") -> dict:
        a = Angle(azimuth, elevation, distance if distance in angles.DISTANCES else "medium")
        s = angles.snap_angle(a)
        return {"prompt": angles.qwen_prompt(a), "snapped": vars(s), "description": angles.describe(a)}

    # ------------------------------------------------------------------ upload
    @app.post("/api/upload")
    async def upload(file: UploadFile = File(...)) -> dict:
        data = await file.read(MAX_UPLOAD + 1)
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "Image too large (max 15 MB).")
        try:
            im = Image.open(io.BytesIO(data))
            im.load()
        except (UnidentifiedImageError, OSError):
            raise HTTPException(415, "That file is not a readable image (PNG, JPEG or WebP).") from None
        im = im.convert("RGB")
        im.thumbnail((2400, 2400))
        uid = uuid.uuid4().hex[:12]
        im.save(uploads / f"{uid}.jpg", "JPEG", quality=92)  # re-encoded: strips metadata
        return {"id": f"upload:{uid}", "url": f"/outputs/uploads/{uid}.jpg", "name": Path(file.filename or "upload").name[:60], "width": im.width, "height": im.height}

    # ------------------------------------------------------------------ estimate
    @app.post("/api/estimate")
    def estimate(b: ShotIn) -> dict:
        eng = engines.get(b.engine)
        if not eng:
            raise HTTPException(404, "Unknown engine")
        try:
            est = eng.estimate("shot", shot_request(b))
        except EngineError as e:
            raise HTTPException(e.http_status, e.to_dict()) from e
        return est.to_dict()

    # ------------------------------------------------------------------ jobs
    @app.post("/api/shots")
    def create_shot(b: ShotIn) -> dict:
        eng = engine_for(b.engine, b.confirm_cost)
        req = shot_request(b)
        job = store.submit("shot", eng.id, req.preset["name"], lambda emit, out: eng.run_shot(req, emit, out), jobs_dir, to_payload)
        return job.snapshot()

    @app.post("/api/reframe")
    def create_reframe(b: ReframeIn) -> dict:
        eng = engine_for(b.engine, b.confirm_cost)
        req = ReframeRequest(source=resolve_source(b.source_id), angle=b.angle.to_angle(), scene=b.scene, seed=b.seed, model=b.model)
        job = store.submit("reframe", eng.id, angles.describe(req.angle), lambda emit, out: eng.reframe(req, emit, out), jobs_dir, to_payload)
        return job.snapshot()

    @app.post("/api/coverage")
    def create_coverage(b: CoverageIn) -> dict:
        eng = engine_for(b.engine, b.confirm_cost)
        req = CoverageRequest(source=resolve_source(b.source_id), scene=b.scene, seed=b.seed, model=b.model)
        job = store.submit("coverage", eng.id, "Coverage board", lambda emit, out: eng.coverage(req, emit, out), jobs_dir, to_payload)
        return job.snapshot()

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str) -> dict:
        job = store.get(job_id)
        if not job:
            raise HTTPException(404, "Unknown job")
        return job.snapshot()

    @app.get("/api/jobs/{job_id}/events")
    async def job_events(job_id: str) -> StreamingResponse:
        job = store.get(job_id)
        if not job:
            raise HTTPException(404, "Unknown job")

        async def gen():
            i = 0
            last = time.time()
            while True:
                with job.lock:
                    batch = job.events[i:]
                for ev in batch:
                    yield f"data: {json.dumps(ev)}\n\n"
                    i += 1
                    last = time.time()
                    if ev.get("type") in ("done", "error"):
                        return
                if time.time() - last > 15:
                    yield ": keepalive\n\n"
                    last = time.time()
                await asyncio.sleep(0.15)

        return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.post("/api/adopt")
    def adopt(b: AdoptIn) -> dict:
        """Turn any generated/example still into a new source image (e.g. 'animate this coverage angle')."""
        p = path_for(b.url)
        try:
            im = Image.open(p).convert("RGB")
        except (UnidentifiedImageError, OSError):
            raise HTTPException(415, "That file is not an image.") from None
        uid = uuid.uuid4().hex[:12]
        im.save(uploads / f"{uid}.jpg", "JPEG", quality=92)
        return {"id": f"upload:{uid}", "url": f"/outputs/uploads/{uid}.jpg", "name": p.stem, "width": im.width, "height": im.height}

    # ------------------------------------------------------------------ sequence
    def _is_sim(path: Path) -> bool:
        rr = realmod.recipe_for_path(path, S.real_dir)
        if rr is not None:
            return bool(rr.get("simulated"))  # real clips are not simulated
        if "examples" in path.parts:
            return True  # every other committed example is a simulated placeholder
        rp = path.parent / "recipe.json"
        try:
            return bool(json.loads(rp.read_text()).get("simulated")) if rp.is_file() else False
        except (OSError, ValueError):
            return False

    def _label(path: Path) -> str:
        if _is_sim(path):
            return "SIMULATED previs: not model output"
        rr = realmod.recipe_for_path(path, S.real_dir) or {}
        n = rr.get("notes") or {}
        return f"REAL: {n.get('model_label') or realmod.DEFAULT_MODEL_LABEL} via {rr.get('platform') or n.get('platform') or realmod.DEFAULT_PLATFORM}"

    def _build_sequence(urls: list[str], crossfade: float, aspect: str | None, labels: bool) -> dict[str, Any]:
        paths = [path_for(u) for u in urls]
        seq_id = uuid.uuid4().hex[:12]
        out = S.outputs_dir / "sequences" / f"{seq_id}.mp4"
        try:
            stitch(paths, out, crossfade=crossfade, aspect=aspect, labels=[_label(p) for p in paths] if labels else None)
        except (StitchError, RuntimeError) as e:
            raise HTTPException(500, {"code": "stitch_failed", "message": str(e), "hint": "Is ffmpeg installed? (apt install ffmpeg / brew install ffmpeg)"}) from e
        flags = [_is_sim(p) for p in paths]
        simulated = any(flags)
        n_sim = sum(flags)
        prov = f"ffmpeg edit of {len(paths)} clip(s): {len(paths) - n_sim} real model output, {n_sim} SIMULATED placeholder" + (" (so the whole sequence must be presented as containing simulated footage)" if n_sim else "")
        recipe = make_recipe(kind="sequence", engine="ffmpeg", model="ffmpeg-xfade" if crossfade else "ffmpeg-concat", source_name=f"{len(paths)} clips", source_sha256=None, simulated=simulated, params={"clips": urls, "crossfade_s": crossfade, "aspect": aspect or "source", "labels": labels, "real_clips": len(paths) - n_sim, "simulated_clips": n_sim}, extra={"provenance": prov})
        (out.parent / f"{seq_id}.recipe.json").write_text(json.dumps(recipe, indent=2))
        return {"url": url_for(out), "recipe": recipe, "recipe_url": url_for(out.parent / f"{seq_id}.recipe.json"), "aspect": aspect or "16:9"}

    @app.post("/api/sequence")
    def make_sequence(b: SequenceIn) -> dict:
        return _build_sequence(b.clips, b.crossfade, b.aspect, b.labels)

    @app.post("/api/reel")
    def make_reel(b: ReelIn) -> dict:
        """'Make my reel': the REAL clips among `clips`, cut together with a burned-in model label, once per aspect ratio. Simulated clips are skipped."""
        real_urls = [u for u in b.clips if not _is_sim(path_for(u))]
        if not real_urls:
            raise HTTPException(422, {"code": "no_real_clips", "message": "A reel is made from real model clips and none of these are real.", "hint": "Add real (green) clips from the gallery to the timeline first."})
        reels = [_build_sequence(real_urls, b.crossfade, a, True) for a in dict.fromkeys(b.aspects)]
        return {"reels": reels, "skipped_simulated": len(b.clips) - len(real_urls)}

    # ------------------------------------------------------------------ static
    app.mount("/outputs", StaticFiles(directory=S.outputs_dir), name="outputs")
    app.mount("/examples", StaticFiles(directory=S.examples_dir), name="examples")
    app.mount("/static", StaticFiles(directory=S.web_dir), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(S.web_dir / "index.html", headers={"Cache-Control": "no-cache"})

    @app.exception_handler(HTTPException)
    async def http_exc(_, exc: HTTPException):  # keep {detail: {...}} bodies structured
        body = exc.detail if isinstance(exc.detail, dict) else {"code": "http_error", "message": str(exc.detail), "hint": ""}
        return JSONResponse(status_code=exc.status_code, content=body)

    return app


app = create_app()


def main() -> None:
    import uvicorn

    S = get_settings()
    print(f"\n  Shot Director v{__version__}  ->  http://{S.host}:{S.port}   ({'DEMO mode: no keys, simulated camera moves' if S.demo else 'engines auto-detected'})\n")
    uvicorn.run("app.server:app", host=S.host, port=S.port, log_level="warning")


if __name__ == "__main__":
    main()
