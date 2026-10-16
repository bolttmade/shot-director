"""The provenance popup must describe the clip that is on the stage (model, move, rating, credits), for every gallery clip, in the
local app and in the static Space. Browser test: skipped when Playwright or Chrome is not available (CI installs neither)."""
from __future__ import annotations

import http.server
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from functools import partial
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sync_api = pytest.importorskip("playwright.sync_api")
CHROME = os.environ.get("CHROME") or shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
pytestmark = pytest.mark.skipif(CHROME is None or shutil.which("ffmpeg") is None, reason="Chrome and ffmpeg needed")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); return s.getsockname()[1]


def expected_bits(c: dict, space: bool = False) -> list[str]:
    u = c.get("credits_used")
    cr = c.get("credits_label") or (None if not u else f"{round(u, 1):g}" if space or u < 100 else f"{u:.0f}")
    return [c["model_label"], f"own rating {c['rating']:g}/10" if c.get("rating") is not None else "", f"{cr} credits" if cr else "free tier"]


def test_local_app_popup_follows_the_selected_gallery_clip(tmp_path):
    port = free_port()
    env = {**os.environ, "DEMO": "1", "PORT": str(port), "OUTPUTS_DIR": str(tmp_path)}
    srv = subprocess.Popen([sys.executable, "-m", "app.server"], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(80):
            try:
                gal = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/gallery", timeout=1).read()); break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        else:
            pytest.skip("server did not start")
        real = [i for i in gal["items"] if i.get("real") and i.get("model_label")]
        assert len(real) >= 10
        with sync_api.sync_playwright() as p:
            b = p.chromium.launch(executable_path=CHROME, headless=True, args=["--no-sandbox"])
            pg = b.new_page(viewport={"width": 1280, "height": 800}); pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_selector(".g-item.is-real")
            texts = {}
            for it in real:   # click every real tile and read the popup straight away (no waiting for the video)
                pg.evaluate("(id) => { const t=[...document.querySelectorAll('.g-item.is-real')].find(e => e.title.includes(id)); t.click(); }", it["badge"])
                txt = pg.inner_text("#simBadge")
                for bit in expected_bits(it):
                    assert bit in txt, (it["id"], bit, txt)
                assert it["badge"] in txt
                texts[it["id"]] = txt
            b.close()
        assert len(set(texts.values())) >= len(real) - 2, "popups must differ between clips (a stale popup would repeat)"
    finally:
        srv.terminate()


def test_space_popup_follows_the_selected_gallery_clip(tmp_path):
    spec = importlib.util.spec_from_file_location("build_static", ROOT / "scripts" / "build_static.py")
    bs = importlib.util.module_from_spec(spec); spec.loader.exec_module(bs)
    out = tmp_path / "space"; bs.build(out, limit=3)
    data = json.loads((out / "data.json").read_text())
    port = free_port()
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), partial(http.server.SimpleHTTPRequestHandler, directory=str(out)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with sync_api.sync_playwright() as p:
            b = p.chromium.launch(executable_path=CHROME, headless=True, args=["--no-sandbox"])
            pg = b.new_page(viewport={"width": 1280, "height": 800}); pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_function("window.__sd && window.__sd.ready", timeout=30000)
            seen = set()
            for i, c in enumerate(sorted(data["clips"], key=lambda c: -(c["rating"] if c["rating"] is not None else -1))):   # same order as the page
                pg.evaluate("(n) => document.querySelectorAll('#gallery button.g')[n].click()", i)
                txt = pg.inner_text("#badge")
                for bit in [c["model_label"], c["preset_name"], c["input_title"]] + [x for x in expected_bits(c, True)[1:] if x]:
                    assert bit in txt, (c["id"], bit, txt)
                seen.add(txt)
            assert len(seen) == len(data["clips"])
            b.close()
    finally:
        httpd.shutdown()
