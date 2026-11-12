"""Unit tests for layout.py — the snap and canvas maths (ARCHITECTURE §5)."""

import random

import pytest

from display_location import layout
from display_location.layout import Rect, Side, along, describe, snap


# --------------------------------------------------------------------------- side + edge coordinate

@pytest.mark.parametrize(
    "drop, expected",
    [
        ((2500, 30), (Side.RIGHT, 1920, 0)),       # x == Pw; within magnet of 0
        ((-2500, 300), (Side.LEFT, -1920, 300)),   # x == -Sw; no magnet
        ((100, -1500), (Side.TOP, 100, -1080)),    # y == -Sh
        ((-50, 1200), (Side.BOTTOM, 0, 1080)),     # y == Ph
    ],
)
def test_clear_drops_equal_sizes(drop, expected):
    assert snap(1920, 1080, 1920, 1080, *drop) == expected


def test_outputs_are_int():
    side, x, y = snap(2560, 1440, 1920, 1080, 2600.7, 413.2)
    assert type(x) is int and type(y) is int and side is Side.RIGHT


@pytest.mark.parametrize(
    "drop, expected",
    [((1920, 1080), (Side.RIGHT, 1920, 972)), ((-1920, -1080), (Side.LEFT, -1920, -972))],
)
def test_corner_tie_goes_horizontal(drop, expected):
    # |nx| == |ny| == 1 → horizontal; along() clamps to the minimum overlap.
    assert snap(1920, 1080, 1920, 1080, *drop) == expected


# --------------------------------------------------------------------------- clamping

# Drops far down/up AND even further right, so RIGHT still wins (|nx| > |ny|).

def test_clamp_far_past_bottom_end():
    side, x, y = snap(2560, 1440, 1920, 1080, 6000, 3000)
    assert (side, x, y) == (Side.RIGHT, 2560, 1332)
    assert 1440 - y == 108  # overlap == 10 % of the shorter edge (1080)


def test_clamp_far_past_top_end():
    side, x, y = snap(2560, 1440, 1920, 1080, 6000, -3000)
    assert (side, y) == (Side.RIGHT, -972)
    assert y + 1080 == 108


def test_clamp_far_past_left_end_on_top():
    side, x, y = snap(2560, 1440, 1920, 1080, -4000, -6000)
    assert (side, x, y) == (Side.TOP, -1728, -1080)  # lo = -1920 + 192
    assert x + 1920 == 192  # overlap == 10 % of 1920


def test_clamp_with_larger_secondary():
    side, x, y = snap(1920, 1080, 3840, 2160, 8000, 3000)
    assert (side, x, y) == (Side.RIGHT, 1920, 972)
    assert 1080 - y >= 108


# --------------------------------------------------------------------------- magnets (P 2560×1440, S 1920×1080)
# vertical candidates: start 0, centre 180, end 360; threshold 0.05 × 1440 = 72

@pytest.mark.parametrize(
    "drop_y, expected_y",
    [
        (250, 180),   # 70 from centre → centred
        (110, 180),   # -70 from centre → centred
        (253, 253),   # 73 from centre, 107 from end → free
        (-60, 0),     # near start → top-aligned
        (60, 0),
        (410, 360),   # near end → bottom-aligned
        (100, 100),   # between start and centre, outside both → free
    ],
)
def test_vertical_magnets(drop_y, expected_y):
    assert snap(2560, 1440, 1920, 1080, 2600, drop_y) == (Side.RIGHT, 2560, expected_y)


def test_horizontal_magnet_centred_on_top():
    # horizontal candidates: 0, 320, 640; threshold 0.05 × 2560 = 128
    assert snap(2560, 1440, 1920, 1080, 420, -2000) == (Side.TOP, 320, -1080)


def test_equal_edges_snap_to_zero():
    assert along(40, 1080, 1080) == 0
    assert along(-40, 1080, 1080) == 0
    assert along(0, 1080, 1080) == 0


# --------------------------------------------------------------------------- different sizes / orientation

def test_larger_secondary_right_centred():
    assert snap(1920, 1080, 3840, 2160, 1920, -540) == (Side.RIGHT, 1920, -540)


def test_larger_secondary_below_centred():
    assert snap(1920, 1080, 3840, 2160, -960, 1500) == (Side.BOTTOM, -960, 1080)


def test_portrait_secondary_left_centred():
    assert snap(1920, 1080, 1080, 1920, -1500, -420) == (Side.LEFT, -1080, -420)


def test_portrait_secondary_above_centred():
    assert snap(1920, 1080, 1080, 1920, 420, -2500) == (Side.TOP, 420, -1920)


@pytest.mark.parametrize(
    "pw, ph, sw, sh",
    [(1920, 1080, 1920, 1080), (2560, 1440, 1920, 1080), (1920, 1080, 3840, 2160),
     (1920, 1080, 1080, 1920), (1920, 1080, 2400, 1080), (1366, 768, 1920, 1200)],
)
def test_every_snap_touches_and_overlaps(pw, ph, sw, sh):
    rng = random.Random(1234)
    for _ in range(2000):
        dx, dy = rng.uniform(-3 * sw, pw + 2 * sw), rng.uniform(-3 * sh, ph + 2 * sh)
        side, x, y = snap(pw, ph, sw, sh, dx, dy)
        if side.horizontal:
            assert x == (pw if side is Side.RIGHT else -sw)
            overlap = min(ph, y + sh) - max(0, y)
            assert overlap >= max(1, round(0.1 * min(sh, ph)))
        else:
            assert y == (ph if side is Side.BOTTOM else -sh)
            overlap = min(pw, x + sw) - max(0, x)
            assert overlap >= max(1, round(0.1 * min(sw, pw)))


