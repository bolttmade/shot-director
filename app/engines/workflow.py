"""Workflow engine: ComfyUI API-format graphs run through `comfy_sdk.Comfy()`.

One adapter, three places to run the SAME graph, chosen only by env vars (SDK feature):

    COMFY_BASE_URL=http://127.0.0.1:8189      self-hosted ComfyUI behind `comfy-api-proxy` (no key, $0, open weights)
    COMFY_BASE_URL=https://<dep>.run.comfy.app  a Comfy API deployment (needs COMFY_API_KEY + a paid plan)
    (unset)                                   Comfy Cloud https://cloud.comfy.org (needs COMFY_API_KEY)

SDK surface used: client.workflows.from_file, client.assets.from_file, wf.set_input / remove_node,
client.submit(wf) once, job.events(), job.get_outputs(node).to_file(). Never wrapped in a retry loop.

STATUS: contract-tested against the real SDK classes with a fake client; NOT run against a live
server (no GPU / no credits on the dev box). The graphs in workflows/ are UNTESTED.
"""

from __future__ import annotations

import ipaddress
import json
import os
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

import httpx

from .. import angles, errors as E
from ..config import get_settings
from ..recipes import make_recipe, sha256_file, sha256_json
from ..types import Artifact, CoverageRequest, Emit, Estimate, Health, ReframeRequest, Result, ShotRequest
from .base import Engine
from .errmap import translate

CLOUD_URL = "https://cloud.comfy.org"
PROXY_URL = "http://127.0.0.1:8189"


