"""Virtual camera: depth-aware re-projection used by the *demo fixtures* engine.

Given one still and a depth map (near=0 .. far=1) this renders what a pinhole camera
would see after moving/rotating/zooming. It is a geometric approximation (single layer,
no inpainting of disocclusions) so it is **not** a generative model and every clip made
with it is labelled "simulated" throughout the app.

Camera channels (all optional, interpolated over normalised time t in 0..1):

    right, up, forward   metres of camera translation (scene is ~3 m .. 30 m deep)
    yaw, pitch, roll     degrees (yaw + = pan right, pitch + = tilt up)
    zoom                 focal-length multiplier (1 = unchanged)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

import numpy as np
from PIL import Image, ImageFilter

ZOOM_SPLAT_MAX = 1.0
NEAR_M = 3.0
FAR_M = 30.0
CHANNELS = ("right", "up", "forward", "yaw", "pitch", "roll", "zoom")
DEFAULTS = {c: 0.0 for c in CHANNELS} | {"zoom": 1.0}


# ----------------------------------------------------------------------------- easing
def ease(name: str, t: float) -> float:
    t = min(max(t, 0.0), 1.0)
    if name == "linear":
        return t
    if name == "in":
        return t * t * t
    if name == "out":
        return 1 - (1 - t) ** 3
    if name == "snap":  # slow start, sudden whip, soft landing (whip pans, crash zooms)
        return t * t * t * (t * (6 * t - 15) + 10)
    return t * t * (3 - 2 * t)  # inout


@dataclass
class CameraPath:
    """Keyframed camera path described by a preset's ``virtual_camera`` block."""

    keys: list[dict[str, float]]
    ease: str = "inout"
    shake: float = 0.0  # handheld amplitude, 1.0 ~ documentary handheld
    motion_blur: int = 0  # extra sub-frames averaged per frame
    rack: dict[str, float] | None = None  # {"from": v, "to": v} focus depth in 0..1
    seed: int = 7
    _phases: np.ndarray = field(default=None, repr=False)  # type: ignore[assignment]

    @classmethod
    def from_spec(cls, spec: dict[str, Any]) -> "CameraPath":
        return cls(
            keys=[{"t": float(k.get("t", i / max(len(spec["keys"]) - 1, 1))), **{c: float(v) for c, v in k.items() if c != "t"}} for i, k in enumerate(spec["keys"])],
            ease=spec.get("ease", "inout"),
            shake=float(spec.get("shake", 0.0)),
            motion_blur=int(spec.get("motion_blur", 0)),
            rack=spec.get("rack"),
            seed=int(spec.get("seed", 7)),
        )

    def __post_init__(self) -> None:
        rng = np.random.default_rng(self.seed)
        self._phases = rng.uniform(0, 2 * math.pi, size=(5, 3))

    def at(self, t: float) -> dict[str, float]:
        te = ease(self.ease, t)
        ks = sorted(self.keys, key=lambda k: k["t"])
        out = dict(DEFAULTS)
        for ch in CHANNELS:
            pts = [(k["t"], k.get(ch, DEFAULTS[ch])) for k in ks]
            if te <= pts[0][0]:
                out[ch] = pts[0][1]
            elif te >= pts[-1][0]:
                out[ch] = pts[-1][1]
            else:
                for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
                    if t0 <= te <= t1:
                        a = (te - t0) / max(t1 - t0, 1e-9)
                        out[ch] = v0 + (v1 - v0) * a
                        break
        if self.shake:
            s = self.shake
            for i, ch in enumerate(("right", "up", "yaw", "pitch", "roll")):
                amp = (0.035, 0.03, 0.45, 0.4, 0.5)[i] * s
                n = sum(math.sin(2 * math.pi * f * t * 4.0 + self._phases[i, j]) / (j + 1) for j, f in enumerate((0.9, 2.3, 4.1)))
                out[ch] += amp * n
        return out

    def focus(self, t: float) -> float | None:
        if not self.rack:
            return None
        a = ease("inout", t)
        return self.rack["from"] + (self.rack["to"] - self.rack["from"]) * a


