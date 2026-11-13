# TASK-010 — Build `DisplayLocation.exe` with PyInstaller

| Field | Value |
|---|---|
| Status | Todo |
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
- [ ] `.\build.ps1` succeeds on a clean checkout + venv.
- [ ] `dist\DisplayLocation.exe` runs with no console window; tray icon shows the app icon.
- [ ] All features work from the exe: popup, drag/apply/revert, identify, start with Windows, single instance (start exe twice).
- [ ] With Start with Windows enabled from the exe, sign out/in → icon appears within ~3 s of the desktop loading.
- [ ] Log file written to `%LOCALAPPDATA%\DisplayLocation\logs\app.log`.
- [ ] Exe size noted in CHANGELOG.

## Edge cases
- Antivirus/SmartScreen warning on first run of an unsigned one-file exe → document in README ("More info → Run anyway"); if Defender quarantines it, switch to `--onedir` and record a new decision.

## Out of scope
Installer, code signing, auto-update.

## Carried over from TASK-007 (2026-11-13)
Start with Windows can only be checked from a process **outside** the Claude desktop app, because Claude's packaged-app redirection hides HKCU writes from Task Manager. With the built `DisplayLocation.exe`, started by the owner:
- [ ] Toggle on → Task Manager → Startup apps lists DisplayLocation as Enabled.
- [ ] Disable it in Task Manager → the menu item shows unticked; tick it again → Enabled.
- [ ] Sign out and in with it enabled → the tray icon appears.
- [ ] Toggle off → the entry is removed.
Then mark TASK-007 Done.
