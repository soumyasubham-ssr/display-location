# TASK-006 — Drag & snap tile 2, apply, Keep/Revert countdown

| Field | Value |
|---|---|
| Status | Todo |
| Milestone | M2 — Tray and popup |
| Depends on | TASK-005 |
| Requirements | FR-06, FR-07, FR-08, FR-09, FR-16, NFR-06; decisions D-004, D-013 |
| Read first | `docs/ARCHITECTURE.md` §6 "Drag", §7, §14; `docs/REQUIREMENTS.md` FR-06…FR-09 |

## What
Make tile 2 draggable, snap it on release using `layout.snap`, apply the new position via `displays.set_position`, and show the "Keep changes? [Keep] [Revert] (10)" bar backed by a `RevertManager` that auto-reverts after 10 s.

## Why
This is the core feature: moving monitor 2 by drag, with a safety net if the result is wrong.

## Expected behaviour
1. Hover tile 2 → open-hand cursor; press → closed-hand; tile follows the mouse freely (may overlap tile 1 while dragging).
2. Release → tile animates (~120 ms) to the snapped spot; the position is applied to Windows; footer updates; revert bar shows with countdown 10 → 0.
3. **Keep** → bar hides, change stays. **Revert** or 0 → previous position restored, tile animates back, bar hides.
4. Drop resulting in the same position as now → nothing applied, no bar (FR-08).
5. Another drop during the countdown → applies the new position, countdown restarts at 10, but Revert still returns to the position from **before the first** change.
6. Popup closed during the countdown → countdown continues in the background; timeout still reverts. Reopening the popup shows the bar with the remaining seconds.
7. Windows rejects the change → tile animates back to the real position; inline red message "Couldn't move display: <reason>" for 5 s; logged (FR-09).
8. Exit from the tray menu during a countdown → revert first, then quit (FR-16, D-013).

## Affected files
- Create `src/display_location/revert.py` (`RevertManager`, owned by `AppController`).
- Edit `src/display_location/popup.py` (drag handling, revert bar, error label).
- Edit `src/display_location/app.py` (wire `positionChosen` → apply → `RevertManager.start`; `before_exit()` → revert if active).
- Edit `src/display_location/log_setup.py` excepthook → call controller revert if a countdown is active (NFR-06).
- Add `tests/test_revert.py` using a fake display service (no real display changes): start/keep/revert/timeout/second-drop-keeps-original.

## Implementation requirements
1. Use `layout.from_canvas` + `layout.snap`; never compute snap maths in the UI.
2. After `set_position`, read back with `displays.snapshot()` and draw the **read-back** position.
3. `RevertManager` per ARCHITECTURE §7; it must not depend on the popup being visible.
4. Disable dragging while an apply call is in progress (it is synchronous; avoid re-entrancy).

## Acceptance criteria
- [ ] Moving monitor 2 to each of the four sides works from the popup; mouse crosses screens on the new edge.
- [ ] Top-aligned / centred / bottom-aligned magnet works on the right side.
- [ ] Keep keeps; Revert reverts; doing nothing for 10 s reverts.
- [ ] Close popup during countdown → still reverts at 0.
- [ ] Second drop during countdown, then Revert → back to the original layout.
- [ ] Exit during countdown → layout reverted.
- [ ] `python -m pytest` passes (including `test_revert.py`).
- [ ] Owner's original layout restored at the end of testing.

## Edge cases
- Mouse released outside the popup → still treated as a drop (Qt delivers the release to the grabbing widget).
- Secondary monitor unplugged during countdown → cancel countdown, log it (full refresh handled in TASK-008).

## Out of scope
Autostart, identify, live refresh, packaging.
