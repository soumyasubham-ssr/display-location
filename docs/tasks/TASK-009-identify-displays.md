# TASK-009 — Identify displays overlay

| Field | Value |
|---|---|
| Status | Done |
| Milestone | M3 — System integration |
| Depends on | TASK-002, TASK-004 |
| Requirements | FR-10 (menu item), FR-11 |
| Read first | `docs/ARCHITECTURE.md` §9 |

## What
Implement `src/display_location/identify.py` and connect the "Identify displays" tray-menu item.

## Why
Lets the owner confirm which physical monitor is "1" and which is "2" — the same numbers shown in the popup tiles.

## Expected behaviour
- Clicking "Identify displays" shows, on each monitor, a rounded translucent dark box at the centre containing the number (1 = primary, 2 = secondary) in large white text (~120 pt), for 3 seconds, then it disappears.
- Overlays are always on top, do not take focus, and let clicks pass through.
- Clicking Identify again while shown restarts the 3 s timer (no duplicate windows).

## Affected files
- Create `src/display_location/identify.py`.
- Edit `src/display_location/tray.py` / `app.py` (enable and wire the menu item).

## Implementation requirements
1. Map `Display.device_name` to `QScreen.name()`; if no match, fall back to matching by geometry and log a warning.
2. Window flags: `FramelessWindowHint | WindowStaysOnTopHint | Tool | WindowTransparentForInput`, `WA_TranslucentBackground`, `WA_ShowWithoutActivating`.
3. Numbering must match the popup tiles exactly.

## Acceptance criteria
- [x] "1" appears on the primary monitor, "2" on the secondary, centred, for ~3 s.
- [x] Correct on mixed scaling (100 % + 125 %).
- [x] Doesn't steal focus from the active app (typing continues in the current window).
- [x] In SINGLE state, only "1" is shown.

## Out of scope
Showing monitor names/resolutions in the overlay.

## Completion notes (Coder, 2026-11-13)
- **New file `identify.py`:** `numbered(snap)` gives ("1", primary) and ("2", secondary when the status is OK) — the same rule as the popup tiles. `find_screen()` matches `QScreen.name()` to `Display.device_name`; if no name matches, it matches by physical size (logical geometry × device pixel ratio), preferring the screen whose primary-ness agrees, and logs a warning. `IdentifyOverlay` is a 220 px rounded translucent box with the number at ~120 pt (capped at 80 % of the box). `Identifier` keeps one window per number and one 3 s single-shot timer.
- **Window flags:** as requirement 2, plus `WindowDoesNotAcceptFocus` and `NoDropShadowWindowHint`; `setFocusPolicy(NoFocus)`.
- **Mixed DPI:** `place_on()` calls `setScreen()` before `setGeometry()`, so each overlay takes its monitor's scale and is centred in that screen's logical geometry.
- **Repeat click:** windows are reused and the timer restarts. A "2" left over from a previous click is hidden if monitor 2 has gone.
- **app.py:** `identify_displays()` takes a fresh snapshot **without** replacing `self.snapshot` (the popup's state), so a pending live refresh (TASK-008) still sees the change. `before_exit()` closes the overlays.
- **tray.py:** no change; the menu item was already enabled and emitting `identify_requested`.
- **Tests:** `tests/test_identify.py` (13 tests: numbering, name/size matching incl. 125 %, centring, flags, real-screen placement, reuse + timer restart, timeout, SINGLE, monitor 2 gone, controller wiring). 166 tests pass.
- **Owner check (2026-11-13):** the owner reports all seven checks passed (numbers on the right monitors and matching the tiles, mixed scaling, no focus stolen, click-through, repeat click, SINGLE shows only "1").
  - **Not confirmed from the log:** the Claude-started instance logged display changes from 11:06 to 11:44 but no "Identify displays" line. The owner most likely ran the check on a copy started outside Claude, which logs to the real `%LOCALAPPDATA%` (README). Acceptance rests on the owner's observation.
