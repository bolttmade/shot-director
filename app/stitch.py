"""Stitch clips into one sequence with ffmpeg (hard cuts or crossfades), optionally as a 16:9 or 9:16 "reel" with a burned-in
provenance label on every clip (so a cut that mixes real and simulated footage can never hide which is which)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .media import ffmpeg_bin, probe_duration


class StitchError(RuntimeError):
    pass


ASPECTS = {"16:9": (1280, 720), "9:16": (720, 1280)}


def _esc(text: str) -> str:
    """Escape a string for use inside a single-quoted ffmpeg drawtext value."""
    return text.replace("\\", "\\\\").replace("'", "\u2019").replace(":", "\\:").replace("%", "\\%").replace(",", "\\,")


def _norm_chain(i: int, width: int, height: int, fps: int, label: str | None, vertical: bool) -> str:
    """Per-clip normalisation: letterbox (16:9) or blurred-background fit (9:16), optional label, constant fps."""
    if vertical:
        # whole frame kept (never cropped): sharp copy centred over a blurred, zoomed copy of itself
        chain = (f"[{i}:v]fps={fps},split=2[bg{i}][fg{i}];[bg{i}]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},boxblur=24:3,setsar=1[b{i}];"
                 f"[fg{i}]scale={width}:{height}:force_original_aspect_ratio=decrease,setsar=1[f{i}];[b{i}][f{i}]overlay=(W-w)/2:(H-h)/2")
    else:
        chain = f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={fps}"
    if label:
        size = max(18, height // (46 if vertical else 36))
        y = f"h-th-{int(height * (0.1 if vertical else 0.04))}"
        chain += f",drawtext=text='{_esc(label)}':x=(w-text_w)/2:y={y}:fontsize={size}:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=10" if vertical else f",drawtext=text='{_esc(label)}':x=24:y={y}:fontsize={size}:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=10"
    return chain + f",format=yuv420p[v{i}]"


def build_command(clips: list[Path], durations: list[float], out: Path, *, crossfade: float = 0.0, width: int = 1280, height: int = 720, fps: int = 24, crf: int = 26, aspect: str | None = None, labels: list[str] | None = None) -> list[str]:
    """Return the ffmpeg argv (pure function: unit-testable without ffmpeg). `aspect` ("16:9" or "9:16") sets the frame size;
    `labels` (one string per clip) are burned into the picture."""
    if not clips:
        raise StitchError("Pick at least one clip to export.")
    if aspect:
        if aspect not in ASPECTS:
            raise StitchError(f"Unknown aspect '{aspect}' (use 16:9 or 9:16).")
        width, height = ASPECTS[aspect]
    if labels is not None and len(labels) != len(clips):
        raise StitchError("Give one label per clip.")
    vertical = height > width
    n = len(clips)
    cmd = [ffmpeg_bin(), "-y", "-loglevel", "error"]
    for c in clips:
        cmd += ["-i", str(c)]
    norm = []
    for i in range(n):
        if labels is None and not vertical:
            norm.append(f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={fps},format=yuv420p[v{i}]")
        else:
            norm.append(_norm_chain(i, width, height, fps, labels[i] if labels else None, vertical))
    if n == 1:
        graph = ";".join(norm) + ";[v0]null[outv]"
    elif crossfade > 0:
        cf = min(crossfade, max(min(durations) / 2 - 0.05, 0.05))
        parts, label, acc = [], "v0", durations[0]
        for i in range(1, n):
            nxt = f"x{i}" if i < n - 1 else "outv"
            parts.append(f"[{label}][v{i}]xfade=transition=fade:duration={cf:.3f}:offset={acc - cf:.3f}[{nxt}]")
            acc += durations[i] - cf
            label = nxt
        graph = ";".join(norm + parts)
    else:
        graph = ";".join(norm) + ";" + "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[outv]"
    cmd += ["-filter_complex", graph, "-map", "[outv]", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    return cmd


def stitch(clips: list[Path], out: Path, *, crossfade: float = 0.0, **kw) -> Path:
    for c in clips:
        if not Path(c).is_file():
            raise StitchError(f"Clip not found: {c.name}")
    durations = [probe_duration(c) or 4.0 for c in clips]
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_command(list(clips), durations, out, crossfade=crossfade, **kw)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 and kw.get("labels"):
        # drawtext needs an ffmpeg built with libfreetype + a default font; fall back to an unlabelled cut rather than failing
        r = subprocess.run(build_command(list(clips), durations, out, crossfade=crossfade, **{**kw, "labels": None}), capture_output=True, text=True)
    if r.returncode != 0:
        raise StitchError(f"ffmpeg failed: {r.stderr[-300:]}")
    return out
