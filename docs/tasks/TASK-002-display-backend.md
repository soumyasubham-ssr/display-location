# TASK-002 — Display backend: read and set monitor position + CLI

| Field | Value |
|---|---|
| Status | Done (2026-11-12) |
| Milestone | M1 — Foundation |
| Depends on | TASK-001 |
| Requirements | FR-07 (apply part), FR-09, FR-15, NFR-01, NFR-04; decisions D-003, D-011 |
| Read first | `docs/ARCHITECTURE.md` §4 (full spec), §13 |

## What
Implement `src/display_location/displays.py`: the **only** module that reads and changes Windows display positions. Add the debug CLI flags `--list` and `--side`.

## Why
The popup, revert logic and identify feature all need an accurate snapshot of the two monitors and a reliable "move secondary to (x, y)".

## Expected behaviour
- `python -m display_location --list` prints e.g.
  ```
  status: ok
  #  device        name                 primary  x      y     width  height
  1  \\.\DISPLAY1  Generic PnP Monitor  yes      0      0     1920   1080
  2  \\.\DISPLAY2  DELL P2419H          no       1920   0     1920   1080
  ```
- `python -m display_location --side left` moves the secondary monitor so it is left of the primary, vertically centred (use `layout.py` if TASK-003 is done; otherwise compute centred position inline and switch to `layout.py` later), then prints the new `--list` output. **No revert** — developer tool.

## Affected files
- Create `src/display_location/displays.py`.
- Edit `src/display_location/__main__.py` (add `--list`, `--side {left,right,top,bottom}`; these run without starting Qt).
- Create `tests/test_displays.py` — tests that do not change the layout: `snapshot()` returns a status, primary is at (0, 0), widths/heights > 0. Mark with `pytest.mark.skipif` when not on Windows.

## Implementation requirements
1. Follow the API in ARCHITECTURE §4.1 exactly (`Display`, `DisplayStatus`, `DisplaySnapshot`, `snapshot()`, `set_position()`, `DisplayChangeError`).
2. Reading per §4.2; writing per §4.3 (stage secondary with `DM_POSITION` + `CDS_UPDATEREGISTRY | CDS_NORESET`, stage primary at (0, 0) likewise, then call `ChangeDisplaySettingsEx()` with no arguments).
3. Map non-zero return codes to readable messages (`DISP_CHANGE_BADMODE`, `DISP_CHANGE_FAILED`, `DISP_CHANGE_NOTUPDATED`, `DISP_CHANGE_BADPARAM`, `DISP_CHANGE_RESTART`, …) in `DisplayChangeError`.
4. Duplicate detection via `QueryDisplayConfig(QDC_ONLY_ACTIVE_PATHS)` with `ctypes` (§4.2 step 5). If it cannot be made reliable, use the documented fallback and **record which approach was used** as a new decision in `docs/DECISIONS.md`.
5. Log every `set_position` call: device, from → to, result.
6. No Qt imports in this module.

## Acceptance criteria
- [x] `--list` matches what Windows Settings → Display shows (positions/resolutions).
- [x] `--side left|right|top|bottom` each visibly moves monitor 2 to that side (check by moving the mouse across the edge) and `--list` confirms the coordinates.
- [x] Afterwards restore the owner's original layout with `--side right` (or whatever it was).
- [x] With displays duplicated (Win+P → Duplicate), `--list` shows `status: duplicate` (or the documented fallback).
- [x] Works without admin rights.
- [x] `python -m pytest` passes.

## Edge cases
- Disconnected/inactive adapters in the enumeration → ignored.
- Monitors with different resolutions and scaling → physical pixels are used; verify with mixed scaling if available.
- `set_position` with a position Windows adjusts → caller reads back via `snapshot()` (document this in the docstring).

## Out of scope
Snap maths (TASK-003), UI, revert (TASK-006).

## Completion notes (Coder, 2026-11-12)
- **Owner's setup:** DISPLAY1 "Generic PnP Monitor" 1920×1080 (primary). DISPLAY21 "Generic Non-PnP Monitor" 2400×1080, originally right of the primary at (1920, 0).
- **`--side` results:** left (-2400, 0), top (-240, -1080), bottom (-240, 1080), right (1920, 0). Each matched the requested position exactly. A scripted check moved the cursor to each new centre of monitor 2, and `MonitorFromPoint` reported DISPLAY21 every time. The original layout was restored with `--side right`.
- **Duplicate mode:** Win+P → Duplicate gives `status: duplicate` (D-014). One monitor alone gives `status: single`. Extend was restored afterwards with `DisplaySwitch.exe /extend`, which brought back the original layout.
- **No admin:** the tests ran in a non-elevated session.
- **Tests:** `pytest` gives 13 passed. `tests/test_displays.py` is read-only. It also covers the error-code mapping, refusing to move the primary or an unknown device, the centring maths and the `--list` format.
- **Not tested:** mixed scaling (both monitors were at their default scale). Leave this for QA.
- **Follow-up for TASK-003:** switch `--side` from `displays.centred_position()` to `layout.py`.

