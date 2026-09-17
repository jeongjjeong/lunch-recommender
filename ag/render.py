"""Per-frame compositing: scene layout, color ramp, and the section-6
time texture (20fps stair-step, 110% vertical-only stretch, gate weave,
print texture, grain).
"""
from __future__ import annotations

import json
from functools import lru_cache

import cv2
import numpy as np

from . import aecurve, fx, paths, scenes, typo

W, H = 1920, 1080
BG_COLOR = np.array([4, 3, 3], dtype=np.float32)  # near-black, not pure 0

# ------------------------------------------------------------ color ramp

def _hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


@lru_cache(maxsize=None)
def _ramps():
    with open(paths.DATA_DIR / "ramps.json") as fp:
        return json.load(fp)


@lru_cache(maxsize=None)
def build_lut(scene_id: str, n: int = 512) -> np.ndarray:
    """512-entry LUT, 5-stop ramp, built once. Brightness -> color is a
    strictly one-directional lookup (spec 5): never averaged or
    re-derived from "brightness range", which is exactly the mistake
    that bleeds the ramp's non-monotonic blue peak into the red band.
    """
    stops_hex = _ramps()[scene_id]
    stops = np.array([_hex_to_rgb(h) for h in stops_hex], dtype=np.float32)  # (5,3) RGB
    xs = np.linspace(0.0, 1.0, len(stops))
    idx = np.linspace(0.0, 1.0, n)
    lut = np.stack(
        [np.interp(idx, xs, stops[:, c]) for c in range(3)], axis=1
    )  # (n, 3) RGB, 0..255
    return lut.astype(np.float32)


def apply_lut(I: np.ndarray, lut: np.ndarray) -> np.ndarray:
    idx = np.clip((I * (lut.shape[0] - 1)).astype(np.int32), 0, lut.shape[0] - 1)
    return lut[idx]  # (H, W, 3) RGB float


# ------------------------------------------------------------ layout helpers

def _caption_positions(scene: scenes.Scene, n: int, seed: int):
    rng = np.random.default_rng(seed)
    cx, cy = scene.light_center
    pts = []
    base = rng.uniform(0, 2 * np.pi)
    for i in range(n):
        ang = base + (2 * np.pi * i / n) + rng.uniform(-0.25, 0.25)
        rad = rng.uniform(340, 560)
        x = np.clip(cx + rad * np.cos(ang), 60, W - 300)
        y = np.clip(cy + rad * np.sin(ang) * 0.55, 60, H - 80)
        pts.append((x, y))
    return pts


def _mark_positions(scene: scenes.Scene, n: int, seed: int):
    rng = np.random.default_rng(seed + 777)
    cx, cy = scene.light_center
    pts = []
    base = rng.uniform(0, 2 * np.pi)
    for i in range(n):
        ang = base + (2 * np.pi * i / n) + rng.uniform(-0.3, 0.3)
        rad = rng.uniform(220, 660)
        kind = rng.choice(["cross", "star"])
        x = np.clip(cx + rad * np.cos(ang), 20, W - 20)
        y = np.clip(cy + rad * np.sin(ang) * 0.55, 20, H - 20)
        pts.append((x, y, kind))
    return pts


def _draw_star8_mask(mask, x, y, size):
    pts = []
    for i in range(16):
        ang = i * np.pi / 8
        r = size if i % 2 == 0 else size * 0.42
        pts.append((x + r * np.cos(ang), y + r * np.sin(ang)))
    pts = np.array(pts, dtype=np.int32).reshape(-1, 1, 2)
    cv2.fillPoly(mask, [pts], 1.0, cv2.LINE_AA)


def _draw_cross(canvas, x, y, size, color, alpha):
    x, y = int(x), int(y)
    overlay = canvas.copy()
    cv2.line(overlay, (x - size, y), (x + size, y), color, 2, cv2.LINE_AA)
    cv2.line(overlay, (x, y - size), (x, y + size), color, 2, cv2.LINE_AA)
    canvas[:] = canvas * (1 - alpha) + overlay * alpha


def _draw_star8(canvas, x, y, size, color, alpha):
    x, y = float(x), float(y)
    pts = []
    for i in range(16):
        ang = i * np.pi / 8
        r = size if i % 2 == 0 else size * 0.4
        pts.append((x + r * np.cos(ang), y + r * np.sin(ang)))
    pts = np.array(pts, dtype=np.int32).reshape(-1, 1, 2)
    overlay = canvas.copy()
    cv2.fillPoly(overlay, [pts], color, cv2.LINE_AA)
    canvas[:] = canvas * (1 - alpha) + overlay * alpha


# ------------------------------------------------------------ noise textures

_rng_master = np.random.default_rng(20260917)
_GATE_WEAVE = None


