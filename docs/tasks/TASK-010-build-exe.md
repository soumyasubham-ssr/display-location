# TASK-010 — Build `DisplayLocation.exe` with PyInstaller

| Field | Value |
|---|---|
| Status | Done |
| Milestone | M4 — Release |
| Depends on | TASK-001 … TASK-009 |
| Requirements | NFR-03, NFR-05; decisions D-007, D-008 |
| Read first | `docs/ARCHITECTURE.md` §15, §8 (resource path) |

## What
Create `build.ps1` that produces a single windowed `dist\DisplayLocation.exe` with the app icon, and verify the exe end to end.

## Why
The owner wants a standalone exe that starts with Windows, without needing Python.

## Expected behaviour
- From the activated venv, `.\build.ps1` builds `dist\DisplayLocation.exe` (no console window, app icon in Explorer and tray).
- Double-clicking the exe gives the same behaviour as running from source.

## Affected files
- Create `build.ps1` (command per ARCHITECTURE §15, absolute paths, `--workpath`/`--specpath` outside OneDrive; fail with a clear message if the venv isn't active; print the exe path and size at the end).
- Edit `README.md` — final "Install / Build / Run" instructions, including copying the exe to a stable folder (e.g. `%LOCALAPPDATA%\Programs\DisplayLocation\`) **before** enabling Start with Windows.
- Edit `docs/ROADMAP.md` — statuses; `docs/CHANGELOG.md` — v1.0 entry.

## Implementation requirements
1. Bump `__version__` to `1.0.0` (and `pyproject.toml`).
2. Set exe version info (PyInstaller `--version-file`) with product name "Display Location" — optional but preferred.
3. Ensure `assets/icon.ico` is found inside the bundle via the resource helper from TASK-004.

## Acceptance criteria
- [x] `.\build.ps1` succeeds on a clean checkout + venv.
- [x] `dist\DisplayLocation.exe` runs with no console window; tray icon shows the app icon.
- [x] All features work from the exe: popup, drag/apply/revert, identify, start with Windows, single instance (start exe twice).
- [x] With Start with Windows enabled from the exe, sign out/in → icon appears within ~3 s of the desktop loading.
- [x] Log file written to `%LOCALAPPDATA%\DisplayLocation\logs\app.log`.
- [x] Exe size noted in CHANGELOG.

## Edge cases
- Antivirus/SmartScreen warning on first run of an unsigned one-file exe → document in README ("More info → Run anyway"); if Defender quarantines it, switch to `--onedir` and record a new decision.

## Out of scope
Installer, code signing, auto-update.

## Carried over from TASK-007 (2026-11-13)
Start with Windows can only be checked from a process **outside** the Claude desktop app, because Claude's packaged-app redirection hides HKCU writes from Task Manager. With the built `DisplayLocation.exe`, started by the owner:
- [x] Toggle on → Task Manager → Startup apps lists DisplayLocation as Enabled.
- [x] Disable it in Task Manager → the menu item shows unticked; tick it again → Enabled.
- [x] Sign out and in with it enabled → the tray icon appears.
- [x] Toggle off → the entry is removed.
Then mark TASK-007 Done.

## Completion notes (Coder, 2026-11-13)
- **`build.ps1`:** the ARCHITECTURE §15 command plus `--clean` and `--version-file`. It refuses to run without an active venv or without PyInstaller in it, and prints the exe path, size and version at the end.
  - **Version info** is generated from `__version__` into `build-tmp\version_info.txt` (ProductName/FileDescription "Display Location", MIT copyright). It is written as UTF-8 **without** a BOM, because Windows PowerShell 5.1's `Out-File -Encoding utf8` adds one.
  - **stderr:** PyInstaller logs to stderr, which PowerShell 5.1 turns into error records; with `$ErrorActionPreference = 'Stop'` that aborted the build. Native calls run through `Invoke-Native` (`Continue`) and are judged by `$LASTEXITCODE`.
- **Version 1.0.0** in `__init__.py`, `pyproject.toml` and `tests/test_smoke.py`. 166 tests pass.
- **Result:** `dist\DisplayLocation.exe`, **49 MB**, one file, windowed; Explorer version info reads "Display Location 1.0.0". PyInstaller 6.22.3, Python 3.14. `dist/` is git-ignored.
- **Smoke test from Claude (2026-11-13):** started the exe; log shows "Display Location 1.0.0 starting" and "Tray icon shown" with no "Icon not found" (so `assets/icon.ico` is found in the bundle). A second launch exited with code 0 and the first instance opened its popup. Memory: ~70 MB for the app plus ~10 MB for PyInstaller's launcher process.
  - That instance runs inside Claude's redirection, so it logs to Claude's copy of `%LOCALAPPDATA%` and its registry writes are invisible to Task Manager (see "Carried over from TASK-007").
- **README:** Install section (copy to `%LOCALAPPDATA%\Programs\DisplayLocation\` before enabling Start with Windows, SmartScreen "More info → Run anyway", log path, uninstall) and build notes.
- **Remaining (owner, exe double-clicked in Explorer — not started from Claude):** no console window and the app icon in the tray; popup, drag/apply/revert, identify, single instance; log at the real `%LOCALAPPDATA%\DisplayLocation\logs\app.log`; the four TASK-007 Start with Windows checks including sign out/in; SmartScreen/Defender behaviour.
- **Owner check (2026-11-13):** with the exe copied to `%LOCALAPPDATA%\Programs\DisplayLocation\` and double-clicked in Explorer, the owner reports all eight checks passed: no console window and the app icon in the tray, popup / drag / Keep / Revert / Identify, single instance, log in the real `%LOCALAPPDATA%`, and the four Start with Windows checks including sign out/in. Not visible from Claude's side (that instance logs to the real profile); acceptance rests on the owner's report.