def test_centred_rounds_half_up():
    # (1080 - 1025) / 2 = 27.5 → 28 (Python's round() would give 28 here but 26 for 26.5)
    assert layout.placed(1920, 1080, 1920, 1025, Side.RIGHT) == (1920, 28)
    assert layout.placed(1920, 1080, 1920, 1027, Side.RIGHT) == (1920, 27)  # 26.5 → 27


@pytest.mark.parametrize(
    "side, align, expected",
    [(Side.RIGHT, "centre", (2560, 180)), (Side.LEFT, "start", (-1920, 0)),
     (Side.TOP, "end", (640, -1080)), (Side.BOTTOM, "centre", (320, 1440))],
)
def test_placed(side, align, expected):
    assert layout.placed(2560, 1440, 1920, 1080, side, align) == expected


# --------------------------------------------------------------------------- describe

P = Rect(0, 0, 2560, 1440)


@pytest.mark.parametrize(
    "sec, text",
    [
        (Rect(2560, 0, 1920, 1080), "Right of 1 (top-aligned)"),
        (Rect(2560, 180, 1920, 1080), "Right of 1 (centred)"),
        (Rect(2560, 360, 1920, 1080), "Right of 1 (bottom-aligned)"),
        (Rect(2560, 100, 1920, 1080), "Right of 1"),
        (Rect(-1920, 0, 1920, 1080), "Left of 1 (top-aligned)"),
        (Rect(-1920, 180, 1920, 1080), "Left of 1 (centred)"),
        (Rect(-1920, 360, 1920, 1080), "Left of 1 (bottom-aligned)"),
        (Rect(-1920, -300, 1920, 1080), "Left of 1"),
        (Rect(0, -1080, 1920, 1080), "Above 1 (left-aligned)"),
        (Rect(320, -1080, 1920, 1080), "Above 1 (centred)"),
        (Rect(640, -1080, 1920, 1080), "Above 1 (right-aligned)"),
        (Rect(-500, -1080, 1920, 1080), "Above 1"),
        (Rect(0, 1440, 1920, 1080), "Below 1 (left-aligned)"),
        (Rect(320, 1440, 1920, 1080), "Below 1 (centred)"),
        (Rect(640, 1440, 1920, 1080), "Below 1 (right-aligned)"),
        (Rect(10, 1440, 1920, 1080), "Below 1"),
    ],
)
def test_describe(sec, text):
    assert describe(P, sec) == text


def test_describe_equal_edges_prefers_centred():
    assert describe(Rect(0, 0, 1920, 1080), Rect(1920, 0, 1920, 1080)) == "Right of 1 (centred)"


@pytest.mark.parametrize(
    "sec, side, text",
    [  # the owner's real layouts from TASK-002 (P 1920×1080, S 2400×1080)
        (Rect(1920, 0, 2400, 1080), Side.RIGHT, "Right of 1 (centred)"),
        (Rect(-2400, 0, 2400, 1080), Side.LEFT, "Left of 1 (centred)"),
        (Rect(-240, -1080, 2400, 1080), Side.TOP, "Above 1 (centred)"),
        (Rect(-240, 1080, 2400, 1080), Side.BOTTOM, "Below 1 (centred)"),
    ],
)
def test_side_of_real_layouts(sec, side, text):
    p = Rect(0, 0, 1920, 1080)
    assert layout.side_of(p, sec) is side
    assert describe(p, sec) == text


# --------------------------------------------------------------------------- canvas

def test_canvas_scale_fits_any_side():
    cw, ch = 340, 180
    pw, ph, sw, sh = 2560, 1440, 1920, 1080
    s = layout.canvas_scale(cw, ch, pw, ph, sw, sh)
    assert (pw + 2 * sw) * s <= cw and (ph + 2 * sh) * s <= ch
    assert s == pytest.approx(min(cw / 6400, ch / 3600) * 0.95)


@pytest.mark.parametrize("cw, ch", [(1, 1), (0, 0), (0.5, 200)])
def test_canvas_scale_positive_on_tiny_canvas(cw, ch):
    assert layout.canvas_scale(cw, ch, 1920, 1080, 1920, 1080) > 0


def test_canvas_origin_centres_primary():
    s = layout.canvas_scale(340, 180, 1920, 1080, 2400, 1080)
    ox, oy = layout.canvas_origin(340, 180, 1920, 1080, s)
    x, y, w, h = layout.to_canvas(Rect(0, 0, 1920, 1080), s, ox, oy)
    assert x + w / 2 == pytest.approx(170) and y + h / 2 == pytest.approx(90)


@pytest.mark.parametrize(
    "pw, ph, sw, sh",
    [(1920, 1080, 2400, 1080), (2560, 1440, 1920, 1080), (1920, 1080, 3840, 2160), (1920, 1080, 1080, 1920)],
)
def test_canvas_round_trip_within_1px(pw, ph, sw, sh):
    s = layout.canvas_scale(340, 180, pw, ph, sw, sh)
    ox, oy = layout.canvas_origin(340, 180, pw, ph, s)
    rng = random.Random(7)
    for _ in range(500):
        r = Rect(rng.randint(-2 * sw, pw + sw), rng.randint(-2 * sh, ph + sh), sw, sh)
        cx, cy, cw, ch = layout.to_canvas(r, s, ox, oy)
        assert cw == pytest.approx(sw * s) and ch == pytest.approx(sh * s)
        bx, by = layout.from_canvas(cx, cy, s, ox, oy)
        assert abs(bx - r.x) <= 1 and abs(by - r.y) <= 1


def test_no_qt_or_win32_imports():
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(layout))
    names = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    names |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not names & {"PySide6", "win32api", "win32con", "pywintypes", "ctypes"}
