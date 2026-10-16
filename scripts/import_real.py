#!/usr/bin/env python3
"""Import REAL model clips (e.g. from the Comfy Cloud web UI) into examples/real/.

    python scripts/import_real.py                       # process every <input>__<preset>.mp4 already in examples/real/
    python scripts/import_real.py ~/Downloads/alley__dolly-in.mp4 ...   # copy files in, then process
    python scripts/import_real.py --check               # validate only; change nothing

For each clip it:
  1. validates the file name  <input-id>__<preset-id>.mp4  against examples/inputs/ and presets/
  2. probes it with ffprobe (needs a video stream, sane duration)
  3. strips ALL container metadata (ffmpeg -map_metadata -1; Comfy Cloud embeds the full workflow JSON in the mp4), and transcodes to H.264 (<= 1280 px wide, <= --max-mb MB) only if it is bigger/odd; the original goes to
     examples/real/_originals/ (git-ignored)
  4. writes <name>.recipe.json with provenance "real LTX-2.3 output via Comfy Cloud web UI" plus the notes
     found in the optional sibling <name>.json (model, template, seed, resolution, duration, date, prompt)
The app then lists the clip in the gallery with a green "Real ... output" badge and the Demo engine replays
it instead of a simulated clip for the same input + move. See docs/REAL_RUN.md.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import real as realmod  # noqa: E402
from app.media import ffmpeg_bin, ffprobe_bin  # noqa: E402
from app.recipes import make_recipe, sha256_file  # noqa: E402

CRF_LADDER = (22, 26, 30, 34)


class ImportError_(Exception):
    pass


def probe(path: Path) -> dict[str, Any]:
    fp = ffprobe_bin()
    if not fp:
        raise ImportError_("ffprobe not found (it ships with ffmpeg). Install ffmpeg first.")
    r = subprocess.run([fp, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise ImportError_(f"ffprobe could not read {path.name}: {r.stderr.strip()[-200:] or 'not a valid media file'}")
    d = json.loads(r.stdout)
    vs = [s for s in d.get("streams", []) if s.get("codec_type") == "video"]
    if not vs:
        raise ImportError_(f"{path.name} has no video stream")
    v = vs[0]
    fr = v.get("avg_frame_rate", "0/1")
    try:
        n, den = fr.split("/")
        fps = round(float(n) / float(den), 3) if float(den) else None
    except ValueError:
        fps = None
    return {
        "width": int(v.get("width", 0)), "height": int(v.get("height", 0)), "codec": v.get("codec_name"), "pix_fmt": v.get("pix_fmt"), "fps": fps,
        "duration": float(d.get("format", {}).get("duration") or v.get("duration") or 0), "has_audio": any(s.get("codec_type") == "audio" for s in d.get("streams", [])),
        "bytes": int(d.get("format", {}).get("size") or path.stat().st_size),
    }


def validate_name(path: Path, inputs_dir: Path, presets_dir: Path) -> tuple[str, str]:
    parsed = realmod.parse_name(path.name)
    if not parsed:
        raise ImportError_(f"'{path.name}' does not match <input-id>__<preset-id>.mp4 (lowercase, hyphens), e.g. alley__dolly-in.mp4")
    inp, preset = parsed
    if not (inputs_dir / f"{inp}.json").is_file() or not any((inputs_dir / f"{inp}{e}").is_file() for e in (".jpg", ".png")):
        known = sorted(p.stem for p in inputs_dir.glob("*.json"))
        raise ImportError_(f"unknown input id '{inp}' (known: {', '.join(known)})")
    if not (presets_dir / f"{preset}.json").is_file() or preset.startswith("_"):
        known = sorted(p.stem for p in presets_dir.glob("*.json") if not p.stem.startswith("_"))
        raise ImportError_(f"unknown preset id '{preset}' (known: {', '.join(known)})")
    return inp, preset


def transcode(src: Path, dst: Path, max_bytes: int, has_audio: bool) -> int:
    """H.264 yuv420p, <=1280 wide, shrink CRF ladder until under max_bytes. Returns the CRF used."""
    for crf in CRF_LADDER:
        cmd = [ffmpeg_bin(), "-y", "-loglevel", "error", "-i", str(src), "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:v", "+bitexact", "-map", "0:v:0", "-vf", "scale='min(1280,iw)':-2:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-movflags", "+faststart"]
        cmd += ["-map", "0:a:0", "-c:a", "aac", "-b:a", "96k"] if has_audio else ["-an"]
        cmd.append(str(dst))
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise ImportError_(f"ffmpeg failed: {r.stderr.strip()[-300:]}")
        if dst.stat().st_size <= max_bytes:
            return crf
    raise ImportError_(f"could not get {src.name} under {max_bytes / 1e6:.1f} MB even at CRF {CRF_LADDER[-1]}; trim it or lower the resolution")


def strip_metadata(path: Path) -> None:
    """Lossless remux without container/stream metadata (Comfy Cloud embeds the whole workflow JSON as an mp4 tag;
    other tools may add titles, encoders or paths). Streams are copied, never re-encoded."""
    tmp = path.with_name(path.stem + ".stripped.mp4")
    cmd = [ffmpeg_bin(), "-y", "-loglevel", "error", "-i", str(path), "-map", "0", "-c", "copy", "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:v", "+bitexact", "-flags:a", "+bitexact",
           "-movflags", "+faststart", str(tmp)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not tmp.is_file() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        raise ImportError_(f"could not strip metadata from {path.name}: {r.stderr.strip()[-200:]}")
    tmp.replace(path)


def import_clip(path: Path, *, real_dir: Path, inputs_dir: Path, presets_dir: Path, max_mb: float = 6.0, force: bool = False, check_only: bool = False) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        raise ImportError_(f"file not found: {path}")
    inp, preset = validate_name(path, inputs_dir, presets_dir)
    dest = real_dir / path.name
    if path.resolve() != dest.resolve():
        if check_only:
            dest = path
        else:
            real_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)
    info = probe(dest)
    if not 0.5 <= info["duration"] <= 30:
        raise ImportError_(f"{path.name}: duration {info['duration']:.1f}s is outside 0.5-30 s; is this the right file?")
    rp = dest.with_suffix(".recipe.json")
    out_sha = sha256_file(dest)
    if rp.is_file() and not force and not check_only:
        try:
            if json.loads(rp.read_text()).get("output_sha256") == out_sha:
                return {"file": dest.name, "status": "unchanged", "input": inp, "preset": preset, **info}
        except ValueError:
            pass
    max_bytes = int(max_mb * 1e6)
    needs = info["bytes"] > max_bytes or info["width"] > 1280 or info["codec"] != "h264" or info["pix_fmt"] != "yuv420p"
    status = "ok" if not needs else "needs-transcode"
    if check_only:
        return {"file": dest.name, "status": status, "input": inp, "preset": preset, **info}
    orig_sha, crf = out_sha, None
    if needs:
        orig_dir = real_dir / "_originals"
        orig_dir.mkdir(exist_ok=True)
        orig = orig_dir / dest.name
        shutil.move(str(dest), orig)
        try:
            crf = transcode(orig, dest, max_bytes, info["has_audio"])
        except Exception:
            shutil.move(str(orig), dest)  # put the original back
            raise
        strip_metadata(dest)
        info_out = probe(dest)
        out_sha = sha256_file(dest)
        status = "transcoded"
    else:
        (real_dir / "_originals").mkdir(exist_ok=True)
        shutil.copyfile(dest, real_dir / "_originals" / dest.name)
        strip_metadata(dest)
        info_out = probe(dest)
        out_sha = sha256_file(dest)
        status = "metadata-stripped"
    notes_path = dest.with_suffix(".json")
    notes: dict[str, Any] = {}
    if notes_path.is_file():
        try:
            notes = json.loads(notes_path.read_text())
            if not isinstance(notes, dict):
                raise ValueError
        except ValueError:
            raise ImportError_(f"{notes_path.name} is not a JSON object") from None
    src_img = next(p for e in (".jpg", ".png") if (p := inputs_dir / f"{inp}{e}").is_file())
    meta = json.loads((inputs_dir / f"{inp}.json").read_text())
    model = notes.get("model") or "LTX-2.3 (Comfy Cloud template 'LTX-2.3: Image to Video')"
    recipe = make_recipe(
        kind="shot", engine="comfy-cloud-web", model=model, source_name=meta.get("title", inp), source_sha256=sha256_file(src_img), preset_id=preset,
        prompt=str(notes.get("prompt", "")), seed=int(notes["seed"]) if str(notes.get("seed", "")).lstrip("-").isdigit() else 0,
        workflow_sha256=sha256_file(wf) if (wf := ROOT / "workflows" / "real" / str(notes.get("workflow_file", ""))).is_file() and notes.get("workflow_file") else None,
        params={"resolution": notes.get("resolution") or f"{info_out['width']}x{info_out['height']}", "duration_s": notes.get("duration") or round(info_out["duration"], 2), "fps": info_out["fps"], "template": notes.get("template"), "settings": notes.get("settings")},
        simulated=False, credits_used=notes.get("credits_used"),
        extra={
            "provenance": notes.get("provenance") or realmod.PROVENANCE, "quality": notes.get("quality"), "seed_note": notes.get("seed_note"), "workflow_file": notes.get("workflow_file"), "badge": realmod.badge_text(notes), "platform": notes.get("platform") or realmod.DEFAULT_PLATFORM,
            "notes_file": notes_path.name if notes else None, "notes_missing": not notes, "notes": notes, "run_date": notes.get("date"),
            "output_sha256": out_sha, "original_sha256": orig_sha, "transcoded": status == "transcoded", "metadata_stripped": True, "transcode_crf": crf,
            "imported": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    )
    rp.write_text(json.dumps(recipe, indent=2) + "\n")
    return {"file": dest.name, "status": status, "input": inp, "preset": preset, "notes": bool(notes), "mb": round(dest.stat().st_size / 1e6, 2), **info_out}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", type=Path, help="mp4 files to copy into examples/real/ and import (default: everything already there)")
    ap.add_argument("--dir", type=Path, default=ROOT / "examples" / "real")
    ap.add_argument("--max-mb", type=float, default=6.0)
    ap.add_argument("--force", action="store_true", help="re-import even if unchanged")
    ap.add_argument("--check", action="store_true", help="validate and probe only")
    a = ap.parse_args(argv)
    files = a.files or sorted(p for p in a.dir.glob("*.mp4"))
    if not files:
        print(f"No .mp4 files found in {a.dir}. Drop <input>__<preset>.mp4 files there (see docs/REAL_RUN.md).")
        return 0
    bad = 0
    for f in files:
        try:
            r = import_clip(f, real_dir=a.dir, inputs_dir=ROOT / "examples" / "inputs", presets_dir=ROOT / "presets", max_mb=a.max_mb, force=a.force, check_only=a.check)
            warn = "" if r.get("notes", True) or a.check else "   (no <name>.json notes file: recipe says notes_missing)"
            print(f"OK   {r['file']:34s} {r['status']:15s} {r['width']}x{r['height']} {r['duration']:.1f}s{warn}")
        except ImportError_ as e:
            bad += 1
            print(f"FAIL {Path(f).name}: {e}", file=sys.stderr)
    print(f"\n{len(files) - bad} ok, {bad} failed" + ("" if bad else "; the app lists these automatically (restart not needed)."))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
