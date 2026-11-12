# TASK-007 — Start with Windows toggle

| Field | Value |
|---|---|
| Status | Todo |
| Milestone | M3 — System integration |
| Depends on | TASK-004 |
| Requirements | FR-10 (menu item), FR-12; decision D-006 |
| Read first | `docs/ARCHITECTURE.md` §10 |

## What
Implement `src/display_location/autostart.py` and connect it to the "Start with Windows" checkable tray-menu item.

## Why
The owner wants the app available automatically after login.

## Expected behaviour
- Menu item shows a check mark if and only if the app is set to start with Windows (re-read on every menu open).
- Clicking toggles it. Default (never toggled) = off.
- When enabled from the exe, the Run value is `"C:\...\DisplayLocation.exe"`. When enabled while running from source, it is `"<venv>\Scripts\pythonw.exe" -m display_location`.
- If the owner disables it in Task Manager → Startup apps, the menu shows it unchecked; checking it again re-enables it.

## Affected files
- Create `src/display_location/autostart.py` (`is_enabled()`, `enable()`, `disable()`, `command()`).
- Edit `src/display_location/tray.py` / `app.py` (wire the menu item).
- Create `tests/test_autostart.py` — exercise the functions with a **test value name** (e.g. `DisplayLocation-pytest`, parametrised in the module) and clean up afterwards; never touch the real `DisplayLocation` value in tests.

## Implementation requirements
1. Registry keys and StartupApproved handling exactly as ARCHITECTURE §10 (`0x03` first byte = disabled).
2. Use `winreg` only.
3. Log every enable/disable with the command written.

## Acceptance criteria
- [ ] Toggle on → value present in `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`; Task Manager → Startup apps lists "DisplayLocation" as Enabled.
- [ ] Toggle off → value removed.
- [ ] Disable in Task Manager → menu shows unchecked; re-check → enabled again in Task Manager.
- [ ] Sign out/in (or reboot) with it enabled → tray icon appears (verify with the packaged exe after TASK-010).
- [ ] `python -m pytest` passes and leaves no test values in the registry.

## Edge cases
- Exe moved to another folder after enabling → `is_enabled()` returns true but the path is stale; on start, if enabled and the stored path ≠ current exe path, rewrite it (log it).

## Out of scope
Installer, Task Scheduler.
