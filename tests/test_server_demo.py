"""End-to-end API tests in DEMO mode: no keys, no network, no GPU."""

import io
import json
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.server import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DEMO", "1")
    return TestClient(create_app())


def wait(client, job, timeout=90):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = client.get(f"/api/jobs/{job['id']}").json()
        if j["status"] in ("done", "error"):
            return j
        time.sleep(0.2)
    raise AssertionError("job timed out")


def test_index_and_static(client):
    r = client.get("/")
    assert r.status_code == 200 and "Shot Director" in r.text
    assert client.get("/static/app.js").status_code == 200 and client.get("/static/style.css").status_code == 200
    assert "http" not in "".join(l for l in r.text.splitlines() if "<script" in l or "<link rel=\"stylesheet\"" in l).replace("http://www.w3.org", "")  # no CDN assets


def test_config_engines_presets_samples(client):
    cfg = client.get("/api/config").json()
    assert cfg["demo"] is True and "simulated" in cfg["badge"]
    eng = client.get("/api/engines").json()
    assert eng["default"] == "demo"
    by = {e["id"]: e for e in eng["engines"]}
    assert by["demo"]["health"]["ok"] and not any(by[k]["health"]["ok"] for k in by if k != "demo")
    assert len(client.get("/api/presets").json()["presets"]) >= 14
    assert len(client.get("/api/samples").json()["samples"]) >= 4


def test_paid_engines_are_refused_in_demo(client):
    r = client.post("/api/shots", json={"source_id": "sample:alpine-dusk", "preset_id": "dolly-in", "engine": "router", "confirm_cost": True})
    assert r.status_code == 409 and "DEMO" in r.json()["message"]


def test_shot_replays_committed_clip_and_is_labelled_simulated(client):
    r = client.post("/api/shots", json={"source_id": "sample:alpine-dusk", "preset_id": "dolly-in", "engine": "demo"})
    assert r.status_code == 200
    j = wait(client, r.json())
    assert j["status"] == "done", j
    res = j["result"]
    assert res["simulated"] is True and res["recipe"]["simulated"] is True
    vid = res["artifacts"][0]
    assert vid["kind"] == "video" and "simulated" in vid["label"].lower()
    assert client.get(vid["url"]).status_code == 200 and client.get(res["recipe_url"]).status_code == 200
    # SSE stream terminates with a done event
    body = client.get(f"/api/jobs/{r.json()['id']}/events").text
    assert '"type": "done"' in body


def test_reframe_and_adopt_and_coverage(client):
    r = client.post("/api/reframe", json={"source_id": "sample:neon-rooftops", "engine": "demo", "angle": {"azimuth": 30, "elevation": 30, "distance": "medium"}})
    j = wait(client, r.json())
    assert j["status"] == "done" and j["result"]["artifacts"][0]["kind"] == "image" and j["result"]["simulated"]
    a = client.post("/api/adopt", json={"url": j["result"]["artifacts"][0]["url"]}).json()
    assert a["id"].startswith("upload:") and client.get(a["url"]).status_code == 200
    c = client.post("/api/coverage", json={"source_id": a["id"], "engine": "demo"})
    jc = wait(client, c.json())
    assert jc["status"] == "done" and [a["label"] for a in jc["result"]["artifacts"]][:2] == ["Wide", "Medium"] and len(jc["result"]["artifacts"]) == 6


def test_upload_validation(client):
    bad = client.post("/api/upload", files={"file": ("x.png", b"not an image", "image/png")})
    assert bad.status_code == 415 and bad.json()["message"]
    buf = io.BytesIO()
    Image.new("RGB", (320, 180), (200, 100, 50)).save(buf, "PNG")
    ok = client.post("/api/upload", files={"file": ("pic.png", buf.getvalue(), "image/png")})
    assert ok.status_code == 200 and ok.json()["id"].startswith("upload:")


def test_unknown_ids_are_clean_404s(client):
    assert client.post("/api/shots", json={"source_id": "sample:nope", "preset_id": "dolly-in"}).status_code == 404
    assert client.post("/api/shots", json={"source_id": "sample:alpine-dusk", "preset_id": "nope"}).status_code == 404
    assert client.get("/api/jobs/zzz").status_code == 404


def test_sequence_stitches_and_rejects_traversal(client):
    clips = [f"/examples/outputs/clips/{n}.mp4" for n in ("alpine-dusk__dolly-in", "neon-rooftops__jib-up")]
    r = client.post("/api/sequence", json={"clips": clips, "crossfade": 0.4})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["recipe"]["simulated"] is True and client.get(d["url"]).status_code == 200
    assert client.post("/api/sequence", json={"clips": ["/examples/../app/server.py"]}).status_code in (400, 404)
    assert client.post("/api/sequence", json={"clips": ["/etc/passwd"]}).status_code == 400


def test_estimate_is_free_in_demo(client):
    e = client.post("/api/estimate", json={"source_id": "sample:alpine-dusk", "preset_id": "orbit-left", "engine": "demo"}).json()
    assert e["credits"] == 0 and e["exact"]


def test_gallery_manifest_points_at_real_files(client):
    items = client.get("/api/gallery").json()["items"]
    assert len([i for i in items if i["kind"] == "clip"]) >= 12
    for it in items:
        if it["kind"] == "clip":
            assert client.get(it["url"]).status_code == 200
