"""Router adapter contract tests: recorded response shapes, a fake SDK client, a mocked /estimate."""

import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from app import errors as E
from app.engines import router as R
from app.engines.errmap import translate
from app.types import ReframeRequest, ShotRequest, Angle


class Handle:
    request_id = "req_123"

    def __init__(self, doc):
        self._doc = doc

    def iter_events(self, timeout=None):
        yield SimpleNamespace(status="QUEUED", queue_position=2, is_completed=False)
        yield SimpleNamespace(status="COMPLETED", queue_position=None, is_completed=True)

    def get(self):
        return self._doc


class FakeClient:
    def __init__(self, doc=None, exc=None):
        self.submits = []
        self.models = SimpleNamespace(submit=self._submit)
        self._doc, self._exc = doc or {"result": {"video_url": "https://cdn.example/out.mp4"}}, exc

    def _submit(self, model, body):
        self.submits.append((model, body))
        if self._exc:
            raise self._exc
        return Handle(self._doc)


def est_transport(payload, status=200, headers=None):
    calls = []

    def handler(req: httpx.Request):
        calls.append(req)
        return httpx.Response(status, json=payload, headers=headers or {})

    return httpx.Client(transport=httpx.MockTransport(handler)), calls


def dl(url, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"\x00\x00\x00 ftypmp42")
    return dest


def shot(source, preset, **kw):
    return ShotRequest(source=source, preset=preset, duration=kw.pop("duration", 5), prompt="a prompt", **kw)


def engine(client=None, http=None, cap=50.0):
    return R.RouterEngine(client_factory=lambda: client, http=http, downloader=dl, cap=cap)


def test_estimate_uses_router_estimate_and_is_exact(sample_source, preset, monkeypatch):
    monkeypatch.setenv("COMFY_API_KEY", "test-key-not-real")
    http, calls = est_transport({"source": "exact", "amount": 0.25, "credits": 52.75, "pricing_as_of": "2026-10-01"})
    e = engine(FakeClient(), http).estimate("shot", shot(sample_source, preset))
    assert e.exact and e.credits == 52.75 and e.over_cap  # 52.75 > default cap of 50
    assert calls and calls[0].url.path == "/v2/models/minimax/minimax-h3/estimate"
    assert calls[0].headers["x-api-key"] == "test-key-not-real"


def test_estimate_falls_back_to_static_table_when_not_enabled(sample_source, preset, monkeypatch):
    monkeypatch.setenv("COMFY_API_KEY", "k")
    http, _ = est_transport({"error": "x"}, status=403, headers={"X-Comfy-Error-Type": "not_enabled"})
    e = engine(FakeClient(), http).estimate("shot", shot(sample_source, preset, duration=5))
    assert not e.exact and e.credits is not None and "static price table" in e.note
    assert e.credits == pytest.approx(0.1287 * 5 * 211, abs=0.05)


def test_cap_blocks_submit(sample_source, preset, monkeypatch, tmp_path):
    monkeypatch.setenv("COMFY_API_KEY", "k")
    http, _ = est_transport({"source": "exact", "amount": 5.0, "credits": 1055.0})
    client = FakeClient()
    with pytest.raises(E.CapExceeded):
        engine(client, http, cap=50).run_shot(shot(sample_source, preset), lambda ev: None, tmp_path)
    assert client.submits == []  # nothing was sent


def test_unknown_cost_refused_unless_allowed(sample_source, preset, monkeypatch, tmp_path):
    monkeypatch.setenv("COMFY_API_KEY", "k")
    http, _ = est_transport({"source": "unknown", "reason": "no_rate"})
    preset = {**preset, "engines": {**preset["engines"], "router": {**preset["engines"]["router"], "model": "someone/unpriced-model"}}}
    client = FakeClient()
    with pytest.raises(E.CapExceeded):
        engine(client, http).run_shot(shot(sample_source, preset), lambda ev: None, tmp_path)
    assert client.submits == []
    monkeypatch.setenv("ALLOW_UNKNOWN_COST", "1")
    engine(client, http).run_shot(shot(sample_source, preset), lambda ev: None, tmp_path)
    assert len(client.submits) == 1


