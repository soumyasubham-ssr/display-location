# TASK-007 — Start with Windows toggle

| Field | Value |
|---|---|
| Status | Done |
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
- [x] Toggle on → value present in `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`; Task Manager → Startup apps lists "DisplayLocation" as Enabled.
- [x] Toggle off → value removed.
- [x] Disable in Task Manager → menu shows unchecked; re-check → enabled again in Task Manager.
- [x] Sign out/in (or reboot) with it enabled → tray icon appears (verify with the packaged exe after TASK-010).
- [x] `python -m pytest` passes and leaves no test values in the registry.

## Edge cases
- Exe moved to another folder after enabling → `is_enabled()` returns true but the path is stale; on start, if enabled and the stored path ≠ current exe path, rewrite it (log it).

## Out of scope
Installer, Task Scheduler.

## Completion notes (Coder, 2026-11-12)
- **New files:** `src/display_location/autostart.py` and `tests/test_autostart.py` (16 tests).
  - `autostart.py` has `command()`, `is_enabled()`, `enable()`, `disable()`, `set_enabled()`, `stored_command()`, `disabled_in_task_manager()` and `refresh_stale_path()`. Every function takes an optional `AutostartKeys(run, approved, value_name)`; the default is the real keys from ARCHITECTURE §10.
- **Tests never touch the real Run key (a change from the task text).** They use a throwaway key, `HKCU\Software\DisplayLocation-pytest\{Run, StartupApproved\Run}`, and delete the whole key afterwards. Reason: a test value in the real Run key is still a startup entry, and Claude's own sandbox refused that write.
- **StartupApproved:** an odd first byte (0x03, also 0x07) means disabled; even (0x02 / 0x06) means enabled. That's slightly broader than "0x03" in §10, because Windows uses both pairs. `enable()` deletes the StartupApproved value, so re-checking the item re-enables it.
- **Stale path:** `AppController.start()` calls `refresh_stale_path()`. It rewrites the value only in the **packaged exe** (`sys.frozen`), only when the entry is enabled and not disabled in Task Manager, and only when the stored path differs. From source it never rewrites, so a dev run can't repoint the exe's entry at Python.
- **app.py:** `autostart_state()` (re-read on every menu open; a registry error gives None, which greys the item out) and `set_autostart()` (errors are logged). Every enable / disable is logged with the command written.
- **Verified:** 141 tests pass; no `DisplayLocation-pytest` key is left; the real value is untouched (off).
- **Caveat for testing from source:** the Claude desktop app redirects `%LOCALAPPDATA%` (README), and the venv `pythonw.exe` path only exists inside that redirect. An entry enabled from a source run launched by Claude would point to a path that Windows can't find at sign-in. The sign-in check therefore waits for the exe (TASK-010), as the acceptance list already says.
- **Owner check from a Claude-launched app (2026-11-13):**
  - Ticking the item wrote the value: the log shows "Start with Windows enabled: …pythonw.exe -m display_location", and the app read it back as enabled.
  - **Task Manager did not list it.** Anything started from inside the Claude desktop app (a packaged app) writes HKCU to Claude's private registry copy, not the real one.
  - The owner unticked the item and exited; afterwards `is_enabled()` was False and nothing was stored.
- **Remaining checks (with `DisplayLocation.exe` started by the owner outside Claude, after TASK-010):**
  - Toggle on → listed as Enabled in Task Manager;
  - disable in Task Manager → menu unticked;
  - re-tick → Enabled;
  - sign in with it enabled → tray icon appears;
  - toggle off → removed.
- **Closed (2026-11-13):** the remaining checks were run with the packaged exe in TASK-010 and passed (owner report).
