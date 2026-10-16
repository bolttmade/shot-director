"""ffmpeg helpers (frames -> H.264) and image utilities."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image


def ffmpeg_bin() -> str:
    p = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if not p:
        raise RuntimeError("ffmpeg not found. Install it (apt install ffmpeg / brew install ffmpeg) or set FFMPEG=/path/to/ffmpeg")
    return p


def ffprobe_bin() -> str | None:
    return os.environ.get("FFPROBE") or shutil.which("ffprobe")


def probe_duration(path: Path) -> float | None:
    fp = ffprobe_bin()
    if not fp:
        return None
    try:
        out = subprocess.run([fp, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)], capture_output=True, text=True, timeout=20, check=True).stdout
        return float(json.loads(out)["format"]["duration"])
    except Exception:
        return None


def encode_frames(frames: Iterable[np.ndarray], out_path: Path, *, width: int, height: int, fps: int = 24, crf: int = 28) -> Path:
    """Pipe RGB frames into ffmpeg -> H.264 yuv420p mp4 (web-friendly, faststart)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg_bin(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        assert proc.stdin
        for f in frames:
            proc.stdin.write(np.ascontiguousarray(f, dtype=np.uint8).tobytes())
        proc.stdin.close()
        err = proc.stderr.read().decode() if proc.stderr else ""
        if proc.wait() != 0:
            raise RuntimeError(f"ffmpeg failed: {err[-400:]}")
    except BrokenPipeError:
        err = proc.stderr.read().decode() if proc.stderr else ""
        raise RuntimeError(f"ffmpeg closed the pipe: {err[-400:]}")
    finally:
        if proc.poll() is None:
            proc.kill()
    return out_path


def save_jpg(arr: np.ndarray | Image.Image, path: Path, quality: int = 82) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    im = arr if isinstance(arr, Image.Image) else Image.fromarray(arr)
    im.convert("RGB").save(path, "JPEG", quality=quality, optimize=True)
    return path


def first_frame(video: Path, out: Path) -> Path:
    subprocess.run([ffmpeg_bin(), "-y", "-loglevel", "error", "-i", str(video), "-frames:v", "1", str(out)], check=True)
    return out
