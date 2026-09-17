"""Typesetting: ink-box-fitted headlines/captions, per-glyph reveal.

Font size and letter-spacing are never specified as fixed numbers --
they're bisected so the rendered ink bounding box (the tight box around
actually-painted pixels, not the font's nominal em box) always lands on
a target width/height. That keeps block dimensions stable when the
copy in content.json changes.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw, ImageFont

PAD = 8  # shared between render_line_mask and glyph_reveal_alpha's column mapping


def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def _ink_bbox_for_text(font_path, size, text, tracking):
    """Renders `text` with per-character `tracking` extra px between
    glyphs, returns (ink_w, ink_h, per_glyph_x_ranges, full_image_size).
    """
    font = _load_font(font_path, size)
    # First pass: measure natural glyph advances/bboxes on a scratch canvas.
    scratch = Image.new("L", (8, 8), 0)
    d = ImageDraw.Draw(scratch)
    x = 0.0
    glyph_boxes = []  # (char, x0, x1) in the layout x-axis before global ink offset
    for ch in text:
        bbox = d.textbbox((x, 0), ch, font=font)
        adv = d.textlength(ch, font=font)
        glyph_boxes.append((ch, x, x + adv, bbox))
        x += adv + tracking

    # Composite ink bbox = union of all glyph bboxes.
    xs0 = [b[3][0] for b in glyph_boxes] or [0]
    ys0 = [b[3][1] for b in glyph_boxes] or [0]
    xs1 = [b[3][2] for b in glyph_boxes] or [0]
    ys1 = [b[3][3] for b in glyph_boxes] or [0]
    ink_x0, ink_y0, ink_x1, ink_y1 = min(xs0), min(ys0), max(xs1), max(ys1)
    return (ink_x1 - ink_x0), (ink_y1 - ink_y0), glyph_boxes, (ink_x0, ink_y0, ink_x1, ink_y1)


def _bisect(lo, hi, f, target, iters=28):
    """Finds x in [lo, hi] with f(x) ~= target, f assumed monotonic increasing."""
    flo, fhi = f(lo), f(hi)
    if flo > target:
        return lo
    if fhi < target:
        return hi
    for _ in range(iters):
        mid = (lo + hi) / 2.0
        if f(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


@dataclass
class FittedLine:
    text: str
    font_path: str
    font_size: float
    tracking: float
    ink_box: tuple  # x0,y0,x1,y1 in local layout space
    glyphs: list  # list of (char, x0, x1) local x-range within ink space
    y_origin: float = 0.0  # raw draw-space y of the ink top, to subtract when rendering


def fit_line(font_path, text, target_w, target_h) -> FittedLine:
    if not text:
        return FittedLine(text, str(font_path), 1.0, 0.0, (0, 0, 0, 0), [], 0.0)

    def h_of(size):
        _, ih, _, _ = _ink_bbox_for_text(font_path, size, text, 0.0)
        return ih

    size = _bisect(4.0, 2000.0, h_of, target_h)

    def w_of(tracking):
        iw, _, _, _ = _ink_bbox_for_text(font_path, size, text, tracking)
        return iw

    # Tracking may need to go negative to tighten an overshoot; keep it
    # in a sane range relative to font size.
    tmax = size * 4.0
    tracking = _bisect(-size * 0.15, tmax, w_of, target_w)

    iw, ih, glyph_boxes, ink_bbox = _ink_bbox_for_text(font_path, size, text, tracking)
    glyphs = [(ch, x0 - ink_bbox[0], x1 - ink_bbox[0]) for (ch, x0, x1, _) in glyph_boxes]
    return FittedLine(text, str(font_path), size, tracking, (0, 0, iw, ih), glyphs, ink_bbox[1])


def render_line_mask(line: FittedLine, pad=PAD):
    """Renders the fitted line to a tight, padded single-channel mask."""
    if not line.text:
        return np.zeros((1, 1), dtype=np.float32), line
    font = _load_font(line.font_path, line.font_size)
    w = int(np.ceil(line.ink_box[2] - line.ink_box[0])) + pad * 2
    h = int(np.ceil(line.ink_box[3] - line.ink_box[1])) + pad * 2
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    for ch, gx0, gx1 in line.glyphs:
        d.text((pad + gx0, pad - line.y_origin), ch, font=font, fill=255)
    arr = np.asarray(img, dtype=np.float32) / 255.0
    return arr, line


def glyph_reveal_alpha(line: FittedLine, mask_w: int, progress: float, ltr: bool) -> np.ndarray:
    """Per-column [0,1] multiplier over the rendered mask's width,
    implementing letter-unit reveal: a glyph is either fully shown or
    hidden depending on whether `progress` (0..1, section 7's
    reveal_fraction) has swept past its position, direction-dependent.
    Returns a (mask_w,) array to be broadcast-multiplied against the
    glyph mask's alpha channel.
    """
    col = np.zeros(mask_w, dtype=np.float32)
    if not line.glyphs:
        return col
    total_w = line.ink_box[2] - line.ink_box[0]
    if total_w <= 0:
        return col
    pad_offset = (mask_w - total_w) / 2.0  # matches render_line_mask's pad on both sides
    glyphs = line.glyphs if ltr else list(reversed(line.glyphs))
    n = len(glyphs)
    for i, (ch, gx0, gx1) in enumerate(glyphs):
        glyph_progress = (i + 1) / n
        shown = 1.0 if progress >= glyph_progress - 1e-6 else 0.0
        x0 = int(np.floor(gx0 + pad_offset))
        x1 = int(np.ceil(gx1 + pad_offset))
        x0 = max(0, min(mask_w, x0))
        x1 = max(0, min(mask_w, x1))
        if shown:
            col[x0:x1] = 1.0
    return col
