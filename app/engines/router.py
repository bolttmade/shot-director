"""Comfy Router engine: partner models through `comfy_sdk` -> `client.models.*`.

Safety rails (all covered by tests/test_router_adapter.py with recorded response shapes):

* /estimate is called BEFORE every run; a hard cap (MAX_CREDITS_PER_RUN) is enforced client-side.
  Unknown cost is refused unless ALLOW_UNKNOWN_COST=1.
* submit() is called exactly once per run; this module never wraps it in a retry loop
  (the SDK itself only replays under the same Idempotency-Key). The request id is emitted
  to the UI immediately so a lost connection can be reconciled in the Comfy dashboard.
* 402 insufficient_credits (checked by Router before body validation) becomes a clean message.
* Result URLs expire in 12-24 h, so the file is downloaded the moment the result arrives.
"""

from __future__ import annotations

import base64
import io
import json
import os
import time
from pathlib import Path
from typing import Any, Callable

import httpx
from PIL import Image

from .. import angles, errors as E
from ..config import get_settings
from ..recipes import make_recipe, sha256_file
from ..types import Artifact, CoverageRequest, Emit, Estimate, Health, ReframeRequest, Result, ShotRequest, SourceImage
from .base import Engine
from .errmap import translate

CREDITS_PER_USD = 211.0
DEFAULT_ROUTER_URL = "https://api.comfy.org"
DEFAULT_VIDEO_MODEL = "minimax/minimax-h3"
IMAGE_MODEL = "bfl/flux-3-image"

# USD per second of output video, from docs.comfy.org/development/comfy-router/pricing (read 2026-10-16).
# Only used when /estimate is unavailable (403 not_enabled while it rolls out) so a cap can still be checked.
STATIC_PRICE_USD_PER_S: dict[str, dict[str, float]] = {
    "minimax/minimax-h3": {"768P": 0.1287},
    "xai/grok-imagine-video-1.5-lite": {"480p": 0.0286, "720p": 0.0429},
    "ltx/ltx-2-5-fast": {"720p": 0.1287},
    "ltx/ltx-2-5-pro": {"720p": 0.1716},
}
STATIC_IMAGE_USD = 0.03  # generous per-still allowance for FLUX 3 edits (usage-based; typically cents)

MODEL_INFO = {
    "minimax/minimax-h3": {"label": "MiniMax H3", "i2v": True, "min_s": 4},
    "byteplus/dreamina-seedance-2-5-260628": {"label": "Seedance 2.5", "i2v": True, "min_s": 4},
    "xai/grok-imagine-video-1.5-lite": {"label": "Grok Imagine 1.5 lite (cheapest)", "i2v": True, "min_s": 1},
    "ltx/ltx-2-5-fast": {"label": "LTX 2.5 Fast (text-to-video only)", "i2v": False, "min_s": 2},
}


