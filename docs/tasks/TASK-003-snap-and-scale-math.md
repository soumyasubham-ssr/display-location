# TASK-003 — Snap and scale maths with unit tests

| Field | Value |
|---|---|
| Status | Done (2026-11-12) |
| Milestone | M1 — Foundation |
| Depends on | TASK-001 |
| Requirements | FR-03 (footer label), FR-06, FR-08 |
| Read first | `docs/ARCHITECTURE.md` §5 (full algorithm) |

## What
Implement `src/display_location/layout.py`: pure functions that turn a dropped tile position into a valid snapped monitor position, describe the side in words, and convert between physical pixels and popup-canvas coordinates. Fully unit-tested.

## Why
The snap rules are the heart of the drag interaction; keeping them pure (no Qt, no Win32) makes them testable and keeps the UI simple.

## Expected behaviour / API
```python
class Side(Enum): LEFT, RIGHT, TOP, BOTTOM

@dataclass(frozen=True)
class Rect: x: int; y: int; w: int; h: int

MIN_OVERLAP_RATIO = 0.10
MAGNET_RATIO = 0.05

def snap(primary_w, primary_h, sec_w, sec_h, drop_x, drop_y) -> tuple[Side, int, int]
def side_of(primary: Rect, secondary: Rect) -> Side          # for an existing layout
def describe(primary: Rect, secondary: Rect) -> str            # "Right of 1", "Above 1 (centred)", ...
def canvas_scale(canvas_w, canvas_h, pw, ph, sw, sh) -> float
def to_canvas(rect: Rect, scale, origin_x, origin_y) -> tuple[float, float, float, float]
def from_canvas(cx, cy, scale, origin_x, origin_y) -> tuple[int, int]
```
- Labels: "Right of 1", "Left of 1", "Above 1", "Below 1", with suffix " (top-aligned)", " (centred)", " (bottom-aligned)" for left/right, and " (left-aligned)", " (centred)", " (right-aligned)" for above/below when the position matches exactly; no suffix otherwise.

## Affected files
- Create `src/display_location/layout.py`.
- Create `tests/test_layout.py`.

## Implementation requirements
1. Implement exactly the algorithm in ARCHITECTURE §5.1–5.4 (normalised side selection, tie → horizontal, `along()` clamp with min overlap, magnet order start → centre → end).
2. All outputs are `int` physical pixels.
3. No imports from PySide6 or pywin32.

## Acceptance criteria (tests must cover)
- [x] Drop clearly to the right / left / above / below → correct side and edge coordinate (`x == Pw`, `x == -Sw`, `y == -Sh`, `y == Ph`).
- [x] Diagonal drop exactly on a corner (|nx| == |ny|) → horizontal side.
- [x] Drop far beyond the end of an edge → clamped so overlap is ≥ 10 % of the shorter edge.
- [x] Drop within 5 % of centred → exactly centred; same for start- and end-aligned.
- [x] Different sizes: primary 2560×1440, secondary 1920×1080, and secondary larger than primary (3840×2160 next to 1920×1080).
- [x] Portrait secondary (1080×1920).
- [x] `from_canvas(to_canvas(...))` round-trips within 1 px.
- [x] `describe` returns the expected strings for all four sides and alignments.
- [x] `python -m pytest` passes.

## Edge cases
- Secondary edge equal to primary edge → start, centre and end coincide; result must be 0.
- Very small canvas → `canvas_scale` > 0.

## Out of scope
Drawing and drag handling (TASK-005/006).

## Completion notes (Coder, 2026-11-12)
- Implemented `layout.py` following ARCHITECTURE §5.1–5.4. Implementation details are in §5.5: half-up rounding, the `placed()` and `canvas_origin()` helpers, and "(centred)" winning when the edges are equal.
- `tests/test_layout.py` has 66 tests. They cover every acceptance item, the owner's real 1920×1080 + 2400×1080 layouts, and a check that no Qt/Win32 module is imported. A randomised check (2,000 drops × 6 size pairs) confirms every snap touches the primary and overlaps it by ≥ 10 % of the shorter edge.
- **Test inputs I corrected:** my first clamp tests dropped far down (y = 5000). There BOTTOM is the correct side, so they never reached the clamp. The clamp cases now drop far down *and* even further to the side.
- **TASK-002 follow-up done:** `--side` now uses `layout.placed()`, and `displays.centred_position()` is removed. Checked on the owner's monitors: `--side left` put monitor 2 at (-2400, 0), and `--side right` restored (1920, 0).
- Full suite: 75 passed.

