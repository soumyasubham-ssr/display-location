# Display Location

A small Windows 11 tray app to move your **second monitor** to the left, right, top or bottom of your main monitor — by dragging a tile in a compact popup, like the arrangement view in Windows Settings.

> **Status:** planning complete, not built yet. See [docs/ROADMAP.md](docs/ROADMAP.md).

## Features (v1)

- Tray icon; left-click opens a dark, rounded popup above the tray.
- Drag monitor **2** around monitor **1**; it snaps to the nearest side and applies instantly.
- "Keep / Revert (10 s)" safety bar after each change.
- Right-click menu: Open, Identify displays, Start with Windows, Exit.
- Single `DisplayLocation.exe`, no admin rights needed.

Full list: [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md).

## Related setup (not part of this app)

Per-monitor taskbars and keeping monitor 2 fixed across virtual desktops are handled with [Windhawk](https://windhawk.net/mods) mods — *Independent taskbar per monitor* and *Secondary Monitor Pin* (see [docs/DECISIONS.md](docs/DECISIONS.md) D-001).

## Development

Python **3.14** (D-009). Run these from your own PowerShell, not from inside the Claude desktop app (it is a packaged app, and Windows redirects `%LOCALAPPDATA%` for anything it starts). `--list` arrives in TASK-002 and `build.ps1` in TASK-010.

```powershell
# one-time: venv outside OneDrive (D-008)
py -3.14 -m venv "$env:LOCALAPPDATA\venvs\display-location"
& "$env:LOCALAPPDATA\venvs\display-location\Scripts\Activate.ps1"
pip install -e . -r requirements-dev.txt

python -m display_location          # run the tray app
python -m display_location --list   # print monitors (debug)
python -m pytest                    # tests
.\build.ps1                         # build dist\DisplayLocation.exe
```

## Docs

| File | What |
|---|---|
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | What the app must do |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | How it is built |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Why |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Milestones and task order |
| [docs/tasks/](docs/tasks/) | Executable task files |
| [docs/AI_WORKFLOW.md](docs/AI_WORKFLOW.md) | AI role workflow settings |
