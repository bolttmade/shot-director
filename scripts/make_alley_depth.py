#!/usr/bin/env python3
"""Generate examples/inputs/alley_depth.png for the alley still: a classical, heuristic depth map (no model, no download).

Why: the Demo engine's virtual camera (app/vcam.py) needs depth (near=dark .. far=bright). Without it, uploads get the generic
`pseudo_depth` guess. The alley is a one-point-perspective corridor, so we can do much better with geometry:

  1. Corridor model. The vanishing point (VP) is placed by eye. Floor pixels below the horizon get Z = H_CAM*f / (y - vy);
     wall pixels get Z = W_HALF*f / |x - vx|; the nearer surface wins (Z = min(floor, wall)). Above the horizon the same wall term
     applies, and nothing special is done for the sky.
  2. Foreground object. The parked scooter is covered by three hand-placed ellipses pulled to ~3 m.
  3. Edge snapping. A guided filter (box filters in numpy, radius 8) with the still as guide makes depth edges follow image edges; the result is contrast-stretched (2nd..98th percentile).

This is a heuristic, NOT a measured or learned depth map: parallax is plausible, not exact, and it is only used for the
simulated demo camera (labelled simulated). The parameters are the constants below; re-run to regenerate:

    .venv/bin/python scripts/make_alley_depth.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC, DST = ROOT / "examples" / "inputs" / "alley.jpg", ROOT / "examples" / "inputs" / "alley_depth.png"

VP = (0.49, 0.57)            # vanishing point (x, y) as fractions of width/height, placed by eye
H_CAM, W_HALF, F = 1.0, 2.6, 0.9   # camera height m, half alley width m, focal length (in image-heights)
Z_NEAR, Z_FAR = 1.5, 60.0
SCOOTER_BLOBS = [(0.245, 0.64, 0.105, 0.17), (0.215, 0.42, 0.06, 0.06), (0.23, 0.50, 0.075, 0.07)]   # (cx, cy, rx, ry) as fractions
SCOOTER_Z = 3.2


def box(a: np.ndarray, r: int) -> np.ndarray:
    k = 2 * r + 1
    p = np.pad(a, r, mode="edge")
    c = p.cumsum(0).cumsum(1)
    c = np.pad(c, ((1, 0), (1, 0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k])[: a.shape[0], : a.shape[1]] / (k * k)


def guided(guide: np.ndarray, src: np.ndarray, r: int = 8, eps: float = 1e-3) -> np.ndarray:
    mg, ms = box(guide, r), box(src, r)
    cov = box(guide * src, r) - mg * ms
    var = box(guide * guide, r) - mg * mg
    a = cov / (var + eps)
    b = ms - a * mg
    return box(a, r) * guide + box(b, r)


def make(src: Path = SRC, dst: Path = DST) -> Path:
    im = Image.open(src).convert("RGB")
    w, h = im.size
    rgb = np.asarray(im, np.float32) / 255.0
    lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    ys, xs = (np.mgrid[0:h, 0:w].astype(np.float32) + 0.5)
    ys, xs = ys / h, xs / w
    vx, vy = VP
    dy, dx = ys - vy, np.abs(xs - vx) * (w / h)
    floor = np.where(dy > 0.004, H_CAM * F / np.maximum(dy, 0.004), Z_FAR)
    wall = W_HALF * F / np.maximum(dx, 0.004)
    z = np.minimum(np.minimum(floor, wall), Z_FAR)
    for (cx, cy, rx, ry) in SCOOTER_BLOBS:                              # hand-placed ellipses over the scooter
        e = ((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2 < 1.0
        z[e] = np.minimum(z[e], SCOOTER_Z)
    z = np.clip(z, Z_NEAR, Z_FAR)
    d = np.log(z / Z_NEAR) / np.log(Z_FAR / Z_NEAR)                    # 0 near .. 1 far
    d = np.clip(guided(lum, d.astype(np.float32), r=6, eps=4e-3), 0, 1)
    lo, hi = np.percentile(d, [2, 98])
    d = np.clip((d - lo) / (hi - lo), 0, 1)                            # use the full range
    out = (40 + d * 215).astype(np.uint8)                              # same range as the procedural depth maps (40 near .. 255 far)
    Image.fromarray(out, "L").save(dst, optimize=True)
    return dst


if __name__ == "__main__":
    print("wrote", make())
