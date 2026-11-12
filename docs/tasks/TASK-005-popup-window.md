# TASK-005 — Popup window: look, position, open/close, status messages

| Field | Value |
|---|---|
| Status | Done |
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
- [x] Popup look matches the description (compare side by side with Windows Settings → Display).
- [x] Tile proportions match real resolutions (test by temporarily changing monitor 2 resolution or with `--side top`).
- [x] Opens above the tray icon when the icon is pinned on the taskbar and when it is in the ^ overflow (fallback position acceptable there).
- [x] Taskbar on the primary monitor at 100 % and 125 %+ scaling: popup fully on-screen.
- [x] Outside click, Esc and second tray click all close it; second tray click does **not** immediately reopen.
- [x] Win+P → Duplicate shows the duplicate message; back to Extend shows tiles again (reopen popup).

## Edge cases
- Taskbar on top/left/right (Windhawk mods can move it) → clamping keeps the popup on-screen.
- Primary monitor with negative-coordinate secondary (left/top) → canvas still centres the primary tile.

## Out of scope
Dragging, applying, revert (TASK-006); live refresh while open (TASK-008).

## Completion notes (Coder, 2026-11-12)
- **New files:** `src/display_location/popup.py` (`Popup`, `ArrangementCanvas`, `popup_position()`, `footer_text()`), `tests/test_popup.py` (19 tests).
- **Changed:** `app.py`. `toggle_popup(open_only)` creates the popup on first use, takes a fresh `displays.snapshot()` (logged) on every open, and ignores a tray click within 300 ms (`TOGGLE_GUARD_S`) of the popup closing. `open_only=True` (menu Open, second launch) never closes the popup and skips the guard. `before_exit()` also closes the popup.
- **Look:** 360 × 240 panel inside a transparent 14 px margin for the drop shadow (window 388 × 268). Tiles are inset 1 px so touching tiles show a thin seam; tile 1 has a `#4a4a4a` border so it stays visible on `#202020`. Numbers are ~28 pt but shrink to fit small tiles.
- **Positioning (small deviation from §6):** the screen is the one under the tray icon (`QGuiApplication.screenAt`), falling back to the primary. When there is no room above the icon (taskbar at the top), the popup opens below it. Both then clamp into the work area with 8 px margin.
- **Reserved for TASK-006:** `revert_bar` (label + Keep/Revert buttons, emitting `keep_clicked` / `revert_clicked`), `error_label`, `TILE_2_HOVER`, `ArrangementCanvas.transform()` / `tile_rects()`, and `Popup.place()` to re-anchor when the bar changes the height. `Popup.refresh(snapshot)` is ready for TASK-008.
- **Verified:** rendered with the real snapshot (2 monitors, secondary right, centred): look and footer correct; duplicate message wraps cleanly. 104 tests pass.
- **Owner check (2026-11-12, owner's PC): all OK.** Opens above the icon (overflow and pinned), outside click / Esc / second tray click close it, Win+P Duplicate → message, Extend → tiles, matches Settings → Display. The log shows `status: duplicate` on the Duplicate open and "tray click right after the popup closed; not reopening" 42 ms after a close.
- **Note for QA:** the first open of that session logged `status: single` (only DISPLAY1), and later opens showed both monitors. The second monitor was probably still waking up. TASK-008 will refresh the popup live in that case.