# ----------------------------------------------------------------------------- sampling
def _reflect(v: np.ndarray, n: int) -> np.ndarray:
    # reflect coordinates into [0, n-1]
    m = 2 * (n - 1)
    v = np.abs(v) % m
    return np.where(v > n - 1, m - v, v)


def _bilinear(img: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    x = _reflect(x, w)
    y = _reflect(y, h)
    x0 = np.floor(x).astype(np.int32)
    y0 = np.floor(y).astype(np.int32)
    x1 = np.minimum(x0 + 1, w - 1)
    y1 = np.minimum(y0 + 1, h - 1)
    fx = (x - x0).astype(np.float32)
    fy = (y - y0).astype(np.float32)
    if img.ndim == 3:
        fx = fx[..., None]
        fy = fy[..., None]
    top = img[y0, x0] * (1 - fx) + img[y0, x1] * fx
    bot = img[y1, x0] * (1 - fx) + img[y1, x1] * fx
    return top * (1 - fy) + bot * fy


def _rotation(yaw: float, pitch: float, roll: float) -> np.ndarray:
    # camera frame: x right, y down, z forward
    y, p, r = map(math.radians, (yaw, pitch, roll))  # pitch + = look up (forward tilts toward -y)
    ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    rx = np.array([[1, 0, 0], [0, math.cos(p), -math.sin(p)], [0, math.sin(p), math.cos(p)]])
    rz = np.array([[math.cos(r), -math.sin(r), 0], [math.sin(r), math.cos(r), 0], [0, 0, 1]])
    return ry @ rx @ rz


@dataclass
class Scene:
    """A still + depth, pre-converted for rendering."""

    rgb: np.ndarray  # H,W,3 float32 0..255
    depth: np.ndarray  # H,W float32 metres
    blurred: np.ndarray | None = None
    _grid: Any = None
    _order: Any = None

    @classmethod
    def from_images(cls, image: Image.Image, depth01: np.ndarray | Image.Image | None = None, max_w: int = 1600) -> "Scene":
        image = image.convert("RGB")
        if image.width > max_w:
            image = image.resize((max_w, round(image.height * max_w / image.width)), Image.LANCZOS)
        rgb = np.asarray(image, dtype=np.float32)
        if depth01 is None:
            d01 = pseudo_depth(image)
        else:
            if isinstance(depth01, Image.Image):
                depth01 = np.asarray(depth01.convert("L").resize(image.size, Image.BILINEAR), dtype=np.float32) / 255.0
            d01 = np.asarray(depth01, dtype=np.float32)
            if d01.shape != rgb.shape[:2]:
                d01 = np.asarray(Image.fromarray((d01 * 255).astype(np.uint8)).resize(image.size, Image.BILINEAR), dtype=np.float32) / 255.0
        depth = NEAR_M + (FAR_M - NEAR_M) * d01
        return cls(rgb=rgb, depth=depth.astype(np.float32))

    def blurred_rgb(self) -> np.ndarray:
        if self.blurred is None:
            im = Image.fromarray(self.rgb.astype(np.uint8)).filter(ImageFilter.GaussianBlur(7))
            self.blurred = np.asarray(im, dtype=np.float32)
        return self.blurred


def pseudo_depth(image: Image.Image) -> np.ndarray:
    """Cheap monocular depth guess for uploads (top = far, bottom = near, centre bulges forward).

    This is a heuristic, not a depth model. It exists so DEMO mode can animate *any* image.
    """
    w, h = image.size
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    yn, xn = ys / (h - 1), xs / (w - 1)
    ramp = 1.0 - yn**0.85
    radial = np.sqrt(((xn - 0.5) * 1.1) ** 2 + ((yn - 0.52) * 1.3) ** 2)
    d = 0.68 * ramp + 0.32 * np.clip(radial * 1.6, 0, 1)
    lum = np.asarray(image.convert("L").resize((w, h)), dtype=np.float32) / 255.0
    d = d + 0.08 * (lum - lum.mean())
    im = Image.fromarray((np.clip(d, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(max(w, h) / 60))
    return np.asarray(im, dtype=np.float32) / 255.0


@np.errstate(invalid="ignore")
def _fill_rows(zbuf: np.ndarray, color: np.ndarray, hole: np.ndarray):
    """Fill holes row-wise. Where both neighbours are on the same surface the hole is a
    stretch crack: interpolate depth (colour is re-sampled later). Where they differ it is
    a disocclusion: copy depth *and colour* from the farther neighbour (reveal background)."""
    h, w = zbuf.shape
    ar = np.arange(w)[None, :].repeat(h, 0)
    left = np.maximum.accumulate(np.where(~hole, ar, -1), axis=1)
    right = np.minimum.accumulate(np.where(~hole, ar, w * 4)[:, ::-1], axis=1)[:, ::-1]
    rows = np.arange(h)[:, None]
    lc = np.clip(left, 0, w - 1)
    rc = np.clip(right, 0, w - 1)
    lz = np.where(left >= 0, zbuf[rows, lc], -np.inf)
    rz = np.where(right < w, zbuf[rows, rc], -np.inf)
    both = np.isfinite(lz) & np.isfinite(rz)
    similar = both & (np.abs(lz - rz) < 0.08 * np.maximum(lz, rz) + 0.5)
    use_left = lz >= rz
    src_x = np.where(use_left, lc, rc)
    far_z = np.where(use_left, lz, rz)
    t = (ar - left) / np.maximum(right - left, 1)
    interp_z = np.where(both, lz + (rz - lz) * np.clip(t, 0, 1), far_z)
    ok = hole & np.isfinite(far_z)
    interp = ok & similar
    far = ok & ~similar
    z = np.where(interp, interp_z, np.where(far, far_z, zbuf))
    color[far] = color[rows.repeat(w, 1)[far], src_x[far]]
    return z, ok, interp, far


def render(scene: Scene, cam: dict[str, float], out_w: int, out_h: int, *, base_zoom: float = 1.12, iters: int = 3, focus: float | None = None) -> np.ndarray:
    """Render one frame (uint8 H,W,3): forward-splat depth+colour with a z-buffer, then
    fill disocclusions from the farther neighbour (so objects reveal *background*)."""
    zoom = cam.get("zoom", 1.0)
    if zoom > ZOOM_SPLAT_MAX:  # beyond this a forward splat gets too sparse: render wider, then punch in cleanly
        inner = render(scene, {**cam, "zoom": ZOOM_SPLAT_MAX}, out_w, out_h, base_zoom=base_zoom, iters=iters, focus=focus)
        k = zoom / ZOOM_SPLAT_MAX
        cw, ch = out_w / k, out_h / k
        box = ((out_w - cw) / 2, (out_h - ch) / 2, (out_w + cw) / 2, (out_h + ch) / 2)
        im = Image.fromarray(inner).resize((out_w, out_h), Image.LANCZOS, box=box).filter(ImageFilter.UnsharpMask(radius=1.4, percent=60, threshold=2))
        return np.asarray(im)
    hs, ws = scene.rgb.shape[:2]
    fs = 0.9 * ws
    fo = fs * (out_w / ws) * base_zoom * zoom
    if scene._grid is None:
        ys, xs = np.mgrid[0:hs, 0:ws].astype(np.float32)
        scene._grid = (((xs - ws / 2 + 0.5) / fs).ravel(), ((ys - hs / 2 + 0.5) / fs).ravel())
        scene._order = np.argsort(-scene.depth.ravel(), kind="stable")  # far -> near
    u, v = scene._grid
    z = scene.depth.ravel()
    rot = _rotation(cam.get("yaw", 0.0), cam.get("pitch", 0.0), cam.get("roll", 0.0)).astype(np.float32)
    t = np.array([cam.get("right", 0.0), -cam.get("up", 0.0), cam.get("forward", 0.0)], dtype=np.float32)
    px, py, pz = u * z - t[0], v * z - t[1], z - t[2]
    cx = rot[0, 0] * px + rot[1, 0] * py + rot[2, 0] * pz  # world -> output camera: R^T (P - T)
    cy = rot[0, 1] * px + rot[1, 1] * py + rot[2, 1] * pz
    cz = rot[0, 2] * px + rot[1, 2] * py + rot[2, 2] * pz
    czs = np.maximum(cz, 0.25)
    xo = np.rint(fo * cx / czs + out_w / 2 - 0.5).astype(np.int32)
    yo = np.rint(fo * cy / czs + out_h / 2 - 0.5).astype(np.int32)
    ok = (cz > 0.25) & (xo >= 0) & (xo < out_w) & (yo >= 0) & (yo < out_h)
    order = scene._order
    order = order[ok[order]]
    idx = yo[order] * out_w + xo[order]
    zbuf = np.full(out_w * out_h, np.inf, np.float32)
    zbuf[idx] = cz[order]  # far first, near last: nearest wins
    col = np.zeros((out_w * out_h, 3), np.float32)
    col[idx] = scene.rgb.reshape(-1, 3)[order]
    zbuf = zbuf.reshape(out_h, out_w)
    col = col.reshape(out_h, out_w, 3)
    hole = ~np.isfinite(zbuf)
    zb = np.where(hole, -np.inf, zbuf)
    interp = np.zeros_like(hole)
    filled = ~hole
    if hole.any():
        zb, ok1, interp, far = _fill_rows(zb, col, hole)
        filled = filled | ok1
        left = hole & ~ok1
        if left.any():  # vertical pass for whatever rows could not fill
            zt, ok2, interp2, far2 = _fill_rows(zb.T.copy(), col.transpose(1, 0, 2), left.T)
            zb = np.where(ok2.T, zt.T, zb)
            interp = interp | interp2.T
            filled = filled | ok2.T
    # crisp re-sample for real splats and interpolated cracks
    xs, ys = np.meshgrid(np.arange(out_w, dtype=np.float32), np.arange(out_h, dtype=np.float32))
    zf = np.where(np.isfinite(zb), zb, FAR_M)
    ox, oy = (xs - out_w / 2 + 0.5) / fo, (ys - out_h / 2 + 0.5) / fo
    qx, qy, qz = ox * zf, oy * zf, zf
    wx = rot[0, 0] * qx + rot[0, 1] * qy + rot[0, 2] * qz + t[0]
    wy = rot[1, 0] * qx + rot[1, 1] * qy + rot[1, 2] * qz + t[1]
    wz = np.maximum(rot[2, 0] * qx + rot[2, 1] * qy + rot[2, 2] * qz + t[2], 0.25)
    sx, sy = fs * wx / wz + ws / 2 - 0.5, fs * wy / wz + hs / 2 - 0.5
    crisp = _bilinear(scene.rgb, sx, sy)
    sd = _bilinear(scene.depth, sx, sy)
    good = ((~hole) | interp) & (np.abs(sd - wz) < 0.08 * wz + 0.5)
    col = np.where((good | ~filled)[..., None], crisp, col)  # never-filled borders: mirrored background, not black
    out = col
    if focus is not None:
        z01 = (zf - NEAR_M) / (FAR_M - NEAR_M)
        w = np.clip(np.abs(z01 - focus) * 5.0 - 0.15, 0, 1)[..., None]
        bl = np.asarray(Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(max(out_w / 160, 2))), np.float32)
        out = col * (1 - w) + bl * w
    return np.clip(out, 0, 255).astype(np.uint8)


def frames(scene: Scene, path: CameraPath, n_frames: int, out_w: int, out_h: int, *, base_zoom: float = 1.12, iters: int = 4, on_frame: Callable[[int, int], None] | None = None) -> Iterable[np.ndarray]:
    for i in range(n_frames):
        t = i / max(n_frames - 1, 1)
        if path.motion_blur:
            acc = np.zeros((out_h, out_w, 3), np.float32)
            n = path.motion_blur + 1
            for k in range(n):
                tk = min(max(t + (k - (n - 1) / 2) / max(n_frames - 1, 1) * 0.9, 0), 1)
                acc += render(scene, path.at(tk), out_w, out_h, base_zoom=base_zoom, iters=iters, focus=path.focus(tk))
            frame = (acc / n).astype(np.uint8)
        else:
            frame = render(scene, path.at(t), out_w, out_h, base_zoom=base_zoom, iters=iters, focus=path.focus(t))
        if on_frame:
            on_frame(i + 1, n_frames)
        yield frame
