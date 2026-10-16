"""scripts/smoke_real.py: estimate first, cap, confirm, exactly one submit, never retries. All with a fake engine (no network, no key use)."""

import importlib.util
from pathlib import Path

import pytest

from app.config import ROOT
from app.engines import router as router_mod
from app.types import Artifact, Estimate, Result

spec = importlib.util.spec_from_file_location("smoke_real", ROOT / "scripts" / "smoke_real.py")
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class FakeEngine:
    est = Estimate(credits=3.0, usd=0.014, seconds=None, exact=True, note="", over_cap=False, cap=10.0)
    runs = 0
    fail = False

    def __init__(self, cap=None, **kw):
        self.cap = cap

    def estimate(self, what, req):
        return self.est

    def run_shot(self, req, emit, out_dir):
        type(self).runs += 1
        if type(self).fail:
            raise RuntimeError("boom")
        emit({"message": "submitted"})
        p = Path(out_dir) / "x.mp4"
        p.write_bytes(b"x")
        return Result(artifacts=[Artifact("video", p)], recipe={"simulated": False}, credits_used=3.0)


@pytest.fixture(autouse=True)
def fake(monkeypatch, tmp_path):
    FakeEngine.runs, FakeEngine.fail = 0, False
    FakeEngine.est = Estimate(credits=3.0, usd=0.014, seconds=None, exact=True, note="", over_cap=False, cap=10.0)
    monkeypatch.setattr(router_mod, "RouterEngine", FakeEngine)
    monkeypatch.setenv("COMFY_API_KEY", "test-key-not-real")
    monkeypatch.delenv("DEMO", raising=False)
    monkeypatch.delenv("ALLOW_UNKNOWN_COST", raising=False)
    return tmp_path


def run(*args, tmp):
    return smoke.main([*args, "--out", str(tmp / "out")])


def test_requires_a_key(monkeypatch, fake):
    monkeypatch.delenv("COMFY_API_KEY")
    assert run(tmp=fake) == 2 and FakeEngine.runs == 0


def test_dry_run_submits_nothing(fake):
    assert run("--dry-run", tmp=fake) == 0 and FakeEngine.runs == 0


def test_over_cap_and_unknown_price_are_refused(fake):
    FakeEngine.est = Estimate(credits=40.0, usd=0.2, seconds=None, exact=True, note="", over_cap=True, cap=10.0)
    assert run("--yes", tmp=fake) == 3 and FakeEngine.runs == 0
    FakeEngine.est = Estimate(credits=None, usd=None, seconds=None, exact=False, note="", over_cap=False, cap=10.0)
    assert run("--yes", tmp=fake) == 3 and FakeEngine.runs == 0


def test_needs_explicit_confirmation(monkeypatch, fake):
    monkeypatch.setattr("builtins.input", lambda *_: "no")
    assert run(tmp=fake) == 1 and FakeEngine.runs == 0
    monkeypatch.setattr("builtins.input", lambda *_: "yes")
    assert run(tmp=fake) == 0 and FakeEngine.runs == 1


def test_exactly_one_submit_even_when_it_fails(fake):
    FakeEngine.fail = True
    assert run("--yes", tmp=fake) == 4
    assert FakeEngine.runs == 1  # never retried


def test_unknown_inputs_are_rejected_before_any_estimate(fake):
    assert run("--preset", "nope", tmp=fake) == 2 and run("--input", "nope", tmp=fake) == 2
