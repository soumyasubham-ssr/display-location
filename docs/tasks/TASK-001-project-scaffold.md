# TASK-001 — Project scaffold, environment, logging, entry point

| Field | Value |
|---|---|
| Status | Done (2026-11-12) |
| Milestone | M1 — Foundation |
| Depends on | — |
| Requirements | NFR-07; decisions D-002, D-008, D-009 |
| Read first | `docs/ARCHITECTURE.md` §1, §2, §14; `docs/DECISIONS.md` D-008, D-009 |

## What
Create the Python package skeleton, the virtual environment, dependency files, logging setup and a runnable entry point that starts an (empty) Qt application.

## Why
Every later task needs the package layout, a working environment with PySide6 + pywin32, and logging.

## Expected behaviour
- `python -m display_location` starts a Qt event loop with no visible window (tray comes in TASK-004), writes "Display Location <version> starting" to the log, and exits cleanly on Ctrl+C in the terminal.
- `python -m display_location --version` prints the version (`0.1.0`) and exits.

## Affected files (create)
- `pyproject.toml` — name `display-location`, version `0.1.0`, `requires-python`, dependencies `PySide6`, `pywin32`; src layout (`[tool.setuptools.packages.find] where = ["src"]`); `[tool.pytest.ini_options] testpaths = ["tests"]`, `pythonpath = ["src"]`.
- `requirements-dev.txt` — `pytest`, `pyinstaller`, `Pillow`.
- `src/display_location/__init__.py` — `__version__ = "0.1.0"`.
- `src/display_location/__main__.py` — argparse (`--version` now; `--list`, `--side` are added in TASK-002), then `from display_location.app import main; main()`. **Absolute imports only.**
- `src/display_location/app.py` — `main()`: set up logging, create `QApplication`, `app.setQuitOnLastWindowClosed(False)`, run the loop. Placeholder `AppController` class.
- `src/display_location/log_setup.py` — rotating file log at `%LOCALAPPDATA%\DisplayLocation\logs\app.log`, 1 MB × 3; also log to stderr when a console is attached; install `sys.excepthook` that logs uncaught exceptions.
- `tests/__init__.py` (empty) and `tests/test_smoke.py` — imports the package and checks `__version__`.
- `.gitignore` — `__pycache__/`, `*.pyc`, `dist/`, `build/`, `*.spec`, `.venv/`, `.pytest_cache/`.

## Implementation requirements
1. **Python version (D-009):** try `py -3.14 -m venv "%LOCALAPPDATA%\venvs\display-location"`, then `pip install -e . -r requirements-dev.txt`. If PySide6, pywin32 or PyInstaller fail to install from wheels, delete the venv and repeat with `py -3.11`. Do **not** use 3.15 unless all three install cleanly on it.
2. The venv must be **outside** the OneDrive project folder (D-008).
3. Set `requires-python` in `pyproject.toml` to match the version chosen.
4. Update `docs/DECISIONS.md` D-009: record the chosen version, set status to Accepted.
5. Update `README.md` "Development" section if any command differs from what is written.

## Acceptance criteria
- [x] venv exists at `%LOCALAPPDATA%\venvs\display-location` and `pip install -e . -r requirements-dev.txt` succeeds.
- [x] `python -c "import PySide6, win32api; print('ok')"` prints `ok`.
- [x] `python -m display_location --version` prints `0.1.0`.
- [x] `python -m display_location` runs and the log file is created with the start line.
- [x] `python -m pytest` passes.
- [x] D-009 updated.

## Edge cases
- `%LOCALAPPDATA%\DisplayLocation\logs` doesn't exist → create it.
- Running under `pythonw` (no console) → no stderr handler errors.

## Out of scope
Tray icon, display code, UI.

## Completion notes (Coder, 2026-11-12)
- Python **3.14.10** (D-009 Accepted). All wheels installed with `--only-binary`.
- Verified: `import PySide6, win32api` → `ok`; `--version` → `0.1.0`; app starts, logs `Display Location 0.1.0 starting`, idles with no window; `pytest` → 2 passed; Ctrl+C/Ctrl+Break → clean exit code 0 with an "exiting" log line; logging under `pythonw` works without a stderr handler.
- Added beyond the spec: SIGBREAK handled like SIGINT; `*.egg-info/` in `.gitignore` (made by `pip install -e .`).
- **Venv location caveat:** the Claude desktop app is a packaged (MSIX) app, so Windows redirected the venv this session created to `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Local\venvs\display-location`. In a normal terminal `%LOCALAPPDATA%\venvs\display-location` will not exist yet. Run the README "Development" commands once from your own PowerShell to create it at the real path. The log file is redirected the same way for runs started from Claude.
