# Changelog — Display Location

Notable changes to docs, decisions and the app. Newest first.

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
