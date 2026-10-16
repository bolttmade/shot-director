"""Real-clip drop folder: importer, detection, Demo-engine preference, UI-facing API labels."""

import importlib.util
import json
import shutil
import subprocess
import time

import pytest
from fastapi.testclient import TestClient

from app import real as realmod
from app.config import ROOT
from app.engines.fixtures import FixturesEngine
from app.media import ffmpeg_bin
from app.presets import build_prompt, load_presets
from app.samples import sample_source
from app.server import create_app
from app.types import ShotRequest

spec = importlib.util.spec_from_file_location("import_real", ROOT / "scripts" / "import_real.py")
imp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imp)

INPUTS, PRESETS = ROOT / "examples" / "inputs", ROOT / "presets"


def make_mp4(path, size="320x180", secs=1.2, audio=False):
    cmd = [ffmpeg_bin(), "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"testsrc=size={size}:rate=12:duration={secs}"]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={secs}", "-c:a", "aac", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(cmd, check=True)
    return path


def do_import(path, real_dir, **kw):
    return imp.import_clip(path, real_dir=real_dir, inputs_dir=INPUTS, presets_dir=PRESETS, **kw)


def test_alley_input_exists_and_is_listed():
    s = sample_source("alley")
    assert s.path.is_file() and s.depth_path is not None and s.depth_path.is_file()


def test_parse_name():
    assert realmod.parse_name("alley__dolly-in.mp4") == ("alley", "dolly-in")
    assert realmod.parse_name("alley__dolly-in__router-x.mp4") == ("alley", "dolly-in") and realmod.parse_variant("alley__dolly-in__router-x.mp4") == "router-x"
    assert realmod.parse_variant("alley__dolly-in.mp4") is None
    for bad in ("alley.mp4", "Alley__dolly-in.mp4", "alley__dolly_in.mp4", "alley__dolly-in.mov", "a__b__c__d.mp4", "a__b__C.mp4"):
        assert realmod.parse_name(bad) is None


def test_import_writes_recipe_with_real_provenance(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    clip = make_mp4(real / "alley__dolly-in.mp4", audio=True)
    (real / "alley__dolly-in.json").write_text(json.dumps({"seed": 20261016, "resolution": "1280x720", "duration": 5, "template": "LTX-2.3: Image to Video", "date": "2026-10-17", "prompt": "p", "credits_used": 0}))
    r = do_import(clip, real)
    assert r["status"] == "metadata-stripped" and r["notes"]
    rec = json.loads((real / "alley__dolly-in.recipe.json").read_text())
    assert rec["simulated"] is False and rec["provenance"] == "real LTX-2.3 output via Comfy Cloud web UI"
    assert rec["badge"] == "Real LTX-2.3 output (Comfy Cloud)" and rec["seed"] == 20261016 and rec["preset"] == "dolly-in"
    assert rec["source"]["sha256"] and rec["output_sha256"] and rec["run_date"] == "2026-10-17"
    assert imp.import_clip(clip, real_dir=real, inputs_dir=INPUTS, presets_dir=PRESETS)["status"] == "unchanged"


def test_import_copies_in_from_elsewhere_and_flags_missing_notes(tmp_path):
    (tmp_path / "dl").mkdir()
    src = make_mp4(tmp_path / "dl" / "alley__orbit-left.mp4")
    real = tmp_path / "real"
    do_import(src, real)
    assert (real / "alley__orbit-left.mp4").is_file()
    assert json.loads((real / "alley__orbit-left.recipe.json").read_text())["notes_missing"] is True


@pytest.mark.parametrize("name,msg", [("alley.mp4", "does not match"), ("nowhere__dolly-in.mp4", "unknown input"), ("alley__no-such-move.mp4", "unknown preset")])
def test_import_rejects_bad_names(tmp_path, name, msg):
    clip = make_mp4(tmp_path / name)
    with pytest.raises(imp.ImportError_, match=msg):
        do_import(clip, tmp_path / "real")


def test_import_rejects_non_video(tmp_path):
    bad = tmp_path / "alley__crane-up.mp4"
    bad.write_text("not a video")
    with pytest.raises(imp.ImportError_):
        do_import(bad, tmp_path / "real")


def test_import_transcodes_oversize_and_keeps_original(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    big = make_mp4(real / "alley__crane-up.mp4", size="1920x1080", secs=1.0)
    r = do_import(big, real)
    assert r["status"] == "transcoded" and r["width"] <= 1280 and r["mb"] <= 6.0
    assert (real / "_originals" / "alley__crane-up.mp4").is_file()
    rec = json.loads((real / "alley__crane-up.recipe.json").read_text())
    assert rec["transcoded"] is True and rec["original_sha256"] != rec["output_sha256"]


def test_scan_find_and_effective_recipe(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    make_mp4(real / "alley__dolly-in.mp4")
    (real / "notes.mp4").write_bytes(b"x")  # ignored: bad name
    (real / "alley__arc.mp4").write_bytes(b"")  # ignored: empty
    clips = realmod.scan(real)
    assert [c.id for c in clips] == ["alley__dolly-in"] and not clips[0].imported
    rec = clips[0].effective_recipe()
    assert rec["simulated"] is False and "NOT yet imported" in rec["provenance"]
    assert realmod.find("alley", "dolly-in", real) and realmod.find("alley", "orbit-left", real) is None and realmod.find(None, "dolly-in", real) is None


def run_shot(engine, tmp_path, preset_id="dolly-in", scene=""):
    presets = load_presets()
    p = presets[preset_id]
    req = ShotRequest(source=sample_source("alley"), preset=p, scene=scene, prompt=build_prompt(p, scene=scene))
    events = []
    return engine.run_shot(req, events.append, tmp_path / "job"), events


def test_demo_engine_prefers_real_clip_and_labels_it(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    make_mp4(real / "alley__dolly-in.mp4")
    do_import(real / "alley__dolly-in.mp4", real)
    eng = FixturesEngine(outputs=tmp_path / "outputs", real_dir=real)
    res, events = run_shot(eng, tmp_path)
    art = res.artifacts[0]
    assert art.meta["real"] is True and art.meta["simulated"] is False and "Real LTX-2.3" in art.meta["label"]
    assert res.recipe["simulated"] is False and res.recipe["replayed_from"] == "real/alley__dolly-in.mp4"
    assert art.path.is_file() and any("generated earlier, not now" in (e.get("message") or "") for e in events)


def test_real_clip_is_not_used_when_the_request_is_customised(tmp_path, monkeypatch):
    """A custom scene text / angle can't be served by a pre-made clip, so it must NOT be presented as the real one."""
    real = tmp_path / "real"
    real.mkdir()
    make_mp4(real / "alley__dolly-in.mp4")
    eng = FixturesEngine(outputs=tmp_path / "outputs", real_dir=real)
    called = {}

    def fake_encode(frames, out, **kw):
        called["live"] = True
        next(iter(frames))
        out.write_bytes(b"x")

    monkeypatch.setattr("app.engines.fixtures.encode_frames", fake_encode)
    res, _ = run_shot(eng, tmp_path, scene="a custom scene")
    assert called.get("live") and res.recipe["simulated"] is True


@pytest.fixture
def client(monkeypatch, tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    make_mp4(real / "alley__dolly-in.mp4")
    do_import(real / "alley__dolly-in.mp4", real)
    monkeypatch.setenv("DEMO", "1")
    monkeypatch.setenv("REAL_DIR", str(real))
    return TestClient(create_app())


def wait(c, job, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = c.get(f"/api/jobs/{job['id']}").json()
        if j["status"] in ("done", "error"):
            return j
        time.sleep(0.15)
    raise AssertionError("timeout")


def test_gallery_lists_real_first_with_distinct_flags(client):
    items = client.get("/api/gallery").json()["items"]
    assert items[0]["real"] is True and items[0]["simulated"] is False and items[0]["badge"] == "Real LTX-2.3 output (Comfy Cloud)"
    sim = [i for i in items if not i.get("real") and i["kind"] == "clip"]
    assert len(sim) >= 12 and all(i["simulated"] is True for i in sim)


def test_shot_api_returns_real_flag_and_badge(client):
    r = client.post("/api/shots", json={"source_id": "sample:alley", "preset_id": "dolly-in", "engine": "demo"})
    j = wait(client, r.json())
    assert j["status"] == "done", j
    res = j["result"]
    assert res["real"] is True and res["simulated"] is False and "Real LTX-2.3" in res["badge"]
    # same sample, a move without a real clip: simulated, not real
    r2 = client.post("/api/shots", json={"source_id": "sample:alpine-dusk", "preset_id": "dolly-in", "engine": "demo"})
    res2 = wait(client, r2.json())["result"]
    assert res2["simulated"] is True and res2["real"] is False and res2["badge"] is None


def test_sequence_of_real_plus_simulated_is_marked_simulated(client):
    real_url = wait(client, client.post("/api/shots", json={"source_id": "sample:alley", "preset_id": "dolly-in", "engine": "demo"}).json())["result"]["artifacts"][0]["url"]
    only_real = client.post("/api/sequence", json={"clips": [real_url]}).json()
    assert only_real["recipe"]["simulated"] is False and only_real["recipe"]["params"]["real_clips"] == 1
    mixed = client.post("/api/sequence", json={"clips": [real_url, "/examples/outputs/clips/alpine-dusk__dolly-in.mp4"], "crossfade": 0.4}).json()
    assert mixed["recipe"]["simulated"] is True and "SIMULATED" in mixed["recipe"]["provenance"] and mixed["recipe"]["params"]["real_clips"] == 1


def test_cli_check_mode_changes_nothing(tmp_path, capsys):
    real = tmp_path / "real"
    real.mkdir()
    make_mp4(real / "alley__dolly-in.mp4")
    assert imp.main(["--dir", str(real), "--check"]) == 0
    assert not (real / "alley__dolly-in.recipe.json").exists()
    assert "alley__dolly-in.mp4" in capsys.readouterr().out
    shutil.copy(real / "alley__dolly-in.mp4", real / "bad.mp4")
    assert imp.main(["--dir", str(real), "--check"]) == 1


def _tags(path):
    out = subprocess.run([imp.ffprobe_bin(), "-v", "error", "-show_entries", "format_tags", "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    return json.loads(out).get("format", {}).get("tags", {})


def test_import_strips_container_metadata_and_keeps_original(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    clip = real / "alley__dolly-in.mp4"
    subprocess.run([ffmpeg_bin(), "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=12:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-movflags", "use_metadata_tags", "-metadata", "workflow={\"secret\": 1}", "-metadata", "title=someone's name", "-metadata", "comment=C:/Users/x/file", str(clip)], check=True)
    assert "workflow" in _tags(clip)
    do_import(clip, real)
    tags = _tags(clip)
    assert not ({"workflow", "title", "comment", "encoder"} & set(tags)), tags
    assert "workflow" in _tags(real / "_originals" / clip.name)  # git-ignored copy of the untouched original
    assert json.loads((real / "alley__dolly-in.recipe.json").read_text())["metadata_stripped"] is True


def test_badge_honours_override_and_quality():
    assert realmod.badge_text({"badge": "B", "quality": "partial: x"}) == "B \u00b7 partial: x"
    assert realmod.badge_text({}) == "Real LTX-2.3 output (Comfy Cloud)"


def test_committed_real_clips_are_honest():
    """The two real clips shipped in examples/real/: labelled prompt-only, crane flagged partial, the failed orbit is NOT featured."""
    d = ROOT / "examples" / "real"
    router_name = "alley__dolly-in__router-grok-imagine-1-5-lite.mp4"
    names = {p.name for p in d.glob("*.mp4")} - {router_name}
    assert names == {"alley__dolly-in.mp4", "alley__crane-up.mp4"}
    for n in names:
        rec = json.loads((d / n.replace(".mp4", ".recipe.json")).read_text())
        assert rec["simulated"] is False and rec["metadata_stripped"] is True
        assert "prompt-only" in rec["badge"] and "no camera LoRA" in rec["badge"] and "unedited" in rec["badge"]
        assert rec["prompt"] and rec["notes"]["camera_lora"] is False and rec["notes"]["edited"] is False
        assert "workflow" not in _tags(d / n)
        assert (ROOT / "workflows" / "real" / rec["workflow_file"]).is_file()
    crane = json.loads((d / "alley__crane-up.recipe.json").read_text())
    assert "partial: rises but also pushes forward" in crane["badge"]
    assert not list(d.glob("*orbit*"))
    # the recorded prompt is exactly the prompt inside the exported workflow
    for n in names:
        rec = json.loads((d / n.replace(".mp4", ".recipe.json")).read_text())
        wf = json.loads((ROOT / "workflows" / "real" / rec["workflow_file"]).read_text())
        sg = wf["definitions"]["subgraphs"][0]["id"]
        assert next(x for x in wf["nodes"] if x["type"] == sg)["widgets_values"][0] == rec["prompt"]


def test_real_workflows_have_no_secrets_or_partner_nodes():
    import re
    spec2 = importlib.util.spec_from_file_location("cow", ROOT / "scripts" / "check_open_weights.py")
    cow = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(cow)
    files = sorted((ROOT / "workflows" / "real").glob("*.json"))
    assert len(files) == 3
    for f in files:
        txt = f.read_text()
        json.loads(txt)
        assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+|sk-[A-Za-z0-9]{10,}|Bearer |api[_-]?key|token", txt, re.I), f.name
        assert cow.check_graph(json.loads(txt)) == []
        assert "prompt" not in json.loads(txt)["extra"]


def test_committed_router_clip_is_honest_and_never_replaces_the_ltx_clip():
    """One real Router clip (Grok Imagine 1.5 lite, prompt-only). It is a gallery-only variant: Demo never substitutes it."""
    d = ROOT / "examples" / "real"
    n = "alley__dolly-in__router-grok-imagine-1-5-lite.mp4"
    rec = json.loads((d / n.replace(".mp4", ".recipe.json")).read_text())
    assert rec["simulated"] is False and rec["engine"] == "router" and rec["metadata_stripped"] is True
    assert rec["model"].startswith("xai/grok-imagine-video-1.5-lite")
    assert "Router" in rec["badge"] and "not open weights" in rec["badge"] and "unedited" in rec["badge"]
    assert "LoRA" not in rec["badge"].replace("no camera LoRA", "")
    assert rec["notes"]["camera_lora"] is False and rec["notes"]["open_weights"] is False and rec["notes"]["edited"] is False
    assert rec["credits_used"] and rec["notes"]["router_request_id"]
    assert "workflow" not in _tags(d / n)
    clip = realmod.find("alley", "dolly-in", d)
    assert clip is not None and clip.variant is None and clip.path.name == "alley__dolly-in.mp4"
    assert any(c.variant == "router-grok-imagine-1-5-lite" for c in realmod.scan(d))
