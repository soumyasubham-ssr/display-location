# TASK-009 — Identify displays overlay

| Field | Value |
|---|---|
| Status | Todo |
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
- [ ] "1" appears on the primary monitor, "2" on the secondary, centred, for ~3 s.
- [ ] Correct on mixed scaling (100 % + 125 %).
- [ ] Doesn't steal focus from the active app (typing continues in the current window).
- [ ] In SINGLE state, only "1" is shown.

## Out of scope
Showing monitor names/resolutions in the overlay.