def is_local_url(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    if host in ("localhost", ""):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_loopback or ip.is_private
    except ValueError:
        return host.endswith(".local") or host.endswith(".lan")


def frames_for(duration: float, fps: int = 24) -> int:
    """LTX needs 8n+1 frames."""
    n = max(1, round(duration * fps / 8))
    return n * 8 + 1


class WorkflowEngine(Engine):
    partner = False  # open-weights graphs only (checked by scripts/check_open_weights.py)

    def __init__(self, mode: str, client_factory: Callable[[], Any] | None = None, workflows_dir: Path | None = None, base_url: str | None = None, probe: Callable[[str], bool] | None = None):
        assert mode in ("open", "cloud")
        self.mode = mode
        self.id = mode
        self.kind = mode
        self.label = "Open weights (local ComfyUI via comfy-api-proxy)" if mode == "open" else "Comfy Cloud / API deployment"
        self.description = ("LTX-2 + camera LoRAs and Qwen-Image-Edit angle LoRA on your own GPU. $0, no partner nodes." if mode == "open" else "The same workflows on Comfy Cloud or a Comfy API deployment. Costs credits (GPU-seconds).")
        self._client_factory = client_factory
        self._client: Any = None
        self._dir = workflows_dir or get_settings().workflows_dir
        self._base_override = base_url
        self._probe = probe or self._default_probe

    # ---------------------------------------------------------------- config
    @property
    def base_url(self) -> str:
        if self._base_override is not None:
            return self._base_override
        return os.environ.get("COMFY_BASE_URL", "").strip() or CLOUD_URL

    def _is_my_target(self) -> bool:
        local = is_local_url(self.base_url)
        return local if self.mode == "open" else not local

    @staticmethod
    def _default_probe(url: str) -> bool:
        try:
            httpx.get(url, timeout=1.5)
            return True
        except httpx.HTTPError:
            return False

    def client(self):
        if self._client is None:
            if self._client_factory:
                self._client = self._client_factory()
            else:
                from comfy_sdk import Comfy

                self._client = Comfy(timeout=60.0)  # base URL + key come from the environment
        return self._client

    def health(self) -> Health:
        if get_settings().demo:
            return Health(False, "disabled", "Disabled while DEMO=1.")
        if not self._is_my_target():
            if self.mode == "open":
                return Health(False, "needs_setup", f"Set COMFY_BASE_URL={PROXY_URL} and run `comfy-api-proxy` next to a ComfyUI with the models from docs/MODELS.md.", ["comfy-api-proxy", "ComfyUI + LTX-2 models", "NVIDIA GPU (24 GB+ recommended)"])
            return Health(False, "needs_setup", "COMFY_BASE_URL points at a local server (Open engine). Unset it to target Comfy Cloud.", ["COMFY_API_KEY"])
        if self.mode == "open":
            if not self._probe(self.base_url):
                return Health(False, "unreachable", f"Nothing is answering at {self.base_url}. Start `comfy-api-proxy` (needs ComfyUI on :8188).", ["comfy-api-proxy running"])
            return Health(True, "ready", f"comfy-api-proxy reachable at {self.base_url}. Models are not verified until a run (see docs/MODELS.md).")
        if not os.environ.get("COMFY_API_KEY", "").strip() and not self._client_factory:
            return Health(False, "needs_setup", "COMFY_API_KEY is not set. Cloud API access needs a paid plan or an API deployment.", ["COMFY_API_KEY", "paid plan / deployment"])
        return Health(True, "ready", f"Target {self.base_url}. Credits are billed per GPU-second; cost is not known ahead of time.")

    # ---------------------------------------------------------------- estimate
    def estimate(self, what: str, req) -> Estimate:
        if self.mode == "open":
            secs = {"shot": 120 + 20 * getattr(req, "duration", 5), "reframe": 40, "coverage": 6 * 40}.get(what, 60)
            return Estimate(credits=0.0, usd=0.0, seconds=secs, exact=False, note="Runs on your own GPU: $0. Time is a rough guess for a 24 GB+ card.")
        cap = get_settings().max_credits_per_run
        return Estimate(credits=None, usd=None, seconds=None, exact=False, note="Cloud/deployment runs are billed per GPU-second; there is no pre-run quote. Set ALLOW_UNKNOWN_COST=1 to accept that.", cap=cap)

    def _guard(self, est: Estimate) -> None:
        if est.credits is None and os.environ.get("ALLOW_UNKNOWN_COST", "").strip().lower() not in {"1", "true", "yes"}:
            raise E.CapExceeded("Cloud/deployment cost cannot be quoted ahead of time, so the cap cannot be enforced.", hint="Set ALLOW_UNKNOWN_COST=1 in .env if you accept that, or use the Open-weights or Demo engine. Nothing was submitted.")

    # ---------------------------------------------------------------- core
    def _load(self, stem: str) -> tuple[Any, dict[str, Any], str]:
        gpath, mpath = self._dir / f"{stem}.json", self._dir / f"{stem}.meta.json"
        if not gpath.is_file() or not mpath.is_file():
            raise E.NotConfigured(f"Workflow '{stem}' is missing from workflows/.", hint="Run `python scripts/build_workflows.py`.")
        meta = json.loads(mpath.read_text())
        wf = self.client().workflows.from_file(gpath)
        return wf, meta, sha256_json(json.loads(gpath.read_text()))

    @staticmethod
    def _set(wf: Any, meta: dict[str, Any], key: str, value: Any) -> None:
        for node_id, field in meta["inputs"].get(key, []):
            wf.set_input(node_id, field, value)

    def _execute(self, wf: Any, meta: dict[str, Any], emit: Emit, dest: Path) -> Path:
        client = self.client()
        emit({"type": "status", "status": "queued", "message": f"Submitting workflow to {self.base_url}"})
        try:
            job = client.submit(wf)  # exactly once; never retried here (double-charge risk)
        except Exception as exc:  # noqa: BLE001
            raise translate(exc) from exc
        emit({"type": "status", "status": "queued", "job_id": getattr(job, "id", None), "message": f"Job {getattr(job, 'id', '?')} queued. Do not resubmit; look it up in Comfy if this page is lost."})
        try:
            for ev in job.events():
                kind = type(ev).__name__
                if kind == "Progress":
                    emit({"type": "progress", "value": float(ev.value), "message": ev.message or (f"step {ev.step}/{ev.steps}" if getattr(ev, "steps", None) else "sampling"), "step": getattr(ev, "step", None), "steps": getattr(ev, "steps", None)})
                elif kind == "StatusChange":
                    emit({"type": "status", "status": ev.status, "queue_position": getattr(ev, "queue_position", None)})
                elif kind == "Preview":
                    emit({"type": "log", "message": f"preview frame from node {ev.node_id}"})
                elif kind == "Log":
                    emit({"type": "log", "message": ev.message})
            job.result()  # waits for terminal and raises JobFailed unless it succeeded
            outs = job.get_outputs(meta["output_node"])
            if not outs:
                raise E.JobFailed("The job finished but produced no output.", hint=f"Output node {meta['output_node']} returned nothing. Check the workflow in ComfyUI.")
            dest.parent.mkdir(parents=True, exist_ok=True)
            outs[0].to_file(dest)  # download right away
        except E.EngineError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise translate(exc) from exc
        return dest

    # ---------------------------------------------------------------- engine API
    def run_shot(self, req: ShotRequest, emit: Emit, out_dir: Path) -> Result:
        est = self.estimate("shot", req)
        emit({"type": "estimate", "estimate": est.to_dict()})
        if self.mode == "cloud":
            self._guard(est)
        wp = req.preset["engines"]["workflow"]
        wf, meta, wf_hash = self._load(wp["workflow"])
        client = self.client()
        src = req.source.path
        if req.angle is not None:  # re-frame first, then use that still as the first frame
            rr = self.reframe(ReframeRequest(req.source, req.angle, req.scene, req.seed), emit, out_dir / "_reframe")
            src = rr.artifacts[0].path
        asset = client.assets.from_file(src)
        res = {"480p": (768, 448), "720p": (1280, 704)}.get(req.resolution, (1280, 704))
        lora = req.preset.get("lora")
        params = dict(wp.get("params", {}))
        self._set(wf, meta, "image", asset)
        self._set(wf, meta, "prompt", req.prompt)
        self._set(wf, meta, "negative", req.preset.get("negative", ""))
        self._set(wf, meta, "seed", req.seed)
        self._set(wf, meta, "width", res[0])
        self._set(wf, meta, "height", res[1])
        self._set(wf, meta, "frames", frames_for(req.duration))
        self._set(wf, meta, "cfg", float(params.get("cfg", 4.0)))
        if lora:
            self._set(wf, meta, "lora_name", lora["name"])
            self._set(wf, meta, "lora_strength", float(params.get("lora_strength", lora["strength"])))
        else:
            for nid in meta.get("lora_nodes", []):
                wf.remove_node(nid)  # SDK rewires consumers to the node's input
        dest = self._execute(wf, meta, emit, out_dir / f"{req.preset['id']}.mp4")
        recipe = make_recipe(kind="shot", engine=self.id, model="LTX-2 19B" + (f" + {lora['name']}" if lora else ""), source_name=req.source.name, source_sha256=sha256_file(req.source.path), preset_id=req.preset["id"], prompt=req.prompt, negative=req.preset.get("negative", ""), seed=req.seed, params={"resolution": f"{res[0]}x{res[1]}", "frames": frames_for(req.duration), "angle": vars(req.angle) if req.angle else None, "base_url_kind": self.mode}, workflow_sha256=wf_hash, credits_used=0.0 if self.mode == "open" else None)
        return Result([Artifact("video", dest, req.preset["name"], {"model": "LTX-2"})], recipe, 0.0 if self.mode == "open" else None)

    def _angle_image(self, source_path: Path, angle, seed: int, emit: Emit, dest: Path) -> tuple[Path, str]:
        wf, meta, wf_hash = self._load("qwen_edit_angle")
        client = self.client()
        self._set(wf, meta, "image", client.assets.from_file(source_path))
        self._set(wf, meta, "prompt", angles.qwen_prompt(angle))
        self._set(wf, meta, "seed", seed)
        return self._execute(wf, meta, emit, dest), wf_hash

    def reframe(self, req: ReframeRequest, emit: Emit, out_dir: Path) -> Result:
        est = self.estimate("reframe", req)
        if self.mode == "cloud":
            self._guard(est)
        dest, h = self._angle_image(req.source.path, req.angle, req.seed, emit, out_dir / "reframe.png")
        recipe = make_recipe(kind="reframe", engine=self.id, model="Qwen-Image-Edit-2511 + Multiple-Angles LoRA", source_name=req.source.name, source_sha256=sha256_file(req.source.path), prompt=angles.qwen_prompt(req.angle), seed=req.seed, params={"angle": vars(req.angle), "snapped": vars(angles.snap_angle(req.angle))}, workflow_sha256=h)
        return Result([Artifact("image", dest, angles.describe(req.angle))], recipe, 0.0 if self.mode == "open" else None)

    def coverage(self, req: CoverageRequest, emit: Emit, out_dir: Path) -> Result:
        est = self.estimate("coverage", req)
        if self.mode == "cloud":
            self._guard(est)
        arts, h = [], ""
        for i, shot in enumerate(angles.COVERAGE):
            dest, h = self._angle_image(req.source.path, shot["angle"], req.seed, emit, out_dir / f"coverage-{shot['id']}.png")
            arts.append(Artifact("image", dest, shot["label"], {"shot": shot["id"]}))
            emit({"type": "progress", "value": (i + 1) / 6, "message": f"Coverage: {shot['label']}"})
        recipe = make_recipe(kind="coverage", engine=self.id, model="Qwen-Image-Edit-2511 + Multiple-Angles LoRA", source_name=req.source.name, source_sha256=sha256_file(req.source.path), seed=req.seed, params={"shots": [s["id"] for s in angles.COVERAGE]}, workflow_sha256=h)
        return Result(arts, recipe, 0.0 if self.mode == "open" else None)
