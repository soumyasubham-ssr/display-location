# TASK-008 — Live refresh on monitor/layout changes

| Field | Value |
|---|---|
| Status | Done |
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
- [x] All four "Expected behaviour" scenarios observed on the owner's machine.
- [x] Idle CPU stays ~0 % in Task Manager over 1 minute.
- [x] Moving via the popup does not cause flicker loops or repeated log lines (one refresh per change).

## Edge cases
- Resolution change of monitor 2 → tile size updates.
- Primary monitor changed in Windows Settings → tiles renumber correctly (1 = new primary).

## Out of scope
Supporting 3+ monitors.

## Completion notes (Coder, 2026-11-13)
- **app.py:** `AppController._watch_screens()` (called from `start()`) connects `screenAdded`, `screenRemoved`, `primaryScreenChanged` and `geometryChanged` of every current screen; a newly added screen gets its `geometryChanged` connected in `_on_screen_added`. Every signal restarts a single-shot `QTimer` (`DISPLAY_DEBOUNCE_MS = 250`), so a burst gives one `displays.snapshot()` in `on_displays_changed()`. No timer runs while idle.
- **Harmless after our own move:** if the new snapshot equals the one already shown (our `set_position` read-back), nothing is logged or redrawn; the refresh never calls `set_position` or `revert.start`.
- **No drag interruption:** while the canvas is dragging or animating (or an apply is running), the refresh re-arms the debounce timer and runs after release.
- **Countdown:** `_take_snapshot()` already cancels the countdown (`RevertManager.cancel`, from TASK-006) when the secondary is gone; the live refresh runs it even while the popup is closed. `revert.py` needed no change.
- **popup.py:** only docstrings; `refresh(snap, animate=True)` is used live, so tiles glide to a new position.
- **Exit:** `before_exit()` stops the debounce timer.
- **Tests:** `tests/test_live_refresh.py` (12 tests: debounce, move/resize/unplug/replug/duplicate, countdown cancel with popup open and closed, own-move harmless, drag not interrupted, exit, primary swapped during the countdown). A script confirmed the signals connect to the real `\\.\DISPLAY1` / `\\.\DISPLAY5` screens.
- **Owner check on the real monitors (2026-11-13):** all scenarios passed: arrangement changed in Settings, unplug/replug, Win+P Duplicate/Extend, unplug during the countdown (cancelled, no revert), resolution change, primary changed, idle CPU ~0 %, one log line per own move.
- **Fix found in that run's log:** the owner made the other monitor primary and then changed it back while a countdown was running. At 0 the countdown tried to revert `DISPLAY1`, which was the primary again, and Windows refused ("The primary display cannot be moved"). `_take_snapshot()` now also cancels the countdown when the revert target is no longer the secondary. New test `test_primary_swapped_during_countdown_cancels_it`; 153 tests pass. This fix is covered by the unit test only, not re-checked on the monitors.
