"""The static (backend-free) Space build: structure, honesty, size budget, and the key-handling rules of the page."""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("build_static", ROOT / "scripts" / "build_static.py")
bs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bs)

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg needed to transcode the clips")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("space")
    stats = bs.build(out, limit=2)
    return out, stats


def test_structure_and_space_header(built):
    out, stats = built
    for f in ("index.html", "app.js", "style.css", "data.json", "README.md"):
        assert (out / f).is_file(), f
    head = (out / "README.md").read_text().split("---")[1]
    assert "sdk: static" in head and "license: mit" in head and "app_file: index.html" in head
    assert stats["total_mb"] < bs.BUDGET_MB


def test_every_referenced_file_exists(built):
    out, _ = built
    data = json.loads((out / "data.json").read_text())
    refs = [i["still"] for i in data["inputs"]] + [i["depth"] for i in data["inputs"]] + [c["file"] for c in data["clips"]] + [c["file"] for c in data["coverage"]]
    assert len(data["inputs"]) == 4 and len(data["coverage"]) == 6 and len(data["presets"]) == 17 and len(data["clips"]) == 2
    for r in refs:
        assert (out / r).is_file(), r
    html = (out / "index.html").read_text()
    for m in re.findall(r'(?:src|href)="([^"#]+)"', html):
        if not m.startswith(("http", "data:")):
            assert (out / m).is_file(), m


def test_clips_are_labelled_real_with_credits_and_never_simulated(built):
    out, _ = built
    for c in json.loads((out / "data.json").read_text())["clips"]:
        assert c["simulated"] is False and c["badge"].startswith("Real") and c["model_label"] and c["platform"]
        assert c["credits_used"] is not None and c["prompt"]
    html = (out / "index.html").read_text()
    assert "simulated previs" in html.lower() and "real model output" in html.lower() and "no backend" in html.lower()


def test_page_never_stores_or_leaks_the_key(built):
    out, _ = built
    js = (out / "app.js").read_text()
    assert not re.search(r"localStorage|sessionStorage|document\.cookie|indexedDB", js)
    hosts = set(re.findall(r"https?://[A-Za-z0-9.-]+", js))
    assert hosts <= {"https://api.comfy.org"}, hosts
    assert "credentials: \"omit\"" in js and "Idempotency-Key" in js
    assert 'type="password"' in (out / "index.html").read_text()
    # one submit, no retry loop around the POST
    assert js.count('method: "POST"') == 1
    for f in out.rglob("*"):
        if f.suffix in (".html", ".js", ".json", ".md", ".css"):
            t = f.read_text()
            assert not re.search(r"sk-[A-Za-z0-9]{16,}|hf_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}", t), f
            assert not re.search("|".join(["z" + "ak", "tay" + "lor", "grok" + " bot"]), t, re.I), f


def test_clips_are_small_silent_720p(built):
    import subprocess
    out, _ = built
    for f in (out / "media" / "clips").glob("*.mp4"):
        info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(f)], capture_output=True, text=True).stdout)["streams"]
        assert [s["codec_type"] for s in info] == ["video"]          # no audio track
        assert info[0]["width"] <= 1280 and info[0]["codec_name"] == "h264"
        assert f.stat().st_size < 3_000_000
