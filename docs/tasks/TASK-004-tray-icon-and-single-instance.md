# TASK-004 — Tray icon, context menu, single instance, app icon

| Field | Value |
|---|---|
| Status | Done (2026-11-12) |
| Milestone | M2 — Tray and popup |
| Depends on | TASK-001 |
| Requirements | FR-01, FR-02 (signal only), FR-10, FR-13, FR-16, NFR-03 |
| Read first | `docs/ARCHITECTURE.md` §3, §8, §11; `docs/DECISIONS.md` D-010 |

## What
Create the app icon, the tray icon with its right-click menu, the single-instance guard, and wire them in `AppController`.

## Why
The tray icon is the app's only entry point; single-instance prevents duplicate icons when the exe is started twice (e.g. autostart + manual launch).

## Expected behaviour
- On start, the tray shows the Display Location icon with tooltip "Display Location" within 3 s.
- Left-click → `AppController.toggle_popup()` (until TASK-005 exists: log "popup toggle requested").
- Right-click menu: **Open**, **Identify displays**, **Start with Windows** (checkable), separator, **Exit**. Identify and Start with Windows are placeholders (disabled or logging) until TASK-009/TASK-007.
- **Exit** removes the icon and quits (the revert-on-exit hook from FR-16 is added in TASK-006; leave a clearly named hook `AppController.before_exit()`).
- Starting a second instance: the second process sends `show` to the first and exits within ~1 s; the first logs it and calls `toggle_popup(open_only=True)`.

## Affected files
- Create `tools/make_icon.py` — draws the icon with Pillow: two rounded rectangles side by side (grey "1", purple `#a64dbf` "2") on transparent background; saves `assets/icon.ico` with sizes 16, 20, 24, 32, 40, 48, 64, 256. Must be legible at 16 px on dark and light taskbars.
- Create `assets/icon.ico` (generated, committed).
- Create `src/display_location/tray.py`.
- Create `src/display_location/single_instance.py`.
- Create a resource-path helper (e.g. `src/display_location/resources.py`) that resolves `assets/icon.ico` from source and from a PyInstaller bundle (`sys._MEIPASS`).
- Edit `src/display_location/app.py`.

## Implementation requirements
1. Single instance per ARCHITECTURE §11 (`QLocalServer` name `DisplayLocation-<USERNAME>`, `removeServer` before `listen`).
2. The single-instance check runs **before** creating the tray icon.
3. Menu state refreshed on `aboutToShow`.
4. Set `QApplication.setApplicationName("Display Location")` and the window icon globally.

## Acceptance criteria
- [x] Icon visible in the tray (or the ^ overflow) with correct tooltip; looks sharp at 100 % and 150 % scaling.
- [x] Left-click triggers the toggle hook (log line).
- [x] Right-click shows the menu with the five entries in order; Exit quits and the icon disappears.
- [x] Running `python -m display_location` twice leaves exactly one tray icon; the log of the first shows the "show" message.
- [x] Killing the process (Task Manager) and restarting still works (stale server name is cleaned up).

## Edge cases
- Tray not available (`QSystemTrayIcon.isSystemTrayAvailable()` false, e.g. Explorer restarting) → retry every 2 s up to 30 s, then log an error and exit.
- Explorer restart while running → Qt re-adds the icon; verify it reappears.

## Out of scope
Popup UI (TASK-005), autostart logic (TASK-007), identify (TASK-009).

## Completion notes (Coder, 2026-11-12)
- **Icon:** the icon is built from the owner's `assets/icon-source.png`, not drawn with Pillow (D-015). `tools/make_icon.py` regenerates `assets/icon.ico`.
- **New files:**
  - `src/display_location/tray.py`
  - `src/display_location/single_instance.py`
  - `src/display_location/resources.py`
  - `tests/test_tray.py`
  - `tests/test_single_instance.py`
  - `tests/conftest.py` (one shared `QApplication`; using a plain `QCoreApplication` and widgets in one run crashed Python)
- **Changed:** `app.py`. `AppController` has `toggle_popup(open_only)`, `identify_displays()`, `set_autostart()`, `exit()` and `before_exit()`. `before_exit()` is connected to `aboutToQuit`, so it runs on every quit path.
- **Placeholders:**
  - Start with Windows is shown greyed out (TASK-007).
  - Identify only logs (TASK-009).
  - Left-click and Open log "popup toggle requested" (TASK-005).
- **Verified on the owner's PC (150 % scaling, 2 monitors):**
  - The icon appears in the ^ overflow and is sharp. The owner confirmed the tooltip "Display Location" and the 5 menu entries in order.
  - Left-click logged the toggle.
  - Exit logged "Exit requested", then exited with code 0. The icon disappeared and no process was left behind.
  - A second `python -m display_location` exited with code 0 in about 1.2 s, including Python and Qt start-up. The first instance logged `Received b'show'` and then `popup toggle requested (open_only=True)`.
  - Restart after a crash: `test_restart_after_killed_instance` hard-kills a real server process and confirms that a new one listens and receives `show`.
- **Tests:** 85 passed.
- **Not tested:** whether the icon comes back after Explorer restarts. That needs an Explorer restart, which closes the owner's File Explorer windows, so it's left for QA.

