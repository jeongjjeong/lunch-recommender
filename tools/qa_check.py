#!/usr/bin/env python3
"""Section 10 QA: numeric self-checks, not eye-balling.

1. Readability: connected components / hole count / largest-blob share
   on a settled frame (light on). A flooded hole shows up as component
   count collapsing and hole count cratering.
2. Distance-brightness profile at +-{8,4,2}/-{2,8,22,80,320}px from the
   boundary, split into hole / open-outside / letter-interior. Checks
   the 3.2 isotropy constraint directly instead of trusting "looks even".
3. Contour displacement: XOR area / perimeter between consecutive
   frames -- mean px the boundary moved along its normal.
4. Stroke ratio: upper-quantile distance-transform * 2 / letter height,
   measured on a PRE-ignition frame (light on turns whited-out blobs
   into "letters" that would fake this number).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np

from ag import paths, scenes, typo, fx  # noqa: E402
from ag.render import _fit_headline, _scene_content, W, H  # noqa: E402

paths.check_numpy_blas()


def letter_mask_at(scene, t_src):
    content = _scene_content(scene.id)
    lines = _fit_headline(scene, content)
    from ag import aecurve
    mask = np.zeros((H, W), dtype=np.float32)
    block_h = len(lines) * 200 + max(0, len(lines) - 1) * 26
    top = scene.light_center[1] - block_h / 2.0
    for i, line in enumerate(lines):
        if not line.text:
            continue
        m, _ = typo.render_line_mask(line)
        mh, mw = m.shape
        ltr = (i % 2 == 0)
        prog = aecurve.reveal_fraction(max(0.0, t_src) / aecurve.REVEAL_DURATION)
        col = typo.glyph_reveal_alpha(line, mw, prog, ltr)
        m = m * col[None, :]
        x0 = int(scene.light_center[0] - mw / 2.0)
        y0 = int(top + i * 226 - 4)
        cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(W, x0 + mw), min(H, y0 + mh)
        if cx1 <= cx0 or cy1 <= cy0:
            continue
        mx0, my0 = cx0 - x0, cy0 - y0
        mask[cy0:cy1, cx0:cx1] = np.maximum(mask[cy0:cy1, cx0:cx1], m[my0:my0 + (cy1 - cy0), mx0:mx0 + (cx1 - cx0)])
    return mask


def readability(mask):
    m = (mask > 0.5).astype(np.uint8)
    bg = 1 - m
    n_bg, labels = cv2.connectedComponents(bg, connectivity=4)
    border = set(labels[0, :]) | set(labels[-1, :]) | set(labels[:, 0]) | set(labels[:, -1])
    border.discard(0)
    holes = [l for l in range(1, n_bg) if l not in border]
    ink_labels_n, ink_labels = cv2.connectedComponents(m, connectivity=4)
    comp_areas = [int((ink_labels == l).sum()) for l in range(1, ink_labels_n)]
    largest_share = max(comp_areas) / max(sum(comp_areas), 1) if comp_areas else 0.0
    return {
        "ink_components": ink_labels_n - 1,
        "hole_count": len(holes),
        "largest_component_share": round(largest_share, 4),
    }


def distance_profile(clean_mask, lit_gray):
    sdf = fx.signed_distance(clean_mask)
    hole_gate_img = fx.hole_gate(clean_mask)
    is_hole = hole_gate_img < 0.999
    offsets = [8, 4, 2, -2, -8, -22, -80, -320]
    out = {"hole": {}, "open": {}, "interior": {}}
    for off in offsets:
        band = np.abs(sdf - off) < 1.0
        for key, region in (("hole", is_hole), ("open", ~is_hole & (sdf < 0)), ("interior", sdf > 2)):
            sel = band & region
            out[key][off] = float(lit_gray[sel].mean()) if sel.any() else None
    return out


def contour_displacement(mask_a, mask_b):
    a = (mask_a > 0.5).astype(np.uint8)
    b = (mask_b > 0.5).astype(np.uint8)
    xor_area = int(np.logical_xor(a, b).sum())
    contours, _ = cv2.findContours(a, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    perim = sum(cv2.arcLength(c, True) for c in contours) or 1.0
    return xor_area / perim


def stroke_ratio(mask):
    m = (mask > 0.5).astype(np.uint8)
    if m.sum() == 0:
        return None
    dist = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    vals = dist[m > 0]
    q = np.quantile(vals, 0.9)
    ys, _ = np.where(m > 0)
    height = ys.max() - ys.min() + 1
    return float(2 * q / height)


def main():
    report = {}
    for scene in scenes.SCENES:
        if not scene.has_headline:
            continue
        settled_t = 3.0 + scene.time_offset  # fully revealed, before outfade
        mask = letter_mask_at(scene, settled_t)
        report[scene.id] = {
            "readability": readability(mask),
            "stroke_ratio_pre_ignition": stroke_ratio(mask),
        }
        flick, _ = fx.flicker_mask(mask, settled_t, 1.0)
        I = fx.light_field(mask, flick, scene.light_center, W, H)
        report[scene.id]["distance_profile"] = distance_profile(mask, I)

    # contour displacement: average over a run of consecutive frames
    # mid-scene (light fully on) -- a single adjacent pair can land
    # inside the same 20fps-quantized source-time bucket and read a
    # false zero, so this averages across enough pairs to cross
    # several quantization steps.
    clean_vals, flick_vals = [], []
    for f0 in range(180, 200):
        f1 = f0 + 1
        sc = scenes.scene_for_frame(f0)
        t0, t1 = scenes.source_time_seconds(f0, sc), scenes.source_time_seconds(f1, sc)
        m0, m1 = letter_mask_at(sc, t0), letter_mask_at(sc, t1)
        flick0, _ = fx.flicker_mask(m0, t0, 1.0)
        flick1, _ = fx.flicker_mask(m1, t1, 1.0)
        clean_vals.append(contour_displacement(m0, m1))
        flick_vals.append(contour_displacement(flick0, flick1))
    report["contour_displacement_px"] = {
        "clean_mask (rays/smear source) mean": float(np.mean(clean_vals)),
        "flicker_mask (near/core source) mean": float(np.mean(flick_vals)),
    }

    print(json.dumps(report, indent=2, default=str))
    out = paths.OUT_DIR / "qa_report.json"
    out.write_text(json.dumps(report, indent=2, default=str))
    print("\nwrote", out)


if __name__ == "__main__":
    main()