def image_data_url(path: Path, max_side: int = 1280, quality: int = 90) -> str:
    im = Image.open(path).convert("RGB")
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def build_video_body(model: str, *, prompt: str, image_url: str | None, duration: int, resolution: str, seed: int | None = None, negative: str = "", overrides: dict[str, Any] | None = None) -> tuple[dict[str, Any], list[str]]:
    """Per-provider native request body (schemas: docs.comfy.org/router-schemas/<model>.json). Returns (body, notes)."""
    notes: list[str] = []
    provider = model.split("/", 1)[0]
    info = MODEL_INFO.get(model, {})
    dur = max(int(duration), info.get("min_s", 1))
    if dur != duration:
        notes.append(f"{model} minimum duration is {dur}s (asked for {duration}s)")
    if provider == "minimax":
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        if image_url:
            content.append({"type": "image_url", "image_url": {"url": image_url}, "role": "first_frame"})
        body: dict[str, Any] = {"content": content, "duration": min(dur, 15), "resolution": "768P", "ratio": "16:9"}
        if seed is not None:
            body["seed"] = seed
    elif provider == "byteplus":
        content = [{"type": "text", "text": prompt}]
        if image_url:
            content.append({"type": "image_url", "image_url": {"url": image_url}, "role": "first_frame"})
        body = {"content": content, "duration": dur, "resolution": "480p" if resolution == "480p" else "720p", "generate_audio": False}
        if image_url:
            # Seedance 2.5 first-frame requests must omit `ratio` (or send "adaptive"): a concrete ratio is refused with HTTP 400
            # (Comfy Router quickstart). The aspect follows the first frame. Text-only requests may still set one.
            notes.append("Seedance 2.5: `ratio` omitted because a first-frame image is attached (aspect follows the image).")
        else:
            body["ratio"] = "16:9"
    elif provider == "xai":
        body = {"prompt": prompt, "duration": dur, "aspect_ratio": "16:9", "resolution": "480p" if resolution == "480p" else "720p"}
        if image_url:
            body["image"] = {"type": "image_url", "url": image_url}
    elif provider == "ltx":
        body = {"prompt": prompt, "duration": dur, "resolution": "1280x720", "fps": 24, "generate_audio": False}
        notes.append("LTX via Router is text-to-video only: your still is NOT used as the first frame. Use the Open-weights engine for LTX image-to-video.")
    else:
        body = {"prompt": prompt, "duration": dur}
        if image_url:
            body["image"] = {"type": "image_url", "url": image_url}
    if overrides:
        body.update(overrides)
    return body, notes


def build_image_body(*, prompt: str, image_url: str) -> dict[str, Any]:
    return {"prompt": prompt, "images": [image_url], "aspect_ratio": "16:9", "resolution": "1k"}


def extract_media_url(doc: Any) -> str | None:
    """Find the output URL in a model's native result document (shape differs per provider)."""
    known = [("result", "video_url"), ("content", "video_url"), ("task", "content", "url"), ("video", "url"), ("result", "sample"), ("output", "url"), ("sample",), ("url",)]
    if isinstance(doc, dict):
        for path in known:
            cur: Any = doc
            for k in path:
                cur = cur.get(k) if isinstance(cur, dict) else None
            if isinstance(cur, str) and cur.startswith("http"):
                return cur

        def walk(o: Any) -> str | None:
            if isinstance(o, dict):
                for k, v in o.items():
                    if isinstance(v, str) and v.startswith("http") and k in ("url", "video_url", "image_url", "sample"):
                        return v
                for v in o.values():
                    r = walk(v)
                    if r:
                        return r
            elif isinstance(o, list):
                for v in o:
                    r = walk(v)
                    if r:
                        return r
            return None

        return walk(doc)
    return None


