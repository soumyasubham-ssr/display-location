# Changelog — Display Location

Notable changes to docs, decisions and the app. Newest first.

## 2026-11-13
- **Repo:** README rewritten for GitHub (logo, badges, screenshots, how it works, download link, install). Screenshots are rendered from the real widgets by `tools/make_screenshots.py` into `docs/images/`. v1.0.0 published as a GitHub release with `DisplayLocation.exe` attached.
- **Docs (audit):** ARCHITECTURE status and test list brought up to date; AI_WORKFLOW no longer says the project isn't a git repo; ROADMAP shows v1.0.0 built. Recorded one known deviation: a 200 ms Ctrl+C wake-up timer runs all the time (NFR-02 says no polling; idle CPU still ≈ 0 %).
- **Release:** v1.0.0. TASK-010 done: `build.ps1` builds `dist\DisplayLocation.exe` (one file, windowed, **49 MB**, version info "Display Location 1.0.0"). Smoke-tested (icon, single instance). README has install steps. Owner checked the exe outside Claude: all OK, which also closes TASK-007 (Start with Windows, sign out/in).
- **App:** TASK-009 done. "Identify displays" shows a big 1 / 2 on each monitor for 3 s (`identify.py`), click-through and without taking focus. 166 tests. Owner checked it on the real monitors: all OK.
- **App:** TASK-008 done. The popup follows display changes made outside the app (screen signals, 250 ms debounce, no polling), waits for an active drag, and cancels the countdown when monitor 2 goes or becomes the primary. 153 tests. Owner checked it on the real monitors: all OK.

## 2026-11-12
- **App:** TASK-007 code done (in review). The Start with Windows menu item reads and writes the HKCU Run key (`autostart.py`) and respects a disable in Task Manager. Tests use a throwaway registry key. 141 tests.
- **App:** TASK-006 done. Drag and snap tile 2, apply, a 10 s Keep/Revert countdown (`revert.py`), the inline error, and revert on Exit and on a crash. 125 tests. Checked by script on the real displays. Owner checked it with the real mouse: all OK.
- **App:** TASK-005 done. Popup window with the arrangement canvas, FR-15 status messages, positioning above the tray icon and the 300 ms toggle guard. 104 tests. Owner checked it on the real tray: all OK.
- **App:** TASK-004 done. Tray icon and menu, single instance (`QLocalServer`), resource-path helper, and an app icon built from the owner's artwork (new decision D-015). 85 tests.
- **App:** TASK-003 done. `layout.py` has the snap, describe and canvas maths, with 66 unit tests. `--side` now uses `layout.placed()`. M1 Foundation is complete.
- **App:** TASK-002 done. `displays.py` Win32 backend (`snapshot`, `set_position`, duplicate detection), plus the `--list` / `--side` CLI. Verified on the owner's two monitors. New decision D-014 (duplicate detection via `QueryDisplayConfig`).
- **App:** TASK-001 done. Package scaffold (`pyproject.toml`, `src/display_location/`, rotating log, Qt entry point, smoke tests), Python 3.14 venv. D-009 Accepted (Python 3.14).
- **Docs:** Project set up with the role workflow ([AI_WORKFLOW.md](AI_WORKFLOW.md)). Manager wrote [REQUIREMENTS.md](REQUIREMENTS.md), [ARCHITECTURE.md](ARCHITECTURE.md), [DECISIONS.md](DECISIONS.md) (D-001 … D-013), [ROADMAP.md](ROADMAP.md), and the README.
- **Scope:** Independent taskbars / per-monitor desktops moved to Windhawk mods (D-001); this app only repositions the second monitor.
- **Tasks:** Tasker created TASK-001 … TASK-010.
