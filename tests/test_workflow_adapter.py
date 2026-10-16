"""Workflow adapter contract tests against a fake comfy_sdk client (real graphs, real meta)."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import errors as E
from app.config import ROOT
from app.engines.workflow import WorkflowEngine, frames_for, is_local_url
from app.types import Angle, CoverageRequest, ReframeRequest, ShotRequest


class FakeWF:
    def __init__(self, graph):
        self.graph, self.removed = graph, []

    def set_input(self, node, field, value):
        assert field in self.graph[node]["inputs"], f"node {node} has no input {field}"
        self.graph[node]["inputs"][field] = value

    def remove_node(self, nid):
        self.removed.append(nid)


class Progress:
    value, message, step, steps = 0.5, "", 3, 6


class Out:
    def to_file(self, dest):
        Path(dest).write_bytes(b"data")


class FakeJob:
    id = "job-1"

    def __init__(self, outputs):
        self._outputs = outputs

    def events(self):
        yield Progress()

    def result(self):
        return self

    def get_outputs(self, node):
        return self._outputs


class FakeClient:
    def __init__(self, outputs=None, fail=None):
        self.submitted, self.wfs, self.fail = [], [], fail
        self.workflows = SimpleNamespace(from_file=self._from_file)
        self.assets = SimpleNamespace(from_file=lambda p: f"asset:{Path(p).name}")
        self._outputs = [Out()] if outputs is None else outputs

    def _from_file(self, p):
        wf = FakeWF(json.loads(Path(p).read_text()))
        self.wfs.append(wf)
        return wf

    def submit(self, wf):
        if self.fail:
            raise self.fail
        self.submitted.append(wf)
        return FakeJob(self._outputs)


def eng(client, mode="open", base="http://127.0.0.1:8189"):
    return WorkflowEngine(mode, client_factory=lambda: client, base_url=base, probe=lambda u: True)


def test_is_local_url():
    assert is_local_url("http://127.0.0.1:8189") and is_local_url("http://192.168.1.5:8188") and is_local_url("http://localhost:8188")
    assert not is_local_url("https://cloud.comfy.org") and not is_local_url("https://abc.run.comfy.app")


def test_frames_are_8n_plus_1():
    assert all((frames_for(d) - 1) % 8 == 0 for d in (1, 2.5, 3, 5, 10))
    assert frames_for(5) == 121


def test_shot_sets_inputs_via_meta_and_submits_once(sample_source, preset, tmp_path):
    c = FakeClient()
    req = ShotRequest(source=sample_source, preset=preset, prompt="PROMPT", seed=11, duration=5, resolution="720p")
    res = eng(c).run_shot(req, lambda e: None, tmp_path)
    assert len(c.submitted) == 1
    g = c.wfs[0].graph
    assert g["4"]["inputs"]["image"] == "asset:alpine-dusk.jpg"
    assert g["8"]["inputs"]["text"] == "PROMPT" and g["24"]["inputs"]["noise_seed"] == 11
    assert g["20"]["inputs"]["value"] == 121 and g["12"]["inputs"]["width"] == 1280
    assert g["5"]["inputs"]["lora_name"] == preset["lora"]["name"]
    assert res.artifacts[0].path.is_file() and res.recipe["engine"] == "open" and res.credits_used == 0.0


def test_preset_without_lora_removes_lora_nodes(sample_source, preset, tmp_path):
    c = FakeClient()
    p = {k: v for k, v in preset.items() if k != "lora"}
    eng(c).run_shot(ShotRequest(source=sample_source, preset=p, prompt="x"), lambda e: None, tmp_path)
    assert set(c.wfs[0].removed) == {"5", "7"}


def test_angle_workflow_prompt_is_qwen_vocab(sample_source, tmp_path):
    c = FakeClient()
    res = eng(c).reframe(ReframeRequest(sample_source, Angle(90, 30, "close"), seed=5), lambda e: None, tmp_path)
    assert c.wfs[0].graph["112"]["inputs"]["prompt"] == "<sks> right side view elevated shot close-up"
    assert res.artifacts[0].kind == "image"


def test_coverage_runs_six_workflows(sample_source, tmp_path):
    c = FakeClient()
    res = eng(c).coverage(CoverageRequest(sample_source), lambda e: None, tmp_path)
    assert len(c.submitted) == 6 and len(res.artifacts) == 6


def test_empty_output_is_clean_error(sample_source, preset, tmp_path):
    with pytest.raises(E.JobFailed):
        eng(FakeClient(outputs=[])).run_shot(ShotRequest(source=sample_source, preset=preset, prompt="x"), lambda e: None, tmp_path)


def test_submit_failure_is_translated(sample_source, preset, tmp_path):
    with pytest.raises(E.EngineError):
        eng(FakeClient(fail=RuntimeError("down"))).run_shot(ShotRequest(source=sample_source, preset=preset, prompt="x"), lambda e: None, tmp_path)


def test_cloud_refuses_unquoted_cost_by_default(sample_source, preset, tmp_path, monkeypatch):
    c = FakeClient()
    cloud = eng(c, "cloud", "https://cloud.comfy.org")
    with pytest.raises(E.CapExceeded):
        cloud.run_shot(ShotRequest(source=sample_source, preset=preset, prompt="x"), lambda e: None, tmp_path)
    assert c.submitted == []
    monkeypatch.setenv("ALLOW_UNKNOWN_COST", "1")
    cloud.run_shot(ShotRequest(source=sample_source, preset=preset, prompt="x"), lambda e: None, tmp_path)
    assert len(c.submitted) == 1


def test_health_states(monkeypatch):
    assert WorkflowEngine("open", base_url="https://cloud.comfy.org").health().status == "needs_setup"
    assert WorkflowEngine("open", base_url="http://127.0.0.1:8189", probe=lambda u: False).health().status == "unreachable"
    assert WorkflowEngine("open", base_url="http://127.0.0.1:8189", probe=lambda u: True).health().ok
    assert WorkflowEngine("cloud", base_url="https://cloud.comfy.org").health().needs  # no key
