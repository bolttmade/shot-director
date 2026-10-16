#!/usr/bin/env python3
"""Capture README screenshots of the running UI in DEMO mode with a headless browser.

Dev-only tool, not part of the app's requirements:
    python3 -m venv /tmp/shots && /tmp/shots/bin/pip install playwright
    /tmp/shots/bin/python scripts/screenshots.py            # uses google-chrome / chromium on PATH

Starts its own server on :8765 with DEMO=1 and a throwaway outputs dir; sends nothing anywhere.
Shots are taken on the real alley frame (green "real" badge for the committed LTX-2.3 clips, amber for simulated ones), saved as WebP,
plus a short GIF of the flow (screen recording -> ffmpeg palette GIF). One headless Chrome at a time, closed after each part.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots"
PORT = 8765
URL = f"http://127.0.0.1:{PORT}"


def wait_up():
    for _ in range(60):
        try:
            urllib.request.urlopen(URL + "/api/config", timeout=1)
            return
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    raise SystemExit("server did not start")


def to_webp(png: Path, width: int = 1400, quality: int = 78) -> None:
    from PIL import Image
    im = Image.open(png).convert("RGB")
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(png.with_suffix(".webp"), "WEBP", quality=quality, method=6)
    png.unlink()


def shot_done(pg, timeout=120000):
    pg.wait_for_function("() => !document.querySelector('#go').disabled && document.querySelector('#go').textContent !== 'Working…'", timeout=timeout)


def pick(pg, name):
    pg.click(f".move:has-text('{name}')")


def stills(chrome: str) -> None:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=chrome, headless=True, args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required"])
        pg = b.new_page(viewport={"width": 1440, "height": 1300}, device_scale_factor=1)
        pg.goto(URL)
        pg.wait_for_selector(".move")
        pg.wait_for_timeout(2000)
        def shot(n):
            pg.evaluate("window.scrollTo(0,0); document.querySelectorAll('#timeline video').forEach(v => { v.currentTime = 0.6; })")
            pg.wait_for_timeout(500)
            pg.screenshot(path=OUT / f"{n}.png")

        # 01: free previs first, then the one real render of the same still and move (MiniMax H3 via the Router, green badge)
        pg.click(".sample[data-id='sample:forest-cabin']"); pg.wait_for_timeout(600)
        pick(pg, "FPV Drone"); pg.click("#go"); shot_done(pg); pg.wait_for_timeout(1000)
        pg.click("#renderNext button:has-text('Play the real render')"); pg.wait_for_timeout(2200)
        shot("01-real-render")
        pg.click(".sample[data-id='sample:alley']"); pg.wait_for_timeout(600)
        pick(pg, "Dolly In"); pg.click("#go"); shot_done(pg); pg.wait_for_timeout(1800)
        pg.click("#addTl")
        pg.click("#abSeg button[data-view=split]"); pg.fill("#wipe", "45"); pg.wait_for_timeout(500)
        shot("02-ab-player")
        pg.click("#abSeg button[data-view=video]")

        pick(pg, "Crane Up"); pg.click("#go"); shot_done(pg); pg.wait_for_timeout(1200)
        pg.click("#addTl")
        pick(pg, "Orbit Left"); pg.click("#go"); pg.wait_for_timeout(500); shot_done(pg); pg.wait_for_timeout(1500)
        shot("03-simulated-orbit")                      # no real orbit exists: amber, labelled simulated
        pg.click("#addTl")

        pg.click("#getCov")
        pg.wait_for_function("() => document.querySelectorAll('#cov .tile.has').length === 6", timeout=120000)
        pg.wait_for_timeout(800)
        shot("04-coverage-board")

        pg.click("#exportSeq"); pg.wait_for_selector("#seqOut:not(.hidden)", timeout=60000); pg.wait_for_timeout(1500)
        pg.evaluate("window.scrollTo(0,0)")
        shot("05-timeline-export")

        pg.click("button.tab[data-tab=angle]")
        pg.focus("#dial"); pg.keyboard.press("ArrowRight"); pg.keyboard.press("ArrowRight")
        pg.fill("#elev", "30")
        pg.click("#previewAngle")
        pg.wait_for_function("() => !document.querySelector('#previewAngle').disabled", timeout=60000)
        pg.wait_for_timeout(800)
        shot("06-reshoot-angle")
        pg.click("button.tab[data-tab=moves]")

        bad = Path(tempfile.mkdtemp()) / "notes.png"
        bad.write_text("this is not an image")
        pg.set_input_files("#file", str(bad)); pg.wait_for_selector("#errorBox:not(.hidden)"); pg.wait_for_timeout(300)
        pg.evaluate("window.scrollTo(0,0)")
        pg.screenshot(path=OUT / "08-error.png")
        pg.close()

        m = b.new_page(viewport={"width": 420, "height": 900}, device_scale_factor=2)
        m.goto(URL); m.wait_for_selector(".move"); m.wait_for_timeout(1500)
        m.screenshot(path=OUT / "07-mobile.png", full_page=True)
        b.close()
    for png in sorted(OUT.glob("*.png")):
        to_webp(png)


def gif(chrome: str) -> None:
    """A ~20 s real flow (real dolly, A/B, crane, timeline, export) as a small GIF.
    Frames are plain page screenshots taken in a loop (no Playwright video, so no extra browser download), then an ffmpeg palette GIF."""
    from playwright.sync_api import sync_playwright
    fdir = Path(tempfile.mkdtemp(prefix="sd-frames-"))
    n = [0]
    t0 = time.time()

    def snap(pg):
        pg.screenshot(path=fdir / f"f{n[0]:05d}.jpg", type="jpeg", quality=70)
        n[0] += 1

    def hold(pg, ms):
        t = time.time()
        while (time.time() - t) * 1000 < ms:
            snap(pg)

    def until_done(pg, timeout=120):
        t = time.time()
        while time.time() - t < timeout:
            if pg.evaluate("() => !document.querySelector('#go').disabled && document.querySelector('#go').textContent !== 'Working…'"):
                return
            snap(pg)

    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=chrome, headless=True, args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required"])
        pg = b.new_page(viewport={"width": 1280, "height": 760}, device_scale_factor=1)
        pg.goto(URL); pg.wait_for_selector(".move"); hold(pg, 1000)
        pick(pg, "Dolly In"); hold(pg, 500); pg.click("#go"); until_done(pg); hold(pg, 2800)
        pg.click("#addTl"); pg.click("#abSeg button[data-view=split]"); pg.fill("#wipe", "30"); hold(pg, 700); pg.fill("#wipe", "70"); hold(pg, 900)
        pg.click("#abSeg button[data-view=video]")
        pick(pg, "Crane Up"); hold(pg, 500); pg.click("#go"); until_done(pg); hold(pg, 2800)
        pg.click("#addTl"); hold(pg, 600); pg.click("#exportSeq")
        t = time.time()
        while time.time() - t < 60 and pg.evaluate("() => document.querySelector('#seqOut').classList.contains('hidden')"):
            snap(pg)
        hold(pg, 2500)
        b.close()
    ff = shutil.which("ffmpeg") or "ffmpeg"
    rate = n[0] / max(time.time() - t0, 1)  # frames were taken back to back: input rate = frames per real second, so playback is real time
    vf = "fps=6,scale=640:-1:flags=lanczos"
    pal = fdir / "pal.png"
    src = ["-framerate", f"{rate:.2f}", "-i", str(fdir / "f%05d.jpg")]
    subprocess.run([ff, "-y", "-loglevel", "error", *src, "-vf", f"{vf},palettegen=max_colors=64:stats_mode=diff", str(pal)], check=True)
    subprocess.run([ff, "-y", "-loglevel", "error", *src, "-i", str(pal), "-lavfi", f"{vf}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle", "-map_metadata", "-1", str(OUT / "demo-flow.gif")], check=True)
    shutil.rmtree(fdir, ignore_errors=True)
    print("gif", n[0], "frames,", round((OUT / "demo-flow.gif").stat().st_size / 1e6, 2), "MB")


def main() -> None:
    try:
        import playwright  # noqa: F401
    except ImportError:
        raise SystemExit("pip install playwright (in a throwaway venv) first; see the docstring")
    chrome = os.environ.get("CHROME") or shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    if not chrome:
        raise SystemExit("Need google-chrome or chromium on PATH (or set CHROME=/path)")
    OUT.mkdir(parents=True, exist_ok=True)
    if os.environ.get("ONLY") != "gif":
        for old in list(OUT.glob("*.webp")) + list(OUT.glob("*.png")) + list(OUT.glob("*.gif")):
            old.unlink()
    env = {**os.environ, "DEMO": "1", "PORT": str(PORT), "OUTPUTS_DIR": tempfile.mkdtemp(prefix="sd-shots-")}
    py = ROOT / ".venv" / "bin" / "python"
    srv = subprocess.Popen([str(py if py.exists() else sys.executable), "-m", "app.server"], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_up()
        if os.environ.get("ONLY") != "gif":
            stills(chrome)
        gif(chrome)
    finally:
        srv.terminate()
        shutil.rmtree(env["OUTPUTS_DIR"], ignore_errors=True)
    print("wrote", *sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
