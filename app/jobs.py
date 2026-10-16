"""In-memory job store: run an engine call on a worker thread, stream its events over SSE."""

from __future__ import annotations

import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

from .errors import EngineError
from .types import Result


class Job:
    def __init__(self, kind: str, engine: str, label: str):
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.engine = engine
        self.label = label
        self.status = "queued"  # queued | running | done | error
        self.events: list[dict[str, Any]] = []
        self.result: dict[str, Any] | None = None
        self.error: dict[str, Any] | None = None
        self.created = time.time()
        self.lock = threading.Lock()

    def emit(self, ev: dict[str, Any]) -> None:
        with self.lock:
            ev = {**ev, "t": round(time.time() - self.created, 2)}
            self.events.append(ev)
            if ev.get("type") == "status" and ev.get("status") == "running":
                self.status = "running"

    def snapshot(self) -> dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "engine": self.engine, "label": self.label, "status": self.status, "result": self.result, "error": self.error, "n_events": len(self.events)}


class JobStore:
    def __init__(self, workers: int = 2, keep: int = 200):
        self.jobs: dict[str, Job] = {}
        self.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="job")
        self.keep = keep

    def submit(self, kind: str, engine: str, label: str, fn: Callable[[Callable[[dict], None], Path], Result], out_dir: Path, to_payload: Callable[[Result, Job], dict]) -> Job:
        job = Job(kind, engine, label)
        self.jobs[job.id] = job
        if len(self.jobs) > self.keep:
            for k in sorted(self.jobs, key=lambda k: self.jobs[k].created)[: len(self.jobs) - self.keep]:
                self.jobs.pop(k, None)

        def work() -> None:
            job.status = "running"
            job.emit({"type": "status", "status": "running", "message": "Started"})
            try:
                res = fn(job.emit, out_dir / job.id)
                payload = to_payload(res, job)
                with job.lock:
                    job.result = payload
                    job.status = "done"
                    job.events.append({"type": "done", "t": round(time.time() - job.created, 2)})
            except EngineError as e:
                with job.lock:
                    job.error = e.to_dict()
                    job.status = "error"
                    job.events.append({"type": "error", "error": job.error, "t": round(time.time() - job.created, 2)})
            except Exception as e:  # noqa: BLE001
                traceback.print_exc()
                with job.lock:
                    job.error = {"code": "internal_error", "message": f"Unexpected error: {type(e).__name__}", "hint": "See the server log.", "retryable": False}
                    job.status = "error"
                    job.events.append({"type": "error", "error": job.error, "t": round(time.time() - job.created, 2)})

        self.pool.submit(work)
        return job

    def get(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)
