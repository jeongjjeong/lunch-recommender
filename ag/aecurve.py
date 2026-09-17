"""Cubic-bezier easing, After-Effects style.

Every eased curve in this project (per spec: "이징이 필요한 모든 곳은
influence 0.95 / speed 0 의 큐빅 베지어로 푼다") goes through
`cubic_bezier_ease`, never `smoothstep`.

"speed 0" at a keyframe means the tangent is flat there, so the
bezier's y-control coincides with the endpoint's y. "influence 0.95"
means the handle reaches 95% of the way toward the neighbouring
keyframe along the time axis. That gives control points
P1=(0.95, 0), P2=(0.05, 1) on the unit square -- a curve that sits
almost flat near both ends and snaps through the middle, which is
exactly the "hold, then rush" shape spec section 7 calls for.
"""
from __future__ import annotations

import numpy as np


def _bezier_xy(t: np.ndarray, x1: float, y1: float, x2: float, y2: float):
    mt = 1.0 - t
    # cubic bezier with P0=(0,0), P3=(1,1)
    x = 3 * mt * mt * t * x1 + 3 * mt * t * t * x2 + t ** 3
    y = 3 * mt * mt * t * y1 + 3 * mt * t * t * y2 + t ** 3
    return x, y


def cubic_bezier_ease(x1: float, y1: float, x2: float, y2: float, samples: int = 4096):
    """Returns f(u) -> eased value, u in [0, 1], via bisection on x(t)=u."""
    t = np.linspace(0.0, 1.0, samples)
    xs, ys = _bezier_xy(t, x1, y1, x2, y2)
    # xs is monotonic increasing for handles clamped to [0, 1] (CSS
    # cubic-bezier() convention); np.interp performs the bisection.
    def f(u):
        u = np.clip(np.asarray(u, dtype=np.float64), 0.0, 1.0)
        return np.interp(u, xs, ys)

    return f


# influence 0.95 / speed 0, both ends -- the one easing curve this
# project uses everywhere a segment needs to be eased.
EASE95 = cubic_bezier_ease(0.95, 0.0, 0.05, 1.0)


# Section 7 reveal curve: fraction of a headline revealed as a function
# of normalized progress u = elapsed_seconds / REVEAL_DURATION.
REVEAL_DURATION = 1.667  # seconds, spec 7
_REVEAL_U = np.array(
    [0.00, 0.28, 0.32, 0.37, 0.43, 0.49, 0.52, 0.55, 0.61, 0.67, 0.73, 0.79, 1.20]
)
_REVEAL_R = np.array(
    [0.00, 0.00, 0.10, 0.22, 0.26, 0.36, 0.62, 0.82, 0.89, 0.96, 0.99, 1.00, 1.00]
)


def reveal_fraction(u):
    """u: elapsed-seconds/REVEAL_DURATION (scalar or array). Returns 0..1."""
    u = np.clip(np.asarray(u, dtype=np.float64), 0.0, _REVEAL_U[-1])
    idx = np.clip(np.searchsorted(_REVEAL_U, u, side="right") - 1, 0, len(_REVEAL_U) - 2)
    u0, u1 = _REVEAL_U[idx], _REVEAL_U[idx + 1]
    r0, r1 = _REVEAL_R[idx], _REVEAL_R[idx + 1]
    span = np.where(u1 > u0, u1 - u0, 1.0)
    s = np.clip((u - u0) / span, 0.0, 1.0)
    eased = EASE95(s)
    return r0 + (r1 - r0) * eased


def reveal_fraction_at(elapsed_seconds):
    return float(reveal_fraction(np.array(elapsed_seconds) / REVEAL_DURATION))
