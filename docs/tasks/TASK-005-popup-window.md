# TASK-005 — Popup window: look, position, open/close, status messages

| Field | Value |
|---|---|
| Status | Todo |
| Milestone | M2 — Tray and popup |
| Depends on | TASK-002, TASK-003, TASK-004 |
| Requirements | FR-02, FR-03, FR-04, FR-05, FR-15; decision D-005 |
| Read first | `docs/ARCHITECTURE.md` §6 (full UI spec), §5.4, §13 |

## What
Build the popup that opens from the tray: dark rounded frameless window, anchored above the tray icon, drawing the real monitor arrangement (tile 1 and tile 2) or a status message. **Dragging is NOT part of this task** (TASK-006).

## Why
This is the main UI; separating the static view from the drag interaction keeps each task testable.

## Expected behaviour
- Left-click tray → popup appears above the tray icon within ~150 ms; left-click again → closes.
- Shows title "Display arrangement", canvas with tile 1 (grey `#2d2d2d`) and tile 2 (purple `#a64dbf`) in their **real** relative positions and proportions, large white numbers, footer like "Display 2: Right of 1 · 1920 × 1080".
- Closes on outside click and on Esc.
- Status states (FR-15) show a centred message instead of the canvas:
  - SINGLE → "Only one display is connected"
  - DUPLICATE → "Displays are duplicated — press Win+P and choose Extend"
  - TOO_MANY → "More than two displays are not supported yet"
- Every time it opens, it takes a fresh `displays.snapshot()`.

## Affected files
- Create `src/display_location/popup.py` (`Popup` window + `ArrangementCanvas` widget).
- Edit `src/display_location/app.py` (`toggle_popup`, toggle-race guard).

## Implementation requirements
1. Window flags, painting, colours, fonts, sizes per ARCHITECTURE §6 (about 360 × 240 logical px, radius 12, shadow).
2. Positioning per §6 "Positioning": above `tray.geometry()`, centred on it, clamped into the primary screen's available geometry with 8 px margin; fallback bottom-right.
3. Toggle race guard: ignore a tray activation that arrives within 300 ms after the popup closed itself.
4. Canvas uses `layout.canvas_scale`, `layout.to_canvas`, `layout.describe` (no duplicate maths).
5. Reserve (hidden) widgets for the revert bar and the inline error label so TASK-006 only fills them in.
6. Expose `Popup.refresh(snapshot)` for TASK-008.

## Acceptance criteria
- [ ] Popup look matches the description (compare side by side with Windows Settings → Display).
- [ ] Tile proportions match real resolutions (test by temporarily changing monitor 2 resolution or with `--side top`).
- [ ] Opens above the tray icon when the icon is pinned on the taskbar and when it is in the ^ overflow (fallback position acceptable there).
- [ ] Taskbar on the primary monitor at 100 % and 125 %+ scaling: popup fully on-screen.
- [ ] Outside click, Esc and second tray click all close it; second tray click does **not** immediately reopen.
- [ ] Win+P → Duplicate shows the duplicate message; back to Extend shows tiles again (reopen popup).

## Edge cases
- Taskbar on top/left/right (Windhawk mods can move it) → clamping keeps the popup on-screen.
- Primary monitor with negative-coordinate secondary (left/top) → canvas still centres the primary tile.

## Out of scope
Dragging, applying, revert (TASK-006); live refresh while open (TASK-008).