def _gate_weave_path(n_frames: int, step: float = 0.08, max_amp: float = 0.8):
    global _GATE_WEAVE
    if _GATE_WEAVE is not None and len(_GATE_WEAVE) == n_frames:
        return _GATE_WEAVE
    rng = np.random.default_rng(7)
    pos = np.zeros((n_frames, 2), dtype=np.float64)
    cur = np.zeros(2)
    for i in range(n_frames):
        cur = cur + rng.normal(0, step, size=2)
        cur = np.clip(cur, -max_amp, max_amp)
        pos[i] = cur
    _GATE_WEAVE = pos
    return pos


@lru_cache(maxsize=1)
def _print_texture(w, h):
    rng = np.random.default_rng(4242)
    speck_src = rng.random((h, w), dtype=np.float64).astype(np.float32)
    speck = cv2.GaussianBlur(speck_src, (0, 0), sigmaX=0.55)
    low_src = rng.random((h // 8 + 1, w // 8 + 1), dtype=np.float64).astype(np.float32)
    low = cv2.resize(low_src, (w, h), interpolation=cv2.INTER_CUBIC)
    speck = (speck - speck.mean()) / (speck.std() + 1e-6)
    low = (low - low.mean()) / (low.std() + 1e-6)
    tex = 0.88 * speck + 0.12 * low
    tex = tex / (np.abs(tex).max() + 1e-6)
    return tex.astype(np.float32)  # roughly -1..1


# ------------------------------------------------------------ scene content

@lru_cache(maxsize=1)
def _content():
    with open(paths.CONTENT_JSON) as fp:
        return json.load(fp)


def _scene_content(scene_id):
    for s in _content()["scenes"]:
        if s["id"] == scene_id:
            return s
    raise KeyError(scene_id)


HEADLINE_TARGET_W = 1650
HEADLINE_LINE_H = 200
HEADLINE_GAP = 26
CAPTION_TARGET_H = 26


def _fit_headline(scene: scenes.Scene, content):
    lines = []
    for text in content["headline"]:
        lines.append(typo.fit_line(str(paths.HEADLINE_FONT), text, HEADLINE_TARGET_W, HEADLINE_LINE_H))
    return lines


# ------------------------------------------------------------ main per-frame render

def render_frame(f: int, n_frames: int = scenes.FRAME_COUNT) -> np.ndarray:
    scene = scenes.scene_for_frame(f)
    lf = scenes.local_frame(f, scene)
    content = _scene_content(scene.id)

    t_src = scenes.source_time_seconds(f, scene)  # 20fps-quantized, scene-shifted
    outfade = scenes.cumulative_outfade(lf, scene.has_outfade)  # 30fps-native, never quantized

    lut = build_lut(scene.ramp_name)
    white = lut[-1]

    canvas = np.tile(BG_COLOR, (H, W, 1)).copy()

    # ---- headline: build letter alpha mask at full canvas res
    letter_mask = np.zeros((H, W), dtype=np.float32)
    lines = _fit_headline(scene, content) if scene.has_headline else []
    n_lines = len(lines)
    block_h = n_lines * HEADLINE_LINE_H + max(0, n_lines - 1) * HEADLINE_GAP
    top = scene.light_center[1] - block_h / 2.0
    if scene.id == "S1":
        top = 300
    elif scene.id == "S3":
        top = 520
    elif scene.id == "S4":
        top = 700

    entry_settle = aecurve.EASE95(np.clip(t_src / 0.6, 0, 1))
    vertical_launch = 0.0
    if scene.from_top:
        vertical_launch = (1.0 - entry_settle) * -420.0
    elif scene.from_bottom:
        vertical_launch = (1.0 - entry_settle) * 420.0

    for i, line in enumerate(lines):
        if not line.text:
            continue
        mask, _ = typo.render_line_mask(line)
        mh, mw = mask.shape
        ltr = (i % 2 == 0)
        elapsed = max(0.0, t_src)
        prog = aecurve.reveal_fraction(elapsed / aecurve.REVEAL_DURATION)
        col_alpha = typo.glyph_reveal_alpha(line, mw, prog, ltr)
        mask = mask * col_alpha[None, :]

        x0 = int(scene.light_center[0] - mw / 2.0)
        y0 = int(top + i * (HEADLINE_LINE_H + HEADLINE_GAP) - 4 + vertical_launch)
        x1, y1 = x0 + mw, y0 + mh
        cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        if cx1 <= cx0 or cy1 <= cy0:
            continue
        mx0, my0 = cx0 - x0, cy0 - y0
        letter_mask[cy0:cy1, cx0:cx1] = np.maximum(
            letter_mask[cy0:cy1, cx0:cx1], mask[my0 : my0 + (cy1 - cy0), mx0 : mx0 + (cx1 - cx0)]
        )

    ignite_progress = float(np.clip((t_src - 0.35) / 0.9, 0.0, 1.0))
    have_letters = letter_mask.max() > 0

    if have_letters:
        flick, noise = fx.flicker_mask(letter_mask, t_src, ignite_progress)
        I = fx.light_field(letter_mask, flick, scene.light_center, W, H)
        rgb = apply_lut(I, lut)
        sdf = fx.signed_distance(letter_mask)
        band_noise = fx.evolving_noise(letter_mask.shape, t_src)
        rgb = fx.edge_trough(rgb, sdf, band_noise)
        core = flick
        rgb = rgb * (1 - core[..., None]) + white[None, None, :] * core[..., None]
    elif scene.star_marks:
        # S5: no headline -- an 8-point star at the light center is the
        # scene's whole subject, so it seeds the light field itself.
        seed_mask = np.zeros((H, W), dtype=np.float32)
        cx, cy = scene.light_center
        _draw_star8_mask(seed_mask, cx, cy, 46)
        cv2.circle(seed_mask, (int(cx), int(cy)), 14, 1.0, -1, cv2.LINE_AA)
        flick, noise = fx.flicker_mask(seed_mask, t_src, 1.0, amp=1.4)
        I = fx.light_field(seed_mask, flick, scene.light_center, W, H)
        rgb = apply_lut(I, lut)
        core = flick
        rgb = rgb * (1 - core[..., None]) + white[None, None, :] * core[..., None]
    else:
        rgb = np.tile(BG_COLOR, (H, W, 1)).copy()

    lit_layer = np.clip(rgb, 0, 255)

    # ---- 110% vertical-ONLY stretch, applied to lit content only (spec 6)
    stretched_h = int(round(H * 1.1))
    stretched = cv2.resize(lit_layer, (W, stretched_h), interpolation=cv2.INTER_LINEAR)
    y_off = (stretched_h - H) // 2
    lit_layer = stretched[y_off : y_off + H, :, :]

    canvas = np.where(
        (lit_layer.sum(axis=2, keepdims=True) > BG_COLOR.sum() + 1.0), lit_layer, canvas
    )

    # ---- captions + marks: NOT affected by the vertical stretch
    mid_color = lut[int(lut.shape[0] * 0.55)]
    cap_in = float(np.clip(lf / 20.0, 0, 1))
    for text, (x, y) in zip(content["captions"], _caption_positions(scene, scene.caption_count, hash(scene.id) & 0xFFFF)):
        cline = typo.fit_line(str(paths.CAPTION_FONT), text, 190, CAPTION_TARGET_H)
        if not cline.text:
            continue
        cmask, _ = typo.render_line_mask(cline)
        mh, mw = cmask.shape
        x0, y0 = int(x), int(y)
        cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(W, x0 + mw), min(H, y0 + mh)
        if cx1 <= cx0 or cy1 <= cy0:
            continue
        mx0, my0 = cx0 - x0, cy0 - y0
        sub = cmask[my0 : my0 + (cy1 - cy0), mx0 : mx0 + (cx1 - cx0)][..., None]
        canvas[cy0:cy1, cx0:cx1] = canvas[cy0:cy1, cx0:cx1] * (1 - sub * cap_in) + mid_color[None, None, :] * sub * cap_in

    for x, y, kind in _mark_positions(scene, 6, hash(scene.id) & 0xFFFF):
        if kind == "cross":
            _draw_cross(canvas, x, y, 9, tuple(float(c) for c in mid_color), cap_in)
        else:
            _draw_star8(canvas, x, y, 7, tuple(float(c) for c in mid_color), cap_in)

    # ---- outfade (30fps-native opacity, applied post-composite)
    canvas = canvas * outfade + BG_COLOR[None, None, :] * (1 - outfade)

    # ---- gate weave: whole-frame subpixel random walk
    weave = _gate_weave_path(n_frames)[f]
    M = np.array([[1, 0, weave[0]], [0, 1, weave[1]]], dtype=np.float32)
    canvas = cv2.warpAffine(canvas, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

    # ---- print texture: multiplicative, bias slightly below 1
    tex = _print_texture(W, H)
    mult = 1.0 - 0.024 + tex * 0.05
    canvas = canvas * mult[..., None]

    # ---- grain
    grain = (np.random.default_rng(9000 + f).random((H, W, 1), dtype=np.float64).astype(np.float32) - 0.5) * 2 * 0.006 * 255
    canvas = canvas + grain

    canvas = np.clip(canvas, 0, 255).astype(np.uint8)
    return cv2.cvtColor(canvas, cv2.COLOR_RGB2BGR)
