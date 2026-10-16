"""Procedurally generated sample scenes (RGB + depth), CC0 by construction.

Everything here is drawn from maths and a seeded RNG: no photographs, no people, no
brands, no logos, no scraped data. Each scene returns an RGB image and a depth map
(0 = near, 1 = far) so the demo engine can do real parallax camera moves.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1600, 900


@dataclass
class Art:
    id: str
    title: str
    rgb: Image.Image
    depth: np.ndarray  # float32 0..1
    subject: tuple[float, float]  # normalised (x, y) of the hero element
    blurb: str


def _lerp(a, b, t):
    a = np.asarray(a, np.float32)
    b = np.asarray(b, np.float32)
    return a + (b - a) * t


def _gradient(stops: list[tuple[float, tuple[int, int, int]]], h: int = H, w: int = W) -> np.ndarray:
    ys = np.linspace(0, 1, h, dtype=np.float32)
    out = np.zeros((h, w, 3), np.float32)
    for c in range(3):
        out[..., c] = np.interp(ys, [s[0] for s in stops], [s[1][c] for s in stops])[:, None]
    return out


def _glow(img: np.ndarray, cx: float, cy: float, r: float, color, strength: float = 1.0) -> None:
    ys, xs = np.mgrid[0:img.shape[0], 0:img.shape[1]].astype(np.float32)
    d = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2) / r
    g = np.exp(-d * d * 2.2)[..., None] * strength
    img += g * np.asarray(color, np.float32)


def _ridge(rng, base: float, amp: float, rough: float, w: int = W) -> np.ndarray:
    x = np.linspace(0, 1, w)
    y = np.zeros(w)
    for i in range(7):
        f = 1.4 * (1.9**i)
        y += (rough**i) * np.sin(2 * math.pi * f * x + rng.uniform(0, 6.28)) * (1 if i else 1.4)
    y = y / np.abs(y).max()
    return base + amp * y


def _fill_below(rgb, depth, curve, color, d, gradient_to=None, haze=None, haze_amt=0.0):
    h, w = depth.shape
    ys = np.arange(h, dtype=np.float32)[:, None]
    mask = ys >= curve[None, :]
    col = np.asarray(color, np.float32)
    layer = np.broadcast_to(col, rgb.shape).copy()
    if gradient_to is not None:
        top = curve.min()
        t = np.clip((ys - top) / max(h - top, 1), 0, 1)
        layer = _lerp(col, gradient_to, t[..., None]) * np.ones((1, w, 1), np.float32)
    if haze is not None and haze_amt:
        layer = _lerp(layer, haze, haze_amt)
    rgb[mask] = layer[mask]
    depth[mask] = d


def _finish(rgb: np.ndarray, rng, grain: float = 3.0, vignette: float = 0.28) -> Image.Image:
    h, w = rgb.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xs - w / 2) / (w / 2)) ** 2 + ((ys - h / 2) / (h / 2)) ** 2)
    rgb = rgb * (1 - vignette * np.clip(r - 0.35, 0, 1.2) ** 1.6)[..., None]
    rgb = rgb + rng.normal(0, grain, rgb.shape).astype(np.float32)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))


def _smooth(depth: np.ndarray, r: float = 2.0) -> np.ndarray:
    im = Image.fromarray((np.clip(depth, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im, np.float32) / 255.0


# ----------------------------------------------------------------------------- scenes
def alpine_dusk(seed: int = 11) -> Art:
    rng = np.random.default_rng(seed)
    rgb = _gradient([(0, (18, 20, 58)), (0.35, (74, 52, 108)), (0.55, (214, 112, 110)), (0.68, (252, 178, 108))])
    depth = np.ones((H, W), np.float32)
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    star = rng.random((H, W)) > 0.9985
    rgb[star & (ys < 330)] += 140
    _glow(rgb, 1020, 520, 380, (255, 150, 80), 0.55)
    _glow(rgb, 1020, 520, 90, (255, 230, 170), 0.9)
    disc = (xs - 1020) ** 2 + (ys - 520) ** 2 < 52**2
    rgb[disc] = (255, 238, 196)
    haze = np.array([244, 160, 112], np.float32)
    palette = [((78, 66, 118), 0.96, 0.6), ((64, 52, 104), 0.86, 0.5), ((46, 40, 84), 0.72, 0.38), ((30, 28, 62), 0.55, 0.22), ((16, 18, 40), 0.36, 0.0)]
    bases = [560, 600, 650, 706, 770]
    amps = [70, 80, 90, 100, 90]
    for (col, d, hz), b, a in zip(palette, bases, amps):
        curve = _ridge(rng, b, a, 0.52)
        _fill_below(rgb, depth, curve, col, d, gradient_to=np.asarray(col) * 0.7, haze=haze, haze_amt=hz * 0.55)
    # lake
    lake_top = 790
    m = ys >= lake_top
    refl = rgb[2 * lake_top - np.clip(ys, lake_top, 2 * lake_top - 0).astype(int)[m], xs.astype(int)[m]]
    rgb[m] = _lerp(refl, (24, 24, 52), 0.55)
    ripple = (np.sin(ys[m] * 0.55 + np.sin(xs[m] * 0.01) * 4) * 0.5 + 0.5)[:, None] * 22
    rgb[m] += ripple
    depth[m] = np.clip(0.55 - (ys[m] - lake_top) / (H - lake_top) * 0.45, 0.05, 1)
    # cabin
    cx, cy = 330, 742
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(img)
    dr.polygon([(cx - 70, cy - 40), (cx, cy - 92), (cx + 70, cy - 40)], fill=(22, 20, 36))
    dr.rectangle([cx - 56, cy - 40, cx + 56, cy + 22], fill=(34, 28, 44))
    dr.rectangle([cx - 14, cy - 22, cx + 22, cy + 2], fill=(255, 196, 96))
    dr.line([(cx - 14, cy - 10), (cx + 22, cy - 10)], fill=(150, 98, 40), width=2)
    dr.rectangle([cx + 30, cy - 80, cx + 44, cy - 52], fill=(28, 24, 40))
    rgb = np.asarray(img, np.float32)
    _glow(rgb, cx + 4, cy - 10, 70, (255, 170, 70), 0.5)
    cab = np.zeros((H, W), bool)
    cab[cy - 92 : cy + 22, cx - 70 : cx + 70] = True
    depth[cab] = np.minimum(depth[cab], 0.42)
    # pines
    for layer, (n, hmin, hmax, dep, col) in enumerate([(26, 90, 170, 0.28, (14, 20, 34)), (14, 170, 300, 0.14, (8, 12, 22))]):
        im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
        dr = ImageDraw.Draw(im)
        mask = Image.new("L", (W, H), 0)
        md = ImageDraw.Draw(mask)
        for _ in range(n):
            x = rng.uniform(-30, W + 30) if layer else rng.choice([rng.uniform(-30, 520), rng.uniform(1180, W + 30)])
            hh = rng.uniform(hmin, hmax)
            base = 900 if layer else 840 + rng.uniform(-10, 40)
            wid = hh * 0.34
            for k in range(5):
                t0 = k / 5
                y1 = base - hh * (t0 * 0.9)
                y2 = base - hh * (t0 * 0.9 + 0.32)
                ww = wid * (1 - t0 * 0.85)
                poly = [(x - ww, y1), (x, y2 - hh * 0.02), (x + ww, y1)]
                dr.polygon(poly, fill=col)
                md.polygon(poly, fill=255)
        rgb = np.asarray(im, np.float32)
        mk = np.asarray(mask) > 0
        depth[mk] = dep
    depth = _smooth(depth, 1.2)
    return Art("alpine-dusk", "Alpine Dusk", _finish(rgb, rng), depth, (0.21, 0.82), "Ridges, a lit cabin and a low sun: layered parallax.")


def neon_rooftops(seed: int = 23) -> Art:
    rng = np.random.default_rng(seed)
    rgb = _gradient([(0, (6, 8, 26)), (0.5, (30, 18, 64)), (0.75, (120, 40, 110)), (1, (210, 80, 120))])
    depth = np.ones((H, W), np.float32)
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    star = rng.random((H, W)) > 0.9988
    rgb[star & (ys < 400)] += 120
    _glow(rgb, 1180, 210, 260, (140, 120, 220), 0.35)
    rgb[(xs - 1180) ** 2 + (ys - 210) ** 2 < 70**2] = (240, 236, 255)
    cut = (xs - 1206) ** 2 + (ys - 192) ** 2 < 62**2
    rgb[cut & ((xs - 1180) ** 2 + (ys - 210) ** 2 < 70**2)] = (46, 28, 88)
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    layers = [  # (count, min w, max w, min h, max h, base y, depth, body, window prob)
        (22, 40, 90, 120, 330, 760, 0.95, (52, 36, 98), 0.18),
        (16, 60, 120, 190, 430, 800, 0.78, (36, 26, 76), 0.28),
        (10, 90, 170, 260, 520, 860, 0.58, (22, 18, 52), 0.34),
    ]
    out_depth = depth.copy()
    for n, wmin, wmax, hmin, hmax, base, dep, body, wp in layers:
        dr = ImageDraw.Draw(img)
        dmask = Image.new("L", (W, H), 0)
        dm = ImageDraw.Draw(dmask)
        x = -20
        while x < W:
            bw = rng.uniform(wmin, wmax)
            bh = rng.uniform(hmin, hmax)
            top = base - bh
            dr.rectangle([x, top, x + bw, H], fill=body)
            dm.rectangle([x, top, x + bw, H], fill=255)
            step = 14 + int(dep * 0 + (1 - dep) * 8)
            for wy in range(int(top) + 10, int(base), step):
                for wx in range(int(x) + 6, int(x + bw) - 6, step - 2):
                    if rng.random() < wp:
                        c = [(255, 206, 120), (120, 220, 255), (255, 120, 190)][rng.integers(0, 3)] if rng.random() < 0.25 else (255, 214, 140)
                        dr.rectangle([wx, wy, wx + 4, wy + 6], fill=c)
            if rng.random() < 0.5:
                dr.line([(x + bw / 2, top), (x + bw / 2, top - rng.uniform(20, 70))], fill=body, width=3)
            x += bw + rng.uniform(-6, 10)
        out_depth[np.asarray(dmask) > 0] = dep
    rgb = np.asarray(img, np.float32)
    # neon strips (abstract light bars, no text)
    for (x0, y0, x1, y1, col, dep) in [(780, 330, 790, 640, (255, 60, 170), 0.6), (840, 470, 1010, 480, (60, 230, 255), 0.6), (1120, 380, 1128, 700, (120, 255, 190), 0.58), (200, 410, 340, 418, (255, 190, 60), 0.6)]:
        rgb[y0:y1, x0:x1] = col
        _glow(rgb, (x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, y1 - y0) * 0.9, col, 0.55)
        out_depth[y0:y1, x0:x1] = dep
    # near rooftop with tank
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(img)
    dmask = Image.new("L", (W, H), 0)
    dm = ImageDraw.Draw(dmask)
    roof = [(0, 800), (W, 770), (W, H), (0, H)]
    dr.polygon(roof, fill=(10, 8, 22)); dm.polygon(roof, fill=255)
    dr.rectangle([1150, 610, 1290, 790], fill=(16, 12, 30)); dm.rectangle([1150, 610, 1290, 790], fill=255)
    dr.polygon([(1140, 612), (1220, 560), (1300, 612)], fill=(20, 16, 36)); dm.polygon([(1140, 612), (1220, 560), (1300, 612)], fill=255)
    for lx in (1160, 1200, 1240, 1280):
        dr.line([(lx, 700), (lx - 12, 800)], fill=(10, 8, 20), width=5)
    dr.line([(150, 800), (150, 520)], fill=(14, 10, 26), width=6); dm.line([(150, 800), (150, 520)], fill=255, width=6)
    dr.line([(110, 560), (190, 560)], fill=(14, 10, 26), width=4)
    dr.line([(120, 600), (180, 600)], fill=(14, 10, 26), width=4)
    dr.ellipse([144, 508, 156, 520], fill=(255, 70, 90))
    rgb = np.asarray(img, np.float32)
    _glow(rgb, 150, 514, 40, (255, 60, 80), 0.8)
    mk = np.asarray(dmask) > 0
    out_depth[mk] = 0.16
    out_depth[1150:1300, 560:800][:0]  # no-op, keeps indices obvious
    tank = np.zeros((H, W), bool); tank[560:800, 1140:1300] = True
    out_depth[tank] = 0.3
    return Art("neon-rooftops", "Neon Rooftops", _finish(rgb, rng, 3.5), _smooth(out_depth, 1.2), (0.55, 0.52), "Night skyline with glowing windows and abstract neon bars.")


def desert_monolith(seed: int = 5) -> Art:
    rng = np.random.default_rng(seed)
    rgb = _gradient([(0, (40, 110, 140)), (0.4, (122, 180, 176)), (0.62, (246, 214, 160)), (1, (246, 214, 160))])
    depth = np.ones((H, W), np.float32)
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    _glow(rgb, 460, 470, 420, (255, 214, 140), 0.6)
    rgb[(xs - 460) ** 2 + (ys - 470) ** 2 < 120**2] = (255, 240, 205)
    haze = np.array([248, 214, 168], np.float32)
    layers = [(520, 24, (214, 150, 118), 0.95, 0.65), (580, 38, (200, 128, 104), 0.82, 0.45), (650, 46, (182, 108, 90), 0.66, 0.28), (730, 52, (150, 86, 78), 0.45, 0.1), (830, 40, (108, 62, 62), 0.22, 0.0)]
    for base, amp, col, d, hz in layers:
        x = np.linspace(0, 1, W)
        curve = base + amp * (np.sin(2 * math.pi * (0.9 + rng.uniform(0, 0.8)) * x + rng.uniform(0, 6)) + 0.5 * np.sin(2 * math.pi * (2.3 + rng.uniform(0, 1.5)) * x + rng.uniform(0, 6)) + 0.25 * np.sin(2 * math.pi * 5.1 * x + rng.uniform(0, 6)))
        # lit / shaded sides: gradient across x slope
        _fill_below(rgb, depth, curve, col, d, gradient_to=np.asarray(col) * 0.62, haze=haze, haze_amt=hz * 0.7)
        slope = np.gradient(curve)
        shade = np.clip(slope * 1.2, -1, 1)
        mask = ys >= curve[None, :]
        band = mask & (ys < curve[None, :] + 38 + amp * 0.6)
        rgb[band] *= (1 - 0.18 * np.clip(shade, 0, 1))[None, :].repeat(H, 0)[band][:, None]
    # monolith
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(img)
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    x0, x1, y0, y1 = 930, 1040, 330, 730
    face = [(x0, y1), (x0 + 6, y0 + 18), (x0 + 28, y0), (x1 - 8, y0 + 10), (x1, y1)]
    dr.polygon(face, fill=(28, 24, 34)); md.polygon(face, fill=255)
    side = [(x1 - 8, y0 + 10), (x1 + 34, y0 + 30), (x1 + 40, y1 - 14), (x1, y1)]
    dr.polygon(side, fill=(14, 12, 20)); md.polygon(side, fill=255)
    dr.line([(x0 + 28, y0), (x0 + 30, y1 - 4)], fill=(96, 84, 110), width=2)
    rgb = np.asarray(img, np.float32)
    # long shadow
    sh = np.zeros((H, W), bool)
    for yy in range(y1 - 6, y1 + 18):
        xa = int(x0 - (yy - y1) * 0 - 330 + (yy - (y1 - 6)) * 2)
        sh[yy, max(xa, 0) : x1] = True
    rgb[sh] *= 0.55
    mk = np.asarray(mask) > 0
    depth[mk] = 0.52
    # foreground rocks
    for rx, ry, rw, rh in [(120, 860, 150, 70), (1360, 880, 220, 90), (640, 900, 120, 50)]:
        im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
        d2 = ImageDraw.Draw(im)
        pts = [(rx - rw, ry + rh)] + [(rx - rw + rw * 2 * (i / 6), ry - rng.uniform(0.3, 1) * rh * math.sin(math.pi * i / 6)) for i in range(1, 6)] + [(rx + rw, ry + rh)]
        d2.polygon(pts, fill=(60, 36, 44))
        d2.line(pts[1:-1], fill=(140, 90, 80), width=3)
        rgb = np.asarray(im, np.float32)
        rm = np.zeros((H, W), bool); rm[int(ry - rh) : H, max(int(rx - rw), 0) : min(int(rx + rw), W)] = True
        rm &= (np.asarray(im).sum(-1) < 200)
        depth[rm] = 0.08
    return Art("desert-monolith", "Desert Monolith", _finish(rgb, rng, 3.0), _smooth(depth, 1.2), (0.62, 0.6), "A lone standing slab among dunes: strong silhouette for orbit and dolly moves.")


def glass_orbs(seed: int = 3) -> Art:
    rng = np.random.default_rng(seed)
    bg = _gradient([(0, (18, 40, 52)), (0.55, (30, 70, 80)), (0.56, (46, 30, 50)), (1, (18, 12, 28))])
    rgb = bg.copy()
    depth = np.ones((H, W), np.float32)
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    # bokeh backdrop
    for _ in range(46):
        cx, cy, r = rng.uniform(0, W), rng.uniform(40, 480), rng.uniform(18, 70)
        col = [(255, 190, 110), (110, 220, 220), (255, 120, 160)][rng.integers(0, 3)]
        m = (xs - cx) ** 2 + (ys - cy) ** 2 < r * r
        rgb[m] = _lerp(rgb[m], col, 0.16)
    # table plane
    table = ys >= 500
    t = (ys - 500) / (H - 500)
    rgb[table] = _lerp((58, 34, 62), (20, 12, 30), t[table][:, None])
    _glow(rgb, 800, 760, 700, (120, 80, 130), 0.25)
    depth[table] = np.clip(0.55 - 0.5 * t[table], 0.04, 1)
    depth[~table] = 0.97
    objs = [(800, 590, 150, (255, 150, 90), 0.0), (470, 640, 96, (90, 210, 230), 0.4), (1130, 650, 110, (240, 90, 160), 0.2), (1330, 560, 58, (210, 230, 120), 0.5)]
    light = np.array([-0.5, -0.6, 0.62], np.float32); light /= np.linalg.norm(light)
    for cx, cy, r, col, ior in objs:
        dx, dy = (xs - cx) / r, (ys - cy) / r
        rr = dx * dx + dy * dy
        m = rr < 1
        nz = np.sqrt(np.clip(1 - rr, 0, 1))
        n = np.stack([dx, dy, nz], -1)
        diff = np.clip((n @ light), 0, 1)[..., None]
        base = np.asarray(col, np.float32)
        fres = (1 - nz) ** 2.2
        reflv = _lerp((30, 60, 76), (255, 210, 160), np.clip(0.5 - dy * 0.5, 0, 1))[..., None] if False else None
        refl = np.stack([np.interp(np.clip(0.5 - n[..., 1] * 0.5, 0, 1), [0, 1], [bg[0, 0, c] * 0.8, 220 - c * 10]) for c in range(3)], -1)
        shade = base * (0.25 + 0.75 * diff) * 0.85 + refl * (0.25 + 0.5 * fres[..., None])
        spec = np.clip((n @ ((light + np.array([0, 0, 1.0], np.float32)) / np.linalg.norm(light + np.array([0, 0, 1.0], np.float32)))), 0, 1) ** 70
        shade += spec[..., None] * 255
        shade += (fres[..., None]) * 70
        rgb[m] = shade[m]
        t_c = 0.55 - 0.5 * ((cy + r - 500) / 400.0)  # table depth at the contact point
        depth[m] = np.clip(t_c - 0.05 * nz[m] * (r / 100.0), 0.03, 1)
        # contact shadow
        sh = ((xs - (cx + r * 0.25)) / (r * 1.25)) ** 2 + ((ys - (cy + r * 0.98)) / (r * 0.22)) ** 2 < 1
        sh &= ~m
        rgb[sh] *= 0.45
    return Art("glass-orbs", "Glass Orbs", _finish(rgb, rng, 2.6, 0.34), _smooth(depth, 1.2), (0.5, 0.65), "Glossy spheres on a table: clean 3D-ish forms for orbit and coverage.")


ALL = {"alpine-dusk": alpine_dusk, "neon-rooftops": neon_rooftops, "desert-monolith": desert_monolith, "glass-orbs": glass_orbs}
