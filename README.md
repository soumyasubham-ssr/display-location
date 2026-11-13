# Display Location

A small Windows 11 tray app to move your **second monitor** to the left, right, top or bottom of your main monitor — by dragging a tile in a compact popup, like the arrangement view in Windows Settings.

> **Status:** v1.0.0 — all features built. See [docs/ROADMAP.md](docs/ROADMAP.md).

## Features (v1)

- Tray icon; left-click opens a dark, rounded popup above the tray.
- Drag monitor **2** around monitor **1**; it snaps to the nearest side and applies instantly.
- "Keep / Revert (10 s)" safety bar after each change.
- Right-click menu: Open, Identify displays, Start with Windows, Exit.
- Single `DisplayLocation.exe`, no admin rights needed.

Full list: [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md).

## Install

1. Build the exe (see **Development** below), or take `DisplayLocation.exe` from someone who built it.
2. Copy it to a folder that won't move, **before** you turn on Start with Windows:
   ```powershell
   New-Item -ItemType Directory -Force "$env:LOCALAPPDATA\Programs\DisplayLocation" | Out-Null
   Copy-Item .\dist\DisplayLocation.exe "$env:LOCALAPPDATA\Programs\DisplayLocation\"
   ```
   If you move it later, start the exe from its new place once: it repoints the startup entry itself.
3. Double-click `DisplayLocation.exe`. The icon appears in the tray (look under the **^** arrow and drag it onto the taskbar to keep it visible).
4. Right-click the icon → **Start with Windows** to start it at sign-in.

The exe is not code-signed. On first run Windows SmartScreen may say "Windows protected your PC": click **More info → Run anyway**. No admin rights are needed.

Log file: `%LOCALAPPDATA%\DisplayLocation\logs\app.log`.

To uninstall: untick Start with Windows, Exit from the tray menu, and delete the folder.

## Related setup (not part of this app)

Per-monitor taskbars and keeping monitor 2 fixed across virtual desktops are handled with [Windhawk](https://windhawk.net/mods) mods — *Independent taskbar per monitor* and *Secondary Monitor Pin* (see [docs/DECISIONS.md](docs/DECISIONS.md) D-001).

## Development

Python **3.14** (D-009). Run these from your own PowerShell, not from inside the Claude desktop app (it is a packaged app, and Windows redirects `%LOCALAPPDATA%` for anything it starts).

```powershell
# one-time: venv outside OneDrive (D-008)
py -3.14 -m venv "$env:LOCALAPPDATA\venvs\display-location"
& "$env:LOCALAPPDATA\venvs\display-location\Scripts\Activate.ps1"
pip install -e . -r requirements-dev.txt

python -m display_location          # run the tray app
python -m display_location --list   # print monitors (debug)
python -m display_location --side left   # dev only: move monitor 2 left/right/top/bottom, centred, NO revert
python -m pytest                    # tests
.\build.ps1                         # build dist\DisplayLocation.exe (one file, ~49 MB)
```

`build.ps1` needs the venv active. PyInstaller's work folders go to `%LOCALAPPDATA%\DisplayLocation\build-tmp` (outside OneDrive, D-008); only `dist\DisplayLocation.exe` lands in the project. The version comes from `src\display_location\__init__.py`.

## Docs

| File | What |
|---|---|
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | What the app must do |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | How it is built |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Why |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Milestones and task order |
| [docs/tasks/](docs/tasks/) | Executable task files |
| [docs/AI_WORKFLOW.md](docs/AI_WORKFLOW.md) | AI role workflow settings |

## License

[MIT](LICENSE)