def test_happy_path_submits_exactly_once_and_downloads(sample_source, preset, monkeypatch, tmp_path):
    monkeypatch.setenv("COMFY_API_KEY", "k")
    http, _ = est_transport({"source": "exact", "amount": 0.2, "credits": 42.2})
    client, events = FakeClient(), []
    res = engine(client, http).run_shot(shot(sample_source, preset), events.append, tmp_path)
    assert len(client.submits) == 1
    model, body = client.submits[0]
    assert model == "minimax/minimax-h3" and body["content"][1]["role"] == "first_frame" and body["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert res.artifacts[0].path.is_file() and res.artifacts[0].kind == "video"
    assert res.recipe["router_request_id"] == "req_123" and res.credits_used == 42.2
    assert any(e.get("request_id") == "req_123" for e in events)  # request id surfaced immediately
    assert "test-key" not in json.dumps(res.recipe)


def test_submit_error_is_translated_and_not_retried(sample_source, preset, monkeypatch, tmp_path):
    monkeypatch.setenv("COMFY_API_KEY", "k")
    http, _ = est_transport({"source": "exact", "amount": 0.2, "credits": 42.2})
    class InsufficientCredits(Exception):
        pass
    client = FakeClient(exc=InsufficientCredits("402"))
    with pytest.raises(E.InsufficientCredits) as ei:
        engine(client, http).run_shot(shot(sample_source, preset), lambda ev: None, tmp_path)
    assert len(client.submits) == 1 and "Nothing was run" in ei.value.to_dict()["hint"]


def test_no_media_url_is_a_clean_failure(sample_source, preset, monkeypatch, tmp_path):
    monkeypatch.setenv("COMFY_API_KEY", "k")
    http, _ = est_transport({"source": "exact", "amount": 0.2, "credits": 42.2})
    with pytest.raises(E.JobFailed):
        engine(FakeClient(doc={"status": "ok"}), http).run_shot(shot(sample_source, preset), lambda ev: None, tmp_path)


def test_ltx_via_router_warns_it_ignores_the_still():
    body, notes = R.build_video_body("ltx/ltx-2-5-fast", prompt="p", image_url="data:x", duration=5, resolution="720p")
    assert "image" not in body and any("text-to-video only" in n for n in notes)


def test_provider_body_shapes():
    b, _ = R.build_video_body("xai/grok-imagine-video-1.5-lite", prompt="p", image_url="data:x", duration=5, resolution="480p")
    assert b["image"] == {"type": "image_url", "url": "data:x"} and b["resolution"] == "480p"
    b, n = R.build_video_body("minimax/minimax-h3", prompt="p", image_url="data:x", duration=2, resolution="720p")
    assert b["duration"] == 4 and n  # minimum duration clamp is reported


@pytest.mark.parametrize("doc,url", [
    ({"result": {"video_url": "https://a/b.mp4"}}, "https://a/b.mp4"),
    ({"content": {"video_url": "https://a/c.mp4"}}, "https://a/c.mp4"),
    ({"video": {"url": "https://a/d.mp4"}}, "https://a/d.mp4"),
    ({"deep": [{"x": {"image_url": "https://a/e.png"}}]}, "https://a/e.png"),
    ({"nothing": 1}, None),
])
def test_extract_media_url(doc, url):
    assert R.extract_media_url(doc) == url


def test_reframe_is_capped_too(sample_source, tmp_path):
    client = FakeClient(doc={"sample": "https://a/img.jpg"})
    eng = R.RouterEngine(client_factory=lambda: client, downloader=dl, cap=1.0)
    with pytest.raises(E.CapExceeded):
        eng.reframe(ReframeRequest(sample_source, Angle(45, 0, "close")), lambda e: None, tmp_path)
    assert client.submits == []


def test_health_needs_key():
    h = R.RouterEngine().health()
    assert not h.ok and "COMFY_API_KEY" in h.needs


def test_translate_unknown_exception_is_friendly():
    e = translate(RuntimeError("boom"))
    assert isinstance(e, E.JobFailed) and "Traceback" not in e.message


def test_seedance_first_frame_omits_ratio_and_text_only_keeps_it():
    sd = "byteplus/dreamina-seedance-2-5-260628"
    b, n = R.build_video_body(sd, prompt="p", image_url="data:x", duration=5, resolution="720p")
    assert "ratio" not in b  # a concrete ratio with a first frame is refused with 400 by the Router
    assert b["content"][1]["role"] == "first_frame" and any("ratio" in x for x in n)
    t, _ = R.build_video_body(sd, prompt="p", image_url=None, duration=5, resolution="720p")
    assert t["ratio"] == "16:9"
