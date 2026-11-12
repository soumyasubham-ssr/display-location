# Decisions — Display Location

**Last Updated:** 2026-11-12

Each decision: context → decision → consequences. Status is **Accepted** unless marked otherwise. New decisions get the next number; superseded ones stay, marked *Superseded by D-xxx*.

---

### D-001 — Independent-display features come from Windhawk, not this app
- **Context:** The owner also wanted taskbar icons only on the window's monitor and monitor 2 unaffected by virtual-desktop switches. Research (2026-11-12) of the Windhawk catalog found ready mods: *Independent taskbar per monitor* (`taskbar-independent-per-monitor`), *Secondary Monitor Pin* (`secondary-monitor-pin`), plus *Alt+Tab per monitor*, *Win+D per monitor*, *Split Tray*. Windhawk provides an on/off toggle per mod.
- **Decision:** The owner manages those with Windhawk. This app builds **only** the second-monitor placement tool.
- **Consequences:** Much smaller scope. Fully separate desktops per monitor (no Windhawk mod exists) remain out of scope; IndepenDesk / Actual Virtual Desktops are the external options if ever wanted.

### D-002 — Python + PySide6 for the UI and tray
- **Context:** Needs a good-looking, frameless, rounded, draggable popup plus a tray icon. Options: tkinter/customtkinter + pystray, wxPython, PySide6.
- **Decision:** PySide6 (Qt 6). It has a built-in `QSystemTrayIcon`, translucent frameless windows, animations, local sockets for single-instance, and screen-change signals.
- **Consequences:** Larger exe (~40–60 MB). One framework for everything; no pystray.

### D-003 — `ChangeDisplaySettingsEx` (pywin32) to move the monitor
- **Context:** Windows offers the legacy `ChangeDisplaySettingsEx` and the modern CCD `SetDisplayConfig`. CCD is more capable but hard to call from Python.
- **Decision:** Use `ChangeDisplaySettingsEx` with `DM_POSITION`, `CDS_UPDATEREGISTRY | CDS_NORESET`, then a final apply call. `ctypes` + `QueryDisplayConfig` only for duplicate-mode detection.
- **Consequences:** Simple, no admin rights. If a future need (e.g. multi-GPU edge cases) breaks it, revisit with CCD.

### D-004 — Apply immediately on drop, with a 10-second Keep/Revert safety bar
- **Context:** Owner wants direct manipulation; a wrong layout can make the mouse hard to move between screens.
- **Decision:** Apply on release; show "Keep / Revert (10)"; auto-revert on timeout.
- **Consequences:** Needs RevertManager independent of the popup (ARCHITECTURE §7).

### D-005 — Popup is fixed; only the monitor tiles are draggable
- **Context:** Owner clarified "draggable" means dragging the monitor tiles (2026-11-12).
- **Decision:** Popup opens anchored above the tray icon and cannot be moved.

### D-006 — Start with Windows via the HKCU Run registry value
- **Context:** Options: Startup-folder shortcut, HKCU Run key, Task Scheduler.
- **Decision:** HKCU `...\CurrentVersion\Run`, value `DisplayLocation`, respecting `StartupApproved` (Task Manager's enable/disable).
- **Consequences:** No admin; shows up in Task Manager → Startup apps where the owner can also disable it.

### D-007 — PyInstaller one-file, windowed exe; no installer
- **Decision:** `dist/DisplayLocation.exe`, built by `build.ps1`.
- **Consequences:** Slightly slower first start (unpacking). Some antivirus tools flag one-file PyInstaller exes; if that happens, switch to `--onedir` (new decision).

### D-008 — Keep the virtual environment and build temp files out of OneDrive
- **Context:** The project folder is synced by OneDrive; a venv and PyInstaller work folders contain thousands of files.
- **Decision:** venv at `%LOCALAPPDATA%\venvs\display-location`; PyInstaller `--workpath`/`--specpath` under `%LOCALAPPDATA%\DisplayLocation\build-tmp`. Only `dist/DisplayLocation.exe` is produced inside the project.

### D-009 — Python version: 3.14
- **Context:** Installed on the owner's PC (2026-11-12): Python 3.15 (default), 3.14, 3.11. PySide6 / pywin32 / PyInstaller wheels can lag behind the newest Python.
- **Decision:** Use the newest of 3.14 → 3.11 for which all three install from wheels and the app starts. Try 3.14 first.
- **Result (TASK-001, 2026-11-12):** **Python 3.14.10.** Wheel-only install worked: PySide6 6.12.0, pywin32 312, PyInstaller 6.22.3, pytest 9.2.0, Pillow 13.0.0. `requires-python = ">=3.14"`. 3.15 not tried, as the task says.

### D-010 — Single instance via `QLocalServer`
- **Decision:** A second launch signals the running instance to open its popup, then exits (FR-13). Chosen over a named mutex because it can also carry the "show" message.

### D-011 — Two monitors only in v1
- **Decision:** Exactly two active displays supported; other states show a message (FR-15).

### D-012 — No settings file in v1
- **Decision:** The only persisted setting is the autostart registry value. Add `%APPDATA%\DisplayLocation\settings.json` only when a real setting appears (new decision).

### D-013 — Exit during a revert countdown reverts
- **Decision:** Safe default: an unconfirmed change is undone on Exit (FR-16).

### D-014 — Duplicate mode is detected with `QueryDisplayConfig` (no fallback needed)
- **Context:** ARCHITECTURE §4.2 step 5 planned `QueryDisplayConfig(QDC_ONLY_ACTIVE_PATHS)` via `ctypes`, with a "report SINGLE" fallback if it proved unreliable (TASK-002).
- **Decision:** Use `QueryDisplayConfig`. When `EnumDisplayDevices` finds one attached desktop, count active paths against distinct `(adapter LUID, source id)` pairs. More paths than sources means DUPLICATE. Struct sizes were checked against wingdi.h (`DISPLAYCONFIG_PATH_INFO` 72 bytes, `DISPLAYCONFIG_MODE_INFO` 64).
- **Verified (2026-11-12, owner's PC):** Win+P → Duplicate gave 2 active paths on 1 source, so `status: duplicate`. One monitor alone gave 1 path, so `status: single`. If the query fails, the code logs a warning and reports SINGLE.
- **Consequences:** The FR-15 messages can tell "single" from "duplicate". In duplicate mode the one listed device may show the *other* monitor's friendly name. That's harmless, because no tiles are drawn in that state.

