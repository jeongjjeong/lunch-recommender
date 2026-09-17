"""Scene geometry and timing table (spec section 2)."""
from __future__ import annotations

from dataclasses import dataclass

FPS = 30
FRAME_COUNT = 652
SCENE_LEN = 125  # frames

# Section 2 outfade multipliers -- applied one per frame starting at
# local frame 126, 26 frames long. The 13th value's 0.70->0.30 cliff is
# intentional and must not be smoothed.
OUTFADE_MULTIPLIERS = [
    1.0, .998, .9968, .9945, .9893, .9856, .9721, .9589, .9408, .9157, .8731,
    .8194, .7022, .2977, .1803, .1239, .0901, .0429, .0201, .0130, .0086,
    .0082, .0062, .0050, .0041, .0034,
]
OUTFADE_START_FRAME = 126  # local frame, 0-indexed within the scene


@dataclass(frozen=True)
class Scene:
    id: str
    start_frame: int
    headline_lines: int
    caption_count: int
    light_center: tuple
    has_headline: bool
    time_offset: float  # seconds added to this scene's local source time
    has_outfade: bool
    ramp_name: str
    diagonal_rays: bool = False  # S3: sagittal/diagonal ray bias
    from_top: bool = False       # S1: pours in from above frame
    from_bottom: bool = False    # S4: fans in from below frame
    star_marks: bool = False     # S5: 8-point star marks take the lead


SCENES = [
    Scene("S1", 0, 2, 3, (960, 0), True, 0.0, True, "S1", from_top=True),
    Scene("S2", 125, 1, 5, (960, 540), True, 1.0 / 3.0, True, "S2"),
    Scene("S3", 250, 2, 4, (230, 390), True, 0.0, True, "S3", diagonal_rays=True),
    Scene("S4", 375, 1, 5, (960, 980), True, 0.0, True, "S4", from_bottom=True),
    Scene("S5", 500, 0, 3, (960, 475), False, 0.0, False, "S5", star_marks=True),
]


def scene_for_frame(f: int) -> Scene:
    idx = min(f // SCENE_LEN, len(SCENES) - 1)
    return SCENES[idx]


def local_frame(f: int, scene: Scene) -> int:
    return f - scene.start_frame


def outfade_multiplier(local_f: int) -> float:
    """30fps-native opacity multiplier -- never quantized to the 20fps
    source stair-step (spec section 6: "아웃페이드만은 계단을 타지
    않는다")."""
    i = local_f - OUTFADE_START_FRAME
    if i < 0:
        return 1.0
    if i >= len(OUTFADE_MULTIPLIERS):
        return OUTFADE_MULTIPLIERS[-1]
    # Cumulative product: each listed value is a per-frame multiplier
    # applied on top of the running opacity, per spec 2 ("매 프레임
    # 곱한다").
    return OUTFADE_MULTIPLIERS[i]


def cumulative_outfade(local_f: int, has_outfade: bool) -> float:
    if not has_outfade:
        return 1.0
    i = local_f - OUTFADE_START_FRAME
    if i < 0:
        return 1.0
    i = min(i, len(OUTFADE_MULTIPLIERS) - 1)
    acc = 1.0
    for m in OUTFADE_MULTIPLIERS[: i + 1]:
        acc *= m
    return acc


def source_time_seconds(f: int, scene: Scene) -> float:
    """20fps-quantized source time, spec section 6:
    k = max(0, (2*(f+1))//3 - 2); t = k/20. Then the scene's own
    +time_offset is applied to the *source* clock, not to a single
    element -- S2's whole timeline is late by 1/3s.
    """
    lf = local_frame(f, scene)
    k = max(0, (2 * (lf + 1)) // 3 - 2)
    t = k / 20.0
    return t + scene.time_offset
