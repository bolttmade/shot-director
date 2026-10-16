"""Stitch clips into one sequence with ffmpeg (hard cuts or crossfades)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .media import ffmpeg_bin, probe_duration


class StitchError(RuntimeError):
    pass


def build_command(clips: list[Path], durations: list[float], out: Path, *, crossfade: float = 0.0, width: int = 1280, height: int = 720, fps: int = 24, crf: int = 26) -> list[str]:
    """Return the ffmpeg argv (pure function: unit-testable without ffmpeg)."""
    if not clips:
        raise StitchError("Pick at least one clip to export.")
    n = len(clips)
    cmd = [ffmpeg_bin(), "-y", "-loglevel", "error"]
    for c in clips:
        cmd += ["-i", str(c)]
    norm = []
    for i in range(n):
        norm.append(f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={fps},format=yuv420p[v{i}]")
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
    if r.returncode != 0:
        raise StitchError(f"ffmpeg failed: {r.stderr[-300:]}")
    return out
