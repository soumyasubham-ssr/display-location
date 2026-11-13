# Roadmap — Display Location

**Last Updated:** 2026-11-13
**Current version:** v1.0.0 built (TASK-001 … TASK-010 Done). Next: the QA session below.

Task files live in [tasks/](tasks/). Status values: `Todo` → `In progress` → `Done` (the task file is the source of truth; keep this table in sync).

## Milestones

### M1 — Foundation (no UI)
| Task | Title | Depends on | Status |
|---|---|---|---|
| TASK-001 | Project scaffold, environment, logging, entry point | — | Done |
| TASK-002 | Display backend: read and set monitor position + CLI | 001 | Done |
| TASK-003 | Snap and scale maths with unit tests | 001 | Done |

**Exit check:** `python -m display_location --list` prints both monitors; `--side left` really moves monitor 2; `pytest` green.

### M2 — Tray and popup
| Task | Title | Depends on | Status |
|---|---|---|---|
| TASK-004 | Tray icon, context menu, single instance, app icon | 001 | Done |
| TASK-005 | Popup window: look, position, open/close, status messages | 002, 003, 004 | Done |
| TASK-006 | Drag & snap tile 2, apply, Keep/Revert countdown | 005 | Done |

**Exit check:** owner can move monitor 2 to all four sides from the popup, and Revert/timeout restores the previous layout.

### M3 — System integration
| Task | Title | Depends on | Status |
|---|---|---|---|
| TASK-007 | Start with Windows toggle | 004 | Done |
| TASK-008 | Live refresh on monitor/layout changes | 005 | Done |
| TASK-009 | Identify displays overlay | 004, 002 | Done |

### M4 — Release
| Task | Title | Depends on | Status |
|---|---|---|---|
| TASK-010 | Build `DisplayLocation.exe` with PyInstaller | 001–009 | Done |
| — | **QA session** against REQUIREMENTS §6 (Role: QA) | 010 | Todo |

## Suggested order

001 → 002 → 003 → 004 → 005 → 006 → 007 → 008 → 009 → 010 → QA.
002 and 003 are independent and can be done in either order; 007 and 009 can start as soon as 004 is done.

## Later ideas (not planned, need owner decision)

- Global hotkeys (e.g. Ctrl+Alt+Arrow) to move monitor 2 without opening the popup.
- Saved layout presets ("Office", "Home").
- Support for three or more monitors.
- Dark/light theme following Windows.
- Installer / winget package.
