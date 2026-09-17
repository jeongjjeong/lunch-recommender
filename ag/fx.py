"""Pixel effects: the four-layer light field (section 3) and the
dynamic edge flicker (section 4).

Everything here operates on a single-channel alpha mask of "painted
letter" at canvas resolution and returns single-channel float32 arrays
in [0, 1]. Colorizing happens in ag/render.py via the LUT ramp.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

# ---------------------------------------------------------------- polar cache

NTHETA = 3072
NR = 1100

_polar_cache: dict = {}
R_MIN = 1.0


def _build_polar_maps(center, max_radius, shape):
    w, h = shape
    cx, cy = center

    # forward map: polar (theta rows x logr cols) -> cartesian source coords
    theta = (np.arange(NTHETA, dtype=np.float64) / NTHETA) * 2 * np.pi
    logr = np.linspace(np.log(R_MIN), np.log(max_radius), NR)
    r = np.exp(logr)
    th_grid, r_grid = np.meshgrid(theta, r, indexing="ij")  # (NTHETA, NR)
    fwd_x = (cx + r_grid * np.cos(th_grid)).astype(np.float32)
    fwd_y = (cy + r_grid * np.sin(th_grid)).astype(np.float32)

    # inverse map: cartesian (y rows x x cols) -> polar coords (theta, logr)
    xs = np.arange(w, dtype=np.float64) - cx
    ys = np.arange(h, dtype=np.float64) - cy
    xg, yg = np.meshgrid(xs, ys)  # (h, w)
    rr = np.sqrt(xg * xg + yg * yg)
    tt = np.mod(np.arctan2(yg, xg), 2 * np.pi)
    rr = np.clip(rr, R_MIN, max_radius)
    inv_x = ((np.log(rr) - np.log(R_MIN)) / (np.log(max_radius) - np.log(R_MIN)) * (NR - 1)).astype(np.float32)
    inv_y = (tt / (2 * np.pi) * NTHETA).astype(np.float32)

    return fwd_x, fwd_y, inv_x, inv_y


def _polar_maps(center, max_radius, shape):
    """Log-polar remap LUTs, built once per light center and cached
    (spec 3.1: "맵은 중심마다 한 번만 만들어 캐시한다") -- every
    subsequent frame just calls cv2.remap against the cached LUT
    instead of re-deriving the angle/radius grid."""
    key = (tuple(center), round(max_radius, 3), shape)
    if key not in _polar_cache:
        _polar_cache[key] = _build_polar_maps(center, max_radius, shape)
    return _polar_cache[key]


def to_polar(src: np.ndarray, center, max_radius: float) -> np.ndarray:
    fwd_x, fwd_y, _, _ = _polar_maps(center, max_radius, (src.shape[1], src.shape[0]))
    return cv2.remap(src, fwd_x, fwd_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def from_polar(q: np.ndarray, center, max_radius: float, shape) -> np.ndarray:
    _, _, inv_x, inv_y = _polar_maps(center, max_radius, shape)
    return cv2.remap(q, inv_x, inv_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def frame_max_radius(center, w, h):
    corners = [(0, 0), (w, 0), (0, h), (w, h)]
    cx, cy = center
    return max(((cx - x) ** 2 + (cy - y) ** 2) ** 0.5 for x, y in corners) + 1.0


# ------------------------------------------------------------ ray-decay filter

def ray_decay_filter(src: np.ndarray, center, w, h, decay: float) -> np.ndarray:
    """Long light-shaft layer: one-sided exponential filter along the
    log-radius axis, solved by doubling recursion (spec 3.1) instead of
    an O(NR) loop or a 26-step zoom-blur -- O(log NR) per row and no
    zoom-step banding.
    """
    max_r = frame_max_radius(center, w, h)
    q = to_polar(src, center, max_r).astype(np.float32)

    dlr = np.log(max_r) / NR
    A = float(np.exp(-dlr / decay))

    step = 1
    f = A
    while step < NR:
        q[:, step:] += f * q[:, :-step]
        f *= f
        step *= 2
    q *= (1.0 - A)

    return from_polar(q, center, max_r, (w, h))


def radial_smear(src: np.ndarray, center, w, h, window_bins: int) -> np.ndarray:
    """Short "smear" layer: a box average in the same log-polar plane,
    but one-directional (outward only). A symmetric kernel would pull
    brightness back toward the center and wash out the dark gaps
    between letters -- spec 3.1 explicitly forbids that.
    """
    max_r = frame_max_radius(center, w, h)
    q = to_polar(src, center, max_r).astype(np.float32)

    cs = np.cumsum(q, axis=1, dtype=np.float64)
    cs = np.concatenate([np.zeros((q.shape[0], 1)), cs], axis=1)
    idx = np.arange(q.shape[1])
    lo = np.clip(idx - window_bins + 1, 0, None)
    counts = (idx - lo + 1).astype(np.float64)
    box = (cs[:, idx + 1] - cs[:, lo]) / counts
    q = box.astype(np.float32)

    return from_polar(q, center, max_r, (w, h))


# ------------------------------------------------------------ hole detection

@dataclass
class HoleGate:
    gate: np.ndarray  # 1.0 outside holes, attenuated curve inside holes


def hole_gate(letter_mask: np.ndarray, depth: float = 0.55, reach: float = 6.0) -> np.ndarray:
    """Connected-components the background (spec 3.2): components that
    never touch the frame border are "holes" enclosed by ink (the
    counter of an O, the inside of an A/e/g/...). Long-shaft light must
    not flood them at full strength, or the letterform reads as a
    solid blob -- it decays with distance from the hole's own boundary.
    """
    h, w = letter_mask.shape
    bg = (letter_mask < 0.5).astype(np.uint8)
    n, labels = cv2.connectedComponents(bg, connectivity=4)

    border_labels = set(labels[0, :].tolist()) | set(labels[-1, :].tolist())
    border_labels |= set(labels[:, 0].tolist()) | set(labels[:, -1].tolist())
    border_labels.discard(0)

    hole_mask = np.zeros((h, w), dtype=np.uint8)
    for lbl in range(1, n):
        if lbl not in border_labels:
            hole_mask[labels == lbl] = 1

    if not hole_mask.any():
        return np.ones((h, w), dtype=np.float32)

    # distance FROM the hole's own boundary, measured going inward
    dist = cv2.distanceTransform(hole_mask, cv2.DIST_L2, 5)
    atten = 1.0 - depth * (1.0 - np.exp(-dist / reach))
    gate = np.where(hole_mask > 0, atten, 1.0).astype(np.float32)
    return gate


# ------------------------------------------------------------ near-field glow

def near_field_glow(letter_mask: np.ndarray) -> np.ndarray:
    """Isotropic, direction-agnostic glow (spec 3.2): a pixel just
    inside a hole and a pixel just outside an open edge end up equally
    bright, because a symmetric gaussian doesn't know or care which
    side of a stroke it's on -- unlike the ray/smear layers above.
    """
    g1 = cv2.GaussianBlur(letter_mask, (0, 0), sigmaX=12)
    g2 = cv2.GaussianBlur(letter_mask, (0, 0), sigmaX=70)
    return np.clip(g1 + 0.5 * g2, 0.0, 1.0)


# ------------------------------------------------------------ evolving noise

_noise_epoch_cache: dict = {}
EPOCH_SECONDS = 0.55


def _fractal_field(shape, seed: int, octaves=4, base_cells=6) -> np.ndarray:
    h, w = shape
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    total = 0.0
    cells = base_cells
    for _ in range(octaves):
        small = rng.random((max(2, cells), max(2, int(cells * w / h))), dtype=np.float64).astype(np.float32)
        big = cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)
        acc += amp * big
        total += amp
        amp *= 0.5
        cells *= 2
    acc /= total
    lo, hi = acc.min(), acc.max()
    return (acc - lo) / max(hi - lo, 1e-6)


def _noise_field(shape, epoch_idx: int) -> np.ndarray:
    key = (shape, epoch_idx)
    if key not in _noise_epoch_cache:
        _noise_epoch_cache[key] = _fractal_field(shape, seed=1000 + epoch_idx)
    return _noise_epoch_cache[key]


def evolving_noise(shape, t_seconds: float) -> np.ndarray:
    """Independent fractal fields every 0.55s, cross-faded with a
    variance-preserving blend (never linear -- linear interpolation
    kills contrast at the midpoint, per spec 4.3)."""
    pos = t_seconds / EPOCH_SECONDS
    epoch = int(np.floor(pos))
    u = pos - epoch
    A = _noise_field(shape, epoch)
    B = _noise_field(shape, epoch + 1)
    n = 0.5 + np.cos(u * np.pi / 2) * (A - 0.5) + np.sin(u * np.pi / 2) * (B - 0.5)
    return np.clip(n, 0.0, 1.0)


# ------------------------------------------------------------ SDF edge flicker

def signed_distance(mask: np.ndarray) -> np.ndarray:
    m = (mask > 0.5).astype(np.uint8)
    inside = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    outside = cv2.distanceTransform(1 - m, cv2.DIST_L2, 5)
    return inside - outside


def flicker_mask(clean_mask: np.ndarray, t_seconds: float, ignite_progress: float,
                  amp: float = 6.0, soft: float = 1.3) -> tuple:
    """Displaces the letters' SDF by an evolving noise field instead of
    multiplying alpha by noise (spec 4.2) -- strokes only sever where
    the displacement exceeds their own half-width, so counters stay
    open and the word stays legible.
    """
    sdf = signed_distance(clean_mask)
    noise = evolving_noise(clean_mask.shape, t_seconds)
    disp = amp * ignite_progress * (2.0 * noise - 1.0)
    out = np.clip((sdf - disp) / soft + 0.5, 0.0, 1.0)
    return out.astype(np.float32), noise


def edge_trough(brightness: np.ndarray, sdf: np.ndarray, noise: np.ndarray,
                 rim_w: float = 2.6, depth: float = 0.55, nmin: float = 0.15) -> np.ndarray:
    """The boundary is a dark groove, not a bright rim (spec 4.1/4.5):
    darkens a triangular band straddling the zero-crossing of the SDF,
    with the band's own depth breathing from the evolving noise field.
    """
    band = np.clip(1.0 - np.abs(sdf) / rim_w, 0.0, 1.0)
    darken = depth * (nmin + (1.0 - nmin) * np.clip(2.0 * noise, 0.0, 2.0))
    mult = 1.0 - band * darken
    if brightness.ndim == mult.ndim + 1:
        mult = mult[..., None]
    return brightness * mult


# ------------------------------------------------------------ layer weights

W_TOP = 0.85
W_STRK = 0.55
W_RAD = 0.9
W_FRAC = 1.0
W_NEAR = 1.0
RAY_DECAY = 0.115          # controls r^(-1/decay) long-shaft falloff
SMEAR_WINDOW_BINS = 42     # log-r bins for the outward-only box smear


def light_field(clean_mask: np.ndarray, flick: np.ndarray, center, w, h) -> np.ndarray:
    """I = max(w_top*top, w_strk*strk, w_rad*rad*ray, w_frac*frac*ray, w_near*near)
    -- section 3's four layers combined with max(), never summed, so a
    hole enclosed by ink can never be pushed brighter than the letter
    body around it by simple layer addition.
    """
    top = cv2.GaussianBlur(flick, (0, 0), sigmaX=4)
    strk = cv2.GaussianBlur(flick, (0, 0), sigmaX=16)
    near = near_field_glow(flick)

    gate = hole_gate(clean_mask)
    rad = radial_smear(clean_mask, center, w, h, SMEAR_WINDOW_BINS) * gate
    frac = ray_decay_filter(clean_mask, center, w, h, RAY_DECAY) * gate

    I = np.maximum.reduce([
        W_TOP * top,
        W_STRK * strk,
        W_RAD * rad,
        W_FRAC * frac,
        W_NEAR * near,
    ])
    return np.clip(I, 0.0, 1.0).astype(np.float32)
