"""Pure snap / scale maths for the arrangement canvas (ARCHITECTURE §5).

No Qt, no Win32. All monitor values are physical pixels; the primary is the
rectangle (0, 0, Pw, Ph). Canvas values are logical pixels (floats).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

MIN_OVERLAP_RATIO = 0.10  # tiles must share >= 10 % of the shorter edge
MAGNET_RATIO = 0.05  # magnet threshold = 5 % of the primary edge
CANVAS_FILL = 0.95  # fraction of the canvas the layout may use
_MIN_SCALE = 1e-6


class Side(Enum):
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"

    @property
    def horizontal(self) -> bool:
        return self in (Side.LEFT, Side.RIGHT)


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int


def _round(v: float) -> int:
    """Round half up (Python's round() is banker's rounding, which would make
    'centred' depend on whether (p - s) / 2 lands on an even number)."""
    return int(math.floor(v + 0.5))


# --------------------------------------------------------------------------- §5.1 side selection


def _pick_side(pw: int, ph: int, sw: int, sh: int, x: float, y: float) -> Side:
    dx = (x + sw / 2) - pw / 2
    dy = (y + sh / 2) - ph / 2
    nx = dx / ((pw + sw) / 2)
    ny = dy / ((ph + sh) / 2)
    if abs(nx) >= abs(ny):  # tie -> horizontal
        return Side.RIGHT if nx > 0 else Side.LEFT
    return Side.BOTTOM if ny > 0 else Side.TOP


# --------------------------------------------------------------------------- §5.2 edge placement


def _alignments(s: int, p: int) -> tuple[int, int, int]:
    """Start-aligned, centred, end-aligned offsets along an edge of length p."""
    return 0, _round((p - s) / 2), p - s


def along(v: float, s: int, p: int) -> int:
    """Position along the shared edge: clamp for minimum overlap, then magnet-snap."""
    min_overlap = max(1, _round(MIN_OVERLAP_RATIO * min(s, p)))
    lo, hi = -s + min_overlap, p - min_overlap
    v = min(max(v, lo), hi)
    threshold = MAGNET_RATIO * p
    for c in _alignments(s, p):  # first match wins: start, centre, end
        if lo <= c <= hi and abs(v - c) <= threshold:
            return c
    return _round(v)


def snap(
    primary_w: int, primary_h: int, sec_w: int, sec_h: int, drop_x: float, drop_y: float
) -> tuple[Side, int, int]:
    """Turn a dropped secondary top-left into a valid snapped (side, x, y)."""
    pw, ph, sw, sh = primary_w, primary_h, sec_w, sec_h
    side = _pick_side(pw, ph, sw, sh, drop_x, drop_y)
    if side is Side.RIGHT:
        return side, pw, along(drop_y, sh, ph)
    if side is Side.LEFT:
        return side, -sw, along(drop_y, sh, ph)
    if side is Side.BOTTOM:
        return side, along(drop_x, sw, pw), ph
    return side, along(drop_x, sw, pw), -sh


def placed(primary_w: int, primary_h: int, sec_w: int, sec_h: int, side: Side, align: str = "centre") -> tuple[int, int]:
    """Secondary top-left for a side and alignment ("start", "centre", "end")."""
    pw, ph, sw, sh = primary_w, primary_h, sec_w, sec_h
    idx = {"start": 0, "centre": 1, "end": 2}[align]
    if side.horizontal:
        y = _alignments(sh, ph)[idx]
        return (pw if side is Side.RIGHT else -sw), y
    x = _alignments(sw, pw)[idx]
    return x, (ph if side is Side.BOTTOM else -sh)


# --------------------------------------------------------------------------- §5.3 description


def side_of(primary: Rect, secondary: Rect) -> Side:
    """Which side of the primary an existing secondary is on."""
    return _pick_side(primary.w, primary.h, secondary.w, secondary.h, secondary.x, secondary.y)


_SIDE_TEXT = {Side.RIGHT: "Right of 1", Side.LEFT: "Left of 1", Side.TOP: "Above 1", Side.BOTTOM: "Below 1"}
_SUFFIX = {
    True: {"start": "top-aligned", "centre": "centred", "end": "bottom-aligned"},
    False: {"start": "left-aligned", "centre": "centred", "end": "right-aligned"},
}


def describe(primary: Rect, secondary: Rect) -> str:
    """Footer text, e.g. "Right of 1", "Above 1 (centred)".

    When several alignments coincide (equal edge lengths), "centred" wins.
    """
    side = side_of(primary, secondary)
    text = _SIDE_TEXT[side]
    if side.horizontal:
        offset, (start, centre, end) = secondary.y - primary.y, _alignments(secondary.h, primary.h)
    else:
        offset, (start, centre, end) = secondary.x - primary.x, _alignments(secondary.w, primary.w)
    for name, value in (("centre", centre), ("start", start), ("end", end)):
        if offset == value:
            return f"{text} ({_SUFFIX[side.horizontal][name]})"
    return text


# --------------------------------------------------------------------------- §5.4 canvas


def canvas_scale(canvas_w: float, canvas_h: float, pw: int, ph: int, sw: int, sh: int) -> float:
    """Scale so the primary plus the secondary on any side always fits the canvas."""
    scale = min(canvas_w / (pw + 2 * sw), canvas_h / (ph + 2 * sh)) * CANVAS_FILL
    return max(scale, _MIN_SCALE)


def canvas_origin(canvas_w: float, canvas_h: float, pw: int, ph: int, scale: float) -> tuple[float, float]:
    """Canvas position of physical (0, 0), with the primary tile centred in the canvas."""
    return (canvas_w - pw * scale) / 2, (canvas_h - ph * scale) / 2


def to_canvas(rect: Rect, scale: float, origin_x: float, origin_y: float) -> tuple[float, float, float, float]:
    """Physical rect -> canvas (x, y, w, h)."""
    return origin_x + rect.x * scale, origin_y + rect.y * scale, rect.w * scale, rect.h * scale


def from_canvas(cx: float, cy: float, scale: float, origin_x: float, origin_y: float) -> tuple[int, int]:
    """Canvas point -> physical (x, y)."""
    return _round((cx - origin_x) / scale), _round((cy - origin_y) / scale)
