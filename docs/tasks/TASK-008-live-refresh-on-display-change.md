# TASK-008 — Live refresh on monitor/layout changes

| Field | Value |
|---|---|
| Status | Todo |
| Milestone | M3 — System integration |
| Depends on | TASK-005 (TASK-006 for the countdown part) |
| Requirements | FR-14, FR-15, NFR-02 |
| Read first | `docs/ARCHITECTURE.md` §12 |

## What
Keep the popup in sync with the real display state when monitors are plugged/unplugged or the layout/resolution changes outside the app.

## Why
Without this, the popup could show a stale layout and the next drag could be computed from wrong sizes.

## Expected behaviour
- Popup open, owner changes arrangement in Windows Settings → popup tiles move to the new real positions within ~0.5 s.
- Popup open, monitor 2 unplugged → message "Only one display is connected"; plugged back → tiles return.
- Win+P Duplicate/Extend while open → message/tiles switch accordingly.
- Revert countdown running and monitor 2 disappears → countdown cancelled, bar hidden, logged.
- No timers or polling while idle.

## Affected files
- Edit `src/display_location/app.py` (connect `QGuiApplication` screen signals, 250 ms debounce `QTimer`, `refresh()`).
- Edit `src/display_location/popup.py` (`refresh(snapshot)` from TASK-005 used live; don't interrupt an active drag — apply the refresh after release).
- Edit `src/display_location/revert.py` (`cancel()`).

## Implementation requirements
1. Connect `screenAdded`, `screenRemoved`, `primaryScreenChanged`, and `geometryChanged` of every current and newly added screen.
2. Debounce to a single `displays.snapshot()` call per burst of signals.
3. The app's own `set_position` also triggers these signals — refresh must be harmless (no extra apply, no countdown restart).

## Acceptance criteria
- [ ] All four "Expected behaviour" scenarios observed on the owner's machine.
- [ ] Idle CPU stays ~0 % in Task Manager over 1 minute.
- [ ] Moving via the popup does not cause flicker loops or repeated log lines (one refresh per change).

## Edge cases
- Resolution change of monitor 2 → tile size updates.
- Primary monitor changed in Windows Settings → tiles renumber correctly (1 = new primary).

## Out of scope
Supporting 3+ monitors.
