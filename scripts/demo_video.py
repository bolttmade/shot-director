#!/usr/bin/env python3
"""Build the demo video draft (free, local, no credits): real UI screen captures + real clips + cards + captions + offline TTS.

Run through scripts/make_demo_video.sh (it prepares the venvs). Stages (each re-runnable):
    cards     PNG cards (concept, platform/build, credit log, end card) drawn with Pillow from repo facts
    tts       one WAV per narration beat with piper (offline); falls back to no audio if piper/voice is missing
    capture   headless Chrome + CDP screencast of the local app (DEMO=1) and of the live static Space -> frame sequences -> mp4
    assemble  per-beat mp4s (timed by the narration), burned-in ASS captions, AAC audio, final mp4 + captions-only variant

Nothing here calls the Comfy API or spends credits. Narration text lives in BEATS below (it is the voice-over of docs/DEMO_VIDEO_PLAN.md).
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(os.environ.get("DEMO_OUT", ROOT / "demo"))
W, H, FPS = 1280, 720, 25
UI_H = 640                      # screen captures are 1280x640; the bottom 80 px bar carries the captions
APP_PORT = 8766
SPACE_URL = "https://bolttmade-shot-director.static.hf.space/"
REPO = "github.com/bolttmade/shot-director"
SPACE = "huggingface.co/spaces/BoltTmade/shot-director"
CHROME = os.environ.get("CHROME") or shutil.which("google-chrome") or shutil.which("chromium") or "google-chrome"
VOICE = Path(os.environ.get("PIPER_VOICE", OUT / "voices" / "en_US-lessac-medium.onnx"))
PIPER_PY = os.environ.get("PIPER_PY", "python3")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_M = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

# kind: clip (real clip full frame) | card | ui:<capture name>.  `label` is burned in as a green/amber tag where the footage has no UI badge.
BEATS = [
    {"id": "hero", "kind": "clip", "src": "examples/real/forest-cabin__fpv-drone__router-minimax-h3.mp4", "label": ("real", "REAL · MiniMax H3 via Comfy Router · one still in, 135.78 credits · unedited"),
     "text": "One still. One real render. This is Shot Director."},
    {"id": "concept", "kind": "card", "card": "concept",
     "text": "Shot Director is a camera-move studio for Comfy. Preview any move for free with a simulated camera, then spend credits once, on the real render of the move you picked."},
    {"id": "previs", "kind": "ui", "cap": "previs",
     "text": "Pick a still and a move. The free preview is simulated, and the amber badge says so. Happy with it? Play the real render: green badge, MiniMax H3 through the Comfy Router, a partner model, unedited. A hundred and thirty-six credits."},
    {"id": "gallery", "kind": "ui", "cap": "gallery",
     "text": "The gallery holds fourteen real clips, with their credits and my honest ratings. Grok lite costs forty-eight credits and is close behind; its orbit is a gentle arc, six out of ten. FLUX 3 Video cost two hundred and twenty-six, and barely moves: four out of ten."},
    {"id": "coverage", "kind": "ui", "cap": "coverage",
     "text": "Coverage: six real FLUX 3 Image angles of one frame. The A/B player compares the still with the clip."},
    {"id": "reel", "kind": "ui", "cap": "reel",
     "text": "Make my reel cuts the real clips into sixteen by nine and nine by sixteen, labelled with the model. No credits spent."},
    {"id": "space", "kind": "ui", "cap": "space",
     "text": "It also runs free in your browser, as a static Hugging Face Space."},
    {"id": "platform", "kind": "card", "card": "platform",
     "text": "Under the hood: the Comfy Router API and SDK, one capped, confirmed submit per request, a hundred tests, and green CI."},
    {"id": "credits", "kind": "card", "card": "credits",
     "text": "Every credit is logged with its request id: about thirteen hundred in total. The open-weights and Cloud engines are contract-tested only, and no camera LoRA result exists."},
    {"id": "end", "kind": "card", "card": "end", "text": "Shot Director. Open source, on GitHub and Hugging Face.", "tail": 2.5},
]
PAD_AFTER = 0.45       # silence after each beat's narration
MAX_SECONDS = 105.0


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, **kw)


def ffprobe_dur(p: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.strip()
    return float(out or 0)


# ----------------------------------------------------------------------------------------------------- cards
def _font(path: str, size: int):
    from PIL import ImageFont
    return ImageFont.truetype(path, size)


def _test_count() -> str:
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT, capture_output=True, text=True, timeout=120)
        m = re.search(r"(\d+) tests? collected", r.stdout) or re.search(r"^(\d+) tests", r.stdout, re.M)
        return m.group(1) if m else "100+"
    except Exception:  # noqa: BLE001
        return "100+"


def make_cards(work: Path) -> None:
    from PIL import Image, ImageDraw
    work.mkdir(parents=True, exist_ok=True)
    BG, PANEL, LINE, TXT, MUT, AMB, GRN, CY = (7, 8, 11), (15, 17, 23), (46, 52, 71), (233, 235, 242), (138, 146, 168), (255, 179, 64), (52, 211, 153), (90, 209, 230)

    def canvas():
        im = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(im)
        for i in range(H):  # soft vertical glow
            a = max(0, 1 - i / 380) * 0.10
            d.line([(0, i), (W, i)], fill=(int(7 + 40 * a * 3), int(8 + 20 * a * 3), int(11 + 40 * a * 3)))
        return im, d

    def head(d, title, sub=None):
        d.text((56, 38), "SHOT DIRECTOR", font=_font(FONT_B, 22), fill=AMB)
        d.text((56, 74), title, font=_font(FONT_B, 44), fill=TXT)
        if sub:
            d.text((56, 130), sub, font=_font(FONT, 22), fill=MUT)

    def box(d, xy, color, title, lines, tsize=26):
        x0, y0, x1, y1 = xy
        d.rounded_rectangle(xy, 16, fill=PANEL, outline=color, width=3)
        d.text((x0 + 22, y0 + 18), title, font=_font(FONT_B, tsize), fill=color)
        y = y0 + 18 + tsize + 14
        for ln in lines:
            d.text((x0 + 22, y), ln, font=_font(FONT, 20), fill=TXT)
            y += 28

    # concept
    im, d = canvas(); head(d, "Free previs, then one real render.", "Preview a camera move for free. Pay for the real one once.")
    box(d, (56, 200, 396, 470), CY, "1  A still frame", ["AI-generated original,", "no people, no logos.", "4 stills in the repo."])
    box(d, (470, 200, 810, 470), AMB, "2  Free previs", ["SIMULATED depth-parallax", "camera: CPU or browser,", "$0, amber badge.", "A preview of the move,", "not model output."])
    box(d, (884, 200, 1224, 470), GRN, "3  One real render", ["Comfy Router partner model", "(MiniMax H3, Grok lite,", "FLUX 3): credits logged,", "green badge, unedited,", "not open weights."])
    for x in (410, 824):
        d.polygon([(x, 320), (x + 46, 335), (x, 350)], fill=MUT)
    d.text((56, 505), "Green = real model output.   Amber = simulated.   Nothing is relabelled.", font=_font(FONT_B, 24), fill=TXT)
    im.save(work / "card_concept.png")

    # platform / build
    n = _test_count()
    im, d = canvas(); head(d, "Built on the Comfy platform")
    rows = [(CY, "Comfy Router API", "minimax/minimax-h3 · xai/grok-imagine-video-1.5-lite · bfl/flux-3-image · bfl/flux-3-video"),
            (CY, "Comfy SDK 0.5.0", "client.models.submit → handle.iter_events() → handle.get(): one submit, never retried"),
            (AMB, "Comfy Cloud", "LTX-2.3 image-to-video template on the free tier (2 prompt-only clips)"),
            (GRN, "Cost guard", "price first (static table: /estimate not enabled), cap, explicit confirm, 402 stops"),
            (GRN, "Quality", f"{n} tests · CI green on Python 3.10, 3.11, 3.12 · secret and real-name scans")]
    y = 150
    for col, t, s in rows:
        d.rounded_rectangle((56, y, 1224, y + 84), 14, fill=PANEL, outline=LINE, width=2)
        d.rectangle((56, y + 10, 62, y + 74), fill=col)
        d.text((84, y + 10), t, font=_font(FONT_B, 25), fill=col)
        d.text((84, y + 46), s, font=_font(FONT, 18), fill=TXT)
        y += 98
    im.save(work / "card_platform.png")

    # credit log
    im, d = canvas(); head(d, "The credit log", "Router spend, 2026-10-16 · 211 credits per US dollar · measured by balance delta")
    rows = [("5 × MiniMax H3 clips (5 s, 768P)", "135.78 each", "679"), ("6 × Grok Imagine 1.5 lite clips (5 s)", "33 to 48 each", "275"),
            ("1 × FLUX 3 Video clip (5 s, hd)", "226.3", "226"), ("3 stills + 6 coverage edits (FLUX 3 Image)", "14.48 each", "130")]
    y = 178
    for a, b, c in rows:
        d.rounded_rectangle((56, y, 1224, y + 62), 12, fill=PANEL, outline=LINE, width=2)
        d.text((78, y + 16), a, font=_font(FONT, 24), fill=TXT)
        d.text((800, y + 18), b, font=_font(FONT, 20), fill=MUT)
        d.text((1124, y + 14), c, font=_font(FONT_B, 28), fill=GRN)
        y += 72
    d.rounded_rectangle((56, y + 8, 1224, y + 84), 12, fill=PANEL, outline=AMB, width=3)
    d.text((78, y + 28), "About 1,310 credits (about $6.2) · every request id in docs/COSTS.md", font=_font(FONT_B, 24), fill=AMB)
    d.text((56, y + 104), "Estimate vs measured is logged for every run: H3 exact, Grok +7%, FLUX 3 Video −12%.", font=_font(FONT, 19), fill=MUT)
    d.text((56, y + 134), "No card charge. No retries. No 402.", font=_font(FONT, 19), fill=MUT)
    im.save(work / "card_credits.png")

    # end
    im, d = canvas()
    d.text((56, 90), "SHOT DIRECTOR", font=_font(FONT_B, 28), fill=AMB)
    d.text((56, 140), "Free previs, then one real render.", font=_font(FONT_B, 50), fill=TXT)
    d.rounded_rectangle((56, 250, 1224, 340), 16, fill=PANEL, outline=CY, width=3)
    d.text((86, 272), "GitHub", font=_font(FONT, 20), fill=MUT)
    d.text((86, 298), REPO, font=_font(FONT_B, 34), fill=CY)
    d.rounded_rectangle((56, 370, 1224, 460), 16, fill=PANEL, outline=GRN, width=3)
    d.text((86, 392), "Live static demo (free Hugging Face Space)", font=_font(FONT, 20), fill=MUT)
    d.text((86, 418), SPACE, font=_font(FONT_B, 34), fill=GRN)
    d.text((56, 500), "MIT · open source · built by bolt · #OpenSourceHiggsfield", font=_font(FONT, 22), fill=MUT)
    im.save(work / "card_end.png")
    print("cards ok")


# ----------------------------------------------------------------------------------------------------- tts
def make_tts(work: Path) -> None:
    (work / "tts").mkdir(parents=True, exist_ok=True)
    if not VOICE.exists():
        print("no piper voice at", VOICE, "-> captions only"); return
    for b in BEATS:
        wav = work / "tts" / f"{b['id']}.wav"
        r = subprocess.run([PIPER_PY, "-m", "piper", "-m", str(VOICE), "-f", str(wav), "--length-scale", os.environ.get("TTS_SPEED", "0.95"), "--sentence-silence", "0.25"], input=b["text"], text=True, capture_output=True)
        if r.returncode != 0 or not wav.exists():
            print("piper failed for", b["id"], r.stderr[-300:]); wav.unlink(missing_ok=True); continue
        print(f"tts {b['id']}: {ffprobe_dur(wav):.1f}s")


# ----------------------------------------------------------------------------------------------------- capture
class Recorder:
    """CDP screencast -> jpeg frames with timestamps. pause()/resume() drop frames (to cut dead waiting time out)."""

    def __init__(self, page, ctx, outdir: Path):
        self.dir, self.n, self.frames, self.paused = outdir, 0, [], False
        shutil.rmtree(outdir, ignore_errors=True); outdir.mkdir(parents=True)
        self.cdp = ctx.new_cdp_session(page)
        self.cdp.on("Page.screencastFrame", self._on)
        self.cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 88, "maxWidth": W, "maxHeight": UI_H, "everyNthFrame": 1})
        self.t_shift, self.last_ts, self.resume_pending = 0.0, None, False

    def _on(self, e):
        self.cdp.send("Page.screencastFrameAck", {"sessionId": e["sessionId"]})
        ts = e["metadata"]["timestamp"]
        if self.paused:
            return
        if self.resume_pending and self.last_ts is not None:
            self.t_shift += ts - self.last_ts - 0.04   # close the gap that was paused away
        self.resume_pending = False
        self.last_ts = ts
        p = self.dir / f"f{self.n:06d}.jpg"; p.write_bytes(base64.b64decode(e["data"]))
        self.frames.append((ts - self.t_shift, p.name)); self.n += 1

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False; self.resume_pending = True

    def stop(self, tail: float = 0.6) -> Path:
        self.cdp.send("Page.stopScreencast")
        lst = self.dir / "list.txt"
        with lst.open("w") as f:
            for (t0, name), nxt in zip(self.frames, self.frames[1:] + [(self.frames[-1][0] + tail, "")]):
                f.write(f"file '{name}'\nduration {max(nxt[0] - t0, 0.001):.4f}\n")
            f.write(f"file '{self.frames[-1][1]}'\n")
        mp4 = self.dir.with_suffix(".mp4")
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", f"fps={FPS},scale={W}:{UI_H}:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-crf", "16", "-preset", "fast", str(mp4)])
        return mp4


class PollRecorder:
    """For WebGL pages (the screencast shows the canvas black under software GL): repeated page.screenshot() frames instead."""

    def __init__(self, page, outdir: Path):
        self.page, self.dir, self.frames = page, outdir, []
        shutil.rmtree(outdir, ignore_errors=True); outdir.mkdir(parents=True)
        self.t0 = time.time()

    def wait(self, ms: int):
        end = time.time() + ms / 1000
        while time.time() < end:
            t = time.time() - self.t0
            name = f"f{len(self.frames):06d}.jpg"
            self.page.screenshot(path=str(self.dir / name), type="jpeg", quality=88)
            self.frames.append((t, name))

    def stop(self, tail: float = 0.6) -> Path:
        lst = self.dir / "list.txt"
        with lst.open("w") as f:
            for (t0, name), nxt in zip(self.frames, self.frames[1:] + [(self.frames[-1][0] + tail, "")]):
                f.write(f"file '{name}'\nduration {max(nxt[0] - t0, 0.001):.4f}\n")
            f.write(f"file '{self.frames[-1][1]}'\n")
        mp4 = self.dir.with_suffix(".mp4")
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", f"fps={FPS},scale={W}:{UI_H}:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-crf", "16", "-preset", "fast", str(mp4)])
        return mp4


def wait_up(url: str):
    for _ in range(80):
        try:
            urllib.request.urlopen(url, timeout=1); return
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    raise SystemExit("server did not start: " + url)


def capture(work: Path, only: set[str] | None = None) -> None:
    from playwright.sync_api import sync_playwright
    outputs = Path(tempfile.mkdtemp(prefix="sd-demo-out-"))
    env = {**os.environ, "DEMO": "1", "PORT": str(APP_PORT), "OUTPUTS_DIR": str(outputs)}
    py = ROOT / ".venv" / "bin" / "python"
    srv = subprocess.Popen([str(py if py.exists() else sys.executable), "-m", "app.server"], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_up(f"http://127.0.0.1:{APP_PORT}/api/config")
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=CHROME, headless=True, args=["--no-sandbox", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--autoplay-policy=no-user-gesture-required", "--hide-scrollbars"])

            def page_for(url: str):
                ctx = b.new_context(viewport={"width": W, "height": UI_H}, device_scale_factor=1)
                pg = ctx.new_page(); pg.goto(url); pg.wait_for_timeout(1200)
                return ctx, pg

            def want(n):
                return only is None or n in only

            base = f"http://127.0.0.1:{APP_PORT}/"
            # ---- previs -> real render (forest cabin, FPV drone)
            if want("previs"):
                ctx, pg = page_for(base); pg.wait_for_selector(".move")
                pg.click(".sample[data-id='sample:forest-cabin']"); pg.wait_for_timeout(500)
                pg.click(".move:has-text('FPV Drone')"); pg.wait_for_timeout(500)
                rec = Recorder(pg, ctx, work / "cap_previs"); pg.wait_for_timeout(1200)
                pg.click("#go"); rec.pause(); pg.wait_for_timeout(600); pg.wait_for_function("() => !document.querySelector('#go').disabled && document.querySelector('#go').textContent !== 'Working…'", timeout=120000); rec.resume()
                top = "window.scrollTo(0, Math.max(0, document.querySelector('#stageTitle').getBoundingClientRect().top + window.scrollY - 70))"
                pg.evaluate(top); pg.wait_for_timeout(3200)   # simulated clip plays, amber badge + callout visible
                pg.click("#renderNext button:has-text('Play the real render')"); pg.evaluate(top); pg.wait_for_timeout(6500)
                rec.stop(); ctx.close()
            # ---- gallery: real clips with credits
            if want("gallery"):
                ctx, pg = page_for(base); pg.wait_for_selector(".g-item")
                pg.evaluate("document.querySelector('#gallery').scrollIntoView({block:'start'})"); pg.wait_for_timeout(300)
                rec = Recorder(pg, ctx, work / "cap_gallery"); pg.wait_for_timeout(1500)
                for label, hold in (("FPV Drone · Forest Cabin", 3000), ("Orbit Left · Rainy Alley", 3600), ("Arc Shot · Retro Diner", 3600)):
                    pg.evaluate("(l) => { const el=[...document.querySelectorAll('.g-item')].find(e => e.textContent.includes(l.split(' · ')[0]) && e.textContent.includes(l.split(' · ')[1]) && e.classList.contains('is-real')); if (el) el.click(); }", label)
                    pg.evaluate("window.scrollTo({top:0})"); pg.wait_for_timeout(hold)
                    pg.evaluate("document.querySelector('#gallery').scrollIntoView({block:'start'})"); pg.wait_for_timeout(700)
                rec.stop(); ctx.close()
            # ---- coverage + A/B
            if want("coverage"):
                ctx, pg = page_for(base); pg.wait_for_selector(".move")
                pg.click(".move:has-text('Dolly In')"); pg.click("#go"); pg.wait_for_timeout(600); pg.wait_for_function("() => !document.querySelector('#go').disabled && document.querySelector('#go').textContent !== 'Working…'", timeout=120000)
                pg.wait_for_timeout(1200)
                rec = Recorder(pg, ctx, work / "cap_coverage"); pg.wait_for_timeout(600)
                pg.click("#getCov"); rec.pause(); pg.wait_for_function("() => document.querySelectorAll('#cov .tile.has').length === 6", timeout=120000); rec.resume()
                pg.wait_for_timeout(2600)
                pg.click("#abSeg button[data-view=split]"); pg.fill("#wipe", "30"); pg.wait_for_timeout(900); pg.fill("#wipe", "70"); pg.wait_for_timeout(1500)
                rec.stop(); ctx.close()
            # ---- make my reel
            if want("reel"):
                ctx, pg = page_for(base); pg.wait_for_selector(".move")
                rec = Recorder(pg, ctx, work / "cap_reel"); pg.wait_for_timeout(700)
                pg.click("#addReal"); pg.wait_for_timeout(1500)
                pg.evaluate("document.querySelector('#makeReel').scrollIntoView({block:'center'})"); pg.wait_for_timeout(700)
                pg.click("#makeReel"); rec.pause(); pg.wait_for_selector("#reelOut:not(.hidden)", timeout=240000); rec.resume()
                pg.evaluate("document.querySelector('#reelOut').scrollIntoView({block:'center'})"); pg.wait_for_timeout(500)
                pg.evaluate("document.querySelectorAll('#reelOut video').forEach(v => { v.muted = true; v.play().catch(()=>{}); })"); pg.wait_for_timeout(4500)
                rec.stop(); ctx.close()
            # ---- the live static Space
            if want("space"):
                ctx, pg = page_for(SPACE_URL); pg.wait_for_function("window.__sd && window.__sd.ready", timeout=60000); pg.wait_for_timeout(800)
                top = "window.scrollTo(0, document.querySelector('#stageTitle').getBoundingClientRect().top + window.scrollY - 16)"
                pg.evaluate(top)
                rec = PollRecorder(pg, work / "cap_space"); rec.wait(150)
                pg.click("#previs"); pg.evaluate(top); rec.wait(4600)       # the in-browser WebGL previs (amber)
                pg.click("#real"); pg.evaluate(top); rec.wait(3200)         # the real clip, green badge
                rec.stop(); ctx.close()
            b.close()
    finally:
        srv.terminate(); shutil.rmtree(outputs, ignore_errors=True)
    print("capture ok")


# ----------------------------------------------------------------------------------------------------- assemble
def ass_time(t: float) -> str:
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def chunks(text: str, limit: int = 96) -> list[str]:
    sents = re.split(r"(?<=[.!?])\s+", text.strip())
    out: list[str] = []
    for s in sents:
        while len(s) > limit:
            cut = max(s.rfind(", ", 0, limit), s.rfind(": ", 0, limit))
            if cut < 30:
                cut = s.rfind(" ", 0, limit)
            out.append(s[:cut + 1].strip()); s = s[cut + 1:].strip()
        if s:
            out.append(s)
    return out


def assemble(work: Path, final: Path) -> dict:
    segs, timeline, t = [], [], 0.0
    have_audio = all((work / "tts" / f"{b['id']}.wav").exists() for b in BEATS)
    ass_events = []
    for b in BEATS:
        wav = work / "tts" / f"{b['id']}.wav"
        nar = ffprobe_dur(wav) if wav.exists() else max(2.0, len(b["text"].split()) / 2.6)
        # visual source
        if b["kind"] == "clip":
            src = ROOT / b["src"]; vis = ffprobe_dur(src)
        elif b["kind"] == "card":
            src = work / f"card_{b['card']}.png"; vis = 0.0
        else:
            src = work / f"cap_{b['cap']}.mp4"; vis = ffprobe_dur(src)
        dur = max(nar + PAD_AFTER, vis if b["kind"] == "clip" else 0.0) + b.get("tail", 0.0)
        if b["kind"] == "ui":
            dur = max(dur, min(vis, nar + PAD_AFTER + 3.0))     # let a capture run a little past the narration, but never freeze for long
        seg = work / f"seg_{b['id']}.mp4"
        if b["kind"] == "clip":
            vf = f"crop='min(iw,1280)':'min(ih,720)',scale={W}:{H}:flags=lanczos,tpad=stop_mode=clone:stop_duration={dur:.2f},fps={FPS},format=yuv420p"
            run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-an", "-vf", vf, "-t", f"{dur:.3f}", "-c:v", "libx264", "-crf", "17", "-preset", "fast", str(seg)])
        elif b["kind"] == "card":
            run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(FPS), "-i", str(src), "-t", f"{dur:.3f}", "-vf", f"fps={FPS},format=yuv420p", "-c:v", "libx264", "-crf", "17", "-preset", "fast", str(seg)])
        else:
            vf = f"tpad=stop_mode=clone:stop_duration={max(dur - vis, 0) + 0.1:.2f},pad={W}:{H}:0:0:black,fps={FPS},format=yuv420p"
            run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-an", "-vf", vf, "-t", f"{dur:.3f}", "-c:v", "libx264", "-crf", "17", "-preset", "fast", str(seg)])
        segs.append(seg)
        # captions: split the narration over the narration time, weighted by characters
        cs = chunks(b["text"]); tot = sum(len(c) for c in cs); tt = t + 0.1
        for c in cs:
            share = nar * len(c) / tot
            ass_events.append(f"Dialogue: 0,{ass_time(tt)},{ass_time(tt + share)},Cap,,0,0,0,,{c.replace(chr(10), ' ')}")
            tt += share
        if b.get("label"):
            kind, txt = b["label"]
            ass_events.append(f"Dialogue: 1,{ass_time(t + 0.15)},{ass_time(t + dur - 0.1)},{'Real' if kind == 'real' else 'Sim'},,0,0,0,,{txt}")
        timeline.append((b["id"], round(t, 2), round(dur, 2)))
        t += dur
    total = t
    if total > MAX_SECONDS:
        raise SystemExit(f"video would be {total:.1f}s, over the {MAX_SECONDS}s limit: shorten BEATS or raise TTS_SPEED")
    ass = work / "captions.ass"
    ass.write_text(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,DejaVu Sans,29,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,2,40,40,16,1
Style: Real,DejaVu Sans,24,&H00231A04,&H000000FF,&H0099D334,&H0099D334,1,0,0,0,100,100,0,0,3,6,0,7,24,24,22,1
Style: Sim,DejaVu Sans,24,&H0006131B,&H000000FF,&H0040B3FF,&H0040B3FF,1,0,0,0,100,100,0,0,3,6,0,7,24,24,22,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ass_events) + "\n")
    lst = work / "segs.txt"; lst.write_text("".join(f"file '{s.name}'\n" for s in segs))
    video = work / "video_nosubs.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(video)])
    # audio: each beat's wav padded to its segment length, concatenated
    audio = work / "narration.wav"
    if have_audio:
        parts = []
        for b, (_, _, dur) in zip(BEATS, timeline):
            pw = work / f"pad_{b['id']}.wav"
            run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(work / "tts" / f"{b['id']}.wav"), "-af", f"adelay=100|100,apad=whole_dur={dur:.3f},aresample=44100", "-ac", "1", "-t", f"{dur:.3f}", str(pw)])
            parts.append(pw)
        (work / "wavs.txt").write_text("".join(f"file '{p.name}'\n" for p in parts))
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(work / "wavs.txt"), "-c", "copy", str(audio)])
    else:
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono", "-t", f"{total:.2f}", str(audio)])
    final.parent.mkdir(parents=True, exist_ok=True)
    sub = f"ass={ass.name}:fontsdir=/usr/share/fonts/truetype/dejavu"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", video.name, "-i", audio.name, "-vf", sub, "-c:v", "libx264", "-crf", "21", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-movflags", "+faststart", "-map_metadata", "-1", "-shortest", str(final.resolve())], cwd=work)
    if have_audio:   # captions-only variant: same picture, silent AAC track
        silent = final.with_name(final.stem + "-captions-only.mp4")
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(final), "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "32k", "-shortest", "-movflags", "+faststart", str(silent)])
    info = {"seconds": round(total, 2), "beats": timeline, "tts": have_audio}
    (work / "timeline.json").write_text(json.dumps(info, indent=1))
    return info


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("stage", choices=["cards", "tts", "capture", "assemble", "all"])
    ap.add_argument("--only", help="capture only these comma-separated captures (previs,gallery,coverage,reel,space)")
    a = ap.parse_args()
    work = OUT / "work"; work.mkdir(parents=True, exist_ok=True)
    if a.stage in ("cards", "all"):
        make_cards(work)
    if a.stage in ("tts", "all"):
        make_tts(work)
    if a.stage in ("capture", "all"):
        capture(work, set(a.only.split(",")) if a.only else None)
    if a.stage in ("assemble", "all"):
        info = assemble(work, OUT / "shot-director-demo.mp4")
        print(json.dumps(info))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