class RouterEngine(Engine):
    id = "router"
    label = "Comfy Router (partner models)"
    description = "Partner video/image models via Comfy Router. Costs credits; every run is estimated first and capped."
    kind = "router"
    partner = True

    def __init__(self, client_factory: Callable[[], Any] | None = None, http: httpx.Client | None = None, downloader: Callable[[str, Path], Path] | None = None, cap: float | None = None, router_url: str | None = None):
        self._client_factory = client_factory
        self._client: Any = None
        self._http = http
        self._download = downloader or self._default_download
        self._cap = cap
        self._router_url = (router_url or os.environ.get("COMFY_ROUTER_BASE_URL") or DEFAULT_ROUTER_URL).rstrip("/")

    # ------------------------------------------------------------ plumbing
    @property
    def cap(self) -> float:
        return self._cap if self._cap is not None else get_settings().max_credits_per_run

    def _api_key(self) -> str:
        return os.environ.get("COMFY_API_KEY", "").strip()

    def client(self):
        if self._client is None:
            if self._client_factory:
                self._client = self._client_factory()
            else:
                from comfy_sdk import Comfy

                self._client = Comfy()  # reads COMFY_API_KEY; Router host from COMFY_ROUTER_BASE_URL
        return self._client

    def health(self) -> Health:
        if get_settings().demo:
            return Health(False, "disabled", "Disabled while DEMO=1.")
        if not self._api_key() and not self._client_factory:
            return Health(False, "needs_setup", "COMFY_API_KEY is not set.", ["COMFY_API_KEY", "credits on the workspace"])
        return Health(True, "ready", f"Key present. Cap {self.cap:g} credits/run (~${self.cap / CREDITS_PER_USD:.2f}). Credits are not verified until a run.")

    def models(self) -> list[dict]:
        return [{"id": m, **info} for m, info in MODEL_INFO.items()]

    # ------------------------------------------------------------ estimate
    def _post_estimate(self, model: str, body: dict[str, Any]) -> dict[str, Any] | None:
        key = self._api_key()
        if not key and self._http is None:
            return None
        client = self._http or httpx.Client(timeout=15.0)
        try:
            r = client.post(f"{self._router_url}/v2/models/{model}/estimate", json=body, headers={"X-API-Key": key} if key else {})
        except httpx.HTTPError:
            return None
        finally:
            if self._http is None:
                client.close()
        if r.status_code == 402:
            raise E.InsufficientCredits("Not enough Comfy credits to run this.", hint="Nothing was run. Top up credits or use Demo mode.")
        if r.status_code in (401,):
            raise E.Unauthorized("Comfy rejected the API key.", hint="Check COMFY_API_KEY in .env.")
        if r.status_code != 200:
            return {"_status": r.status_code, "_type": r.headers.get("X-Comfy-Error-Type", "")}
        try:
            return r.json()
        except json.JSONDecodeError:
            return None

    def estimate_body(self, model: str, body: dict[str, Any], *, seconds: float, resolution: str, image: bool = False) -> Estimate:
        cap = self.cap
        doc = self._post_estimate(model, body)
        credits: float | None = None
        exact = False
        note = ""
        if doc and "_status" not in doc:
            src = doc.get("source")
            if src == "exact":
                credits = float(doc.get("credits", float(doc.get("amount", 0)) * CREDITS_PER_USD))
                exact = True
                note = f"Router /estimate (exact), rates as of {doc.get('pricing_as_of', '?')}"
            elif src == "estimated":
                credits = float(doc.get("max_amount", 0)) * CREDITS_PER_USD
                note = f"Router /estimate: upper bound (between ${doc.get('min_amount')} and ${doc.get('max_amount')})"
            else:
                note = f"Router could not price this ahead of time ({doc.get('reason', 'unknown')})"
        elif doc and doc.get("_type") == "not_enabled":
            note = "Router /estimate is not enabled for this workspace yet"
        if credits is None:
            usd = self._static_usd(model, seconds, resolution, image)
            if usd is not None:
                credits = usd * CREDITS_PER_USD
                note = (note + "; " if note else "") + "using the static price table in app/engines/router.py (may be stale)"
            else:
                note = (note + "; " if note else "") + "no price available"
        usd_v = credits / CREDITS_PER_USD if credits is not None else None
        over = credits is not None and credits > cap
        return Estimate(credits=round(credits, 2) if credits is not None else None, usd=round(usd_v, 4) if usd_v is not None else None, seconds=None, exact=exact, note=note, over_cap=over, cap=cap)

    @staticmethod
    def _static_usd(model: str, seconds: float, resolution: str, image: bool) -> float | None:
        if image:
            return STATIC_IMAGE_USD
        table = STATIC_PRICE_USD_PER_S.get(model)
        if not table:
            return None
        rate = table.get(resolution) or table.get("768P") or max(table.values())
        return rate * seconds

    def _shot_body(self, req: ShotRequest, model: str) -> tuple[dict[str, Any], list[str]]:
        overrides = (req.preset.get("engines", {}).get("router", {}).get("body_overrides") or {}) if model == req.preset.get("engines", {}).get("router", {}).get("model") else {}
        return build_video_body(model, prompt=req.prompt, image_url=image_data_url(req.source.path), duration=req.duration, resolution=req.resolution, seed=req.seed, negative=req.preset.get("negative", ""), overrides=overrides)

    def _pick_model(self, req: Any) -> str:
        if getattr(req, "model", None):
            return req.model
        preset = getattr(req, "preset", None)
        if preset:
            return preset.get("engines", {}).get("router", {}).get("model", DEFAULT_VIDEO_MODEL)
        return DEFAULT_VIDEO_MODEL

    def estimate(self, what: str, req) -> Estimate:
        if what == "shot":
            model = self._pick_model(req)
            body, notes = self._shot_body(req, model)
            est = self.estimate_body(model, body, seconds=body.get("duration", req.duration), resolution=body.get("resolution", req.resolution))
            if notes:
                est.note = (est.note + " | " if est.note else "") + "; ".join(notes)
            return est
        n = 1 if what == "reframe" else 6
        one = Estimate(credits=round(STATIC_IMAGE_USD * CREDITS_PER_USD * n, 2), usd=round(STATIC_IMAGE_USD * n, 3), seconds=None, exact=False, note=f"{n} FLUX 3 edit(s); static allowance, actual usage-based price is typically lower", cap=self.cap)
        one.over_cap = one.credits is not None and one.credits > self.cap
        return one

    # ------------------------------------------------------------ guard
    def _guard(self, est: Estimate) -> None:
        if est.over_cap:
            raise E.CapExceeded(f"Estimated cost {est.credits:g} credits (${est.usd}) is over your cap of {est.cap:g} credits per run.", hint="Pick a shorter duration or cheaper model, or raise MAX_CREDITS_PER_RUN in .env. Nothing was submitted.")
        if est.credits is None and os.environ.get("ALLOW_UNKNOWN_COST", "").strip().lower() not in {"1", "true", "yes"}:
            raise E.CapExceeded("Cannot verify the cost of this run, so the hard cap cannot be enforced.", hint="Pick a model with a known price, or set ALLOW_UNKNOWN_COST=1 in .env if you accept the risk. Nothing was submitted.")

    # ------------------------------------------------------------ run helpers
    def _default_download(self, url: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as r:
            r.raise_for_status()
            with open(dest, "wb") as fh:
                for chunk in r.iter_bytes(1 << 16):
                    fh.write(chunk)
        return dest

    def _run_model(self, model: str, body: dict[str, Any], emit: Emit, dest_stem: Path, ext: str) -> tuple[Path, str | None]:
        """Submit ONCE, poll, fetch, download immediately. Returns (file, request_id)."""
        client = self.client()
        try:
            handle = client.models.submit(model, body)  # NEVER retried here: a second call would be a second charge
        except Exception as exc:  # noqa: BLE001
            raise translate(exc) from exc
        rid = getattr(handle, "request_id", None)
        emit({"type": "status", "status": "queued", "request_id": rid, "message": f"Submitted to Comfy Router (request {rid}). Do not resubmit: check your Comfy dashboard if this page is lost."})
        try:
            t0 = time.time()
            for upd in handle.iter_events(timeout=900):
                pos = getattr(upd, "queue_position", None)
                done = getattr(upd, "is_completed", False)
                emit({"type": "status", "status": "completed" if done else (upd.status or "running").lower(), "queue_position": pos, "message": "Waiting in queue" + (f" (position {pos})" if pos else "") if not done else "Generation finished"})
                if not done:
                    emit({"type": "progress", "value": min(0.9, 0.1 + (time.time() - t0) / 240), "message": "Partner model is generating"})
            doc = handle.get()
        except Exception as exc:  # noqa: BLE001
            raise translate(exc) from exc
        content = getattr(doc, "content", None)
        if isinstance(content, (bytes, bytearray)):
            dest = dest_stem.with_suffix(ext)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(bytes(content))
            return dest, rid
        url = extract_media_url(doc)
        if not url:
            raise E.JobFailed("The model finished but returned no downloadable file.", hint=f"Request id {rid}. Check the Comfy dashboard; the result may still be billed.")
        emit({"type": "progress", "value": 0.95, "message": "Downloading result before the link expires"})
        try:
            return self._download(url, dest_stem.with_suffix(ext)), rid
        except Exception as exc:  # noqa: BLE001
            raise E.JobFailed("Generated, but downloading the result failed.", hint=f"Request id {rid}. The link expires in 12-24 h; fetch it from your Comfy dashboard.") from exc

    # ------------------------------------------------------------ engine API
    def run_shot(self, req: ShotRequest, emit: Emit, out_dir: Path) -> Result:
        model = self._pick_model(req)
        body, notes = self._shot_body(req, model)
        est = self.estimate_body(model, body, seconds=body.get("duration", req.duration), resolution=body.get("resolution", req.resolution))
        emit({"type": "estimate", "estimate": est.to_dict()})
        self._guard(est)
        file, rid = self._run_model(model, body, emit, out_dir / req.preset["id"], ".mp4")
        recipe = make_recipe(kind="shot", engine="router", model=model, source_name=req.source.name, source_sha256=sha256_file(req.source.path), preset_id=req.preset["id"], prompt=req.prompt, negative=req.preset.get("negative", ""), seed=req.seed, params={"duration": body.get("duration"), "resolution": body.get("resolution"), "notes": notes}, credits_used=est.credits, extra={"router_request_id": rid, "credits_used_is": "estimate (queued runs expose no X-Comfy-Credits-Used)"})
        return Result([Artifact("video", file, req.preset["name"], {"model": model})], recipe, est.credits)

    def reframe(self, req: ReframeRequest, emit: Emit, out_dir: Path) -> Result:
        est = self.estimate("reframe", req)
        emit({"type": "estimate", "estimate": est.to_dict()})
        self._guard(est)
        prompt = f"Re-shoot this exact scene from a different camera position: {angles.describe(req.angle)}. Keep the same subject, style, lighting and colours."
        body = build_image_body(prompt=prompt, image_url=image_data_url(req.source.path))
        file, rid = self._run_model(req.model or IMAGE_MODEL, body, emit, out_dir / "reframe", ".jpg")
        recipe = make_recipe(kind="reframe", engine="router", model=req.model or IMAGE_MODEL, source_name=req.source.name, source_sha256=sha256_file(req.source.path), prompt=prompt, seed=req.seed, params={"angle": vars(req.angle)}, credits_used=est.credits, extra={"router_request_id": rid})
        return Result([Artifact("image", file, angles.describe(req.angle))], recipe, est.credits)

    def coverage(self, req: CoverageRequest, emit: Emit, out_dir: Path) -> Result:
        est = self.estimate("coverage", req)
        emit({"type": "estimate", "estimate": est.to_dict()})
        self._guard(est)
        arts: list[Artifact] = []
        data = image_data_url(req.source.path)
        for i, shot in enumerate(angles.COVERAGE):
            prompt = f"Re-shoot this exact scene as a {angles.describe(shot['angle'])}. Keep the same subject, style, lighting and colours."
            file, _rid = self._run_model(req.model or IMAGE_MODEL, build_image_body(prompt=prompt, image_url=data), emit, out_dir / f"coverage-{shot['id']}", ".jpg")
            arts.append(Artifact("image", file, shot["label"], {"shot": shot["id"]}))
            emit({"type": "progress", "value": (i + 1) / 6, "message": f"Coverage: {shot['label']}"})
        recipe = make_recipe(kind="coverage", engine="router", model=req.model or IMAGE_MODEL, source_name=req.source.name, source_sha256=sha256_file(req.source.path), seed=req.seed, params={"shots": [s["id"] for s in angles.COVERAGE]}, credits_used=est.credits)
        return Result(arts, recipe, est.credits)
