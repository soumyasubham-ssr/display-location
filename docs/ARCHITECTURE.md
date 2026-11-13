# Architecture — Display Location

**Last Updated:** 2026-11-12
**Status:** Planned (no code yet). Coder updates this file when the implementation deviates.

Requirements are in [REQUIREMENTS.md](REQUIREMENTS.md) (FR-xx / NFR-xx). Reasons for choices are in [DECISIONS.md](DECISIONS.md) (D-xxx).

## 1. Tech stack

| Concern | Choice | Decision |
|---|---|---|
| Language | Python (version per D-009) | D-002, D-009 |
| UI, tray, popup, timers, single instance | **PySide6** (Qt 6) | D-002, D-010 |
| Reading/changing display positions | **pywin32** (`win32api`, `win32con`); `ctypes` only where pywin32 lacks an API | D-003 |
| Startup registration | `winreg` (standard library) | D-006 |
| Packaging | **PyInstaller** one-file, windowed | D-007 |
| Tests | **pytest** | — |

Runtime dependencies are only `PySide6` and `pywin32`. Dev dependencies: `pytest`, `pyinstaller`, `Pillow` (icon generation only).

## 2. Project layout

```
Display Location/
├─ CLAUDE.md                     AI workflow pointer
├─ README.md                     what it is, how to run/build
├─ pyproject.toml                package metadata, deps, pytest config
├─ requirements-dev.txt          dev tools (pytest, pyinstaller, pillow)
├─ build.ps1                     one-command exe build (TASK-010)
├─ assets/
│  ├─ icon-source.png            owner's artwork, the master for the icon (D-015)
│  └─ icon.ico                   app + tray icon (multi-size 16…256), generated
├─ tools/
│  └─ make_icon.py               regenerates assets/icon.ico from icon-source.png (Pillow)
├─ src/display_location/
│  ├─ __init__.py                __version__
│  ├─ __main__.py                entry point: CLI flags or start the tray app
│  ├─ app.py                     AppController: wires everything together
│  ├─ displays.py                Win32 display backend (ONLY place that changes displays)
│  ├─ layout.py                  pure snap / scale maths (no Qt, no Win32)
│  ├─ tray.py                    QSystemTrayIcon + context menu
│  ├─ popup.py                   popup window + arrangement canvas + revert bar
│  ├─ revert.py                  RevertManager (10 s keep/revert countdown)
│  ├─ identify.py                "Identify displays" overlays
│  ├─ autostart.py               HKCU Run key read/write
│  ├─ single_instance.py         QLocalServer/QLocalSocket guard
│  ├─ resources.py               finds assets/ from source or the PyInstaller bundle
│  └─ log_setup.py               rotating file logging
├─ tests/
│  ├─ test_layout.py             unit tests for layout.py (required)
│  ├─ test_autostart.py          registry tests using a temp value name
│  ├─ test_single_instance.py    second-launch and killed-instance tests (real processes)
│  ├─ test_tray.py               menu order, tooltip, signals
│  └─ conftest.py                one shared QApplication for all tests
└─ docs/                         shared project memory (this folder)
```

`dist/DisplayLocation.exe` is the build output. The venv and PyInstaller work folders live **outside** the project (D-008).

## 3. Components and data flow

```
            ┌──────────── AppController (app.py) ────────────┐
 tray click │                                                 │
 ─────────► TrayIcon ──open/toggle──► Popup ──drop(x,y)──► layout.snap()
            │   menu: Identify ─► IdentifyOverlay             │
            │         Start with Windows ─► autostart         ▼
            │         Exit                         DisplayService.set_position()
            │                                                 │
            │   RevertManager ◄── previous position ──────────┘
            │      keep / revert / timeout ─► DisplayService.set_position(previous)
            │                                                 │
            │   QGuiApplication screen signals ─► refresh Popup state
            └─────────────────────────────────────────────────┘
 second launch ─► SingleInstance (QLocalServer "show") ─► Popup.open()
```

- **AppController** owns one instance of each component, connects Qt signals, and holds no display logic itself.
- **RevertManager** is owned by the controller, not the popup, so the countdown keeps running after the popup closes (FR-07).
- **layout.py** is pure Python so it is fully unit-testable.

## 4. Display backend (`displays.py`)

### 4.1 Model

```python
@dataclass(frozen=True)
class Display:
    device_name: str      # r"\\.\DISPLAY1" (matches QScreen.name() on Windows)
    friendly_name: str    # monitor name from EnumDisplayDevices(device_name, 0).DeviceString
    x: int                # top-left in virtual-screen PHYSICAL pixels
    y: int
    width: int            # physical pixels (current mode)
    height: int
    is_primary: bool

class DisplayStatus(Enum):
    OK = "ok"                 # exactly two active, extended
    SINGLE = "single"
    DUPLICATE = "duplicate"
    TOO_MANY = "too_many"

@dataclass(frozen=True)
class DisplaySnapshot:
    status: DisplayStatus
    primary: Display | None
    secondary: Display | None
    all: tuple[Display, ...]

def snapshot() -> DisplaySnapshot
def set_position(device_name: str, x: int, y: int) -> None   # raises DisplayChangeError
```

### 4.2 Reading

1. Iterate `win32api.EnumDisplayDevices(None, i)` until it raises.
2. Keep devices where `StateFlags & DISPLAY_DEVICE_ATTACHED_TO_DESKTOP (0x1)`. Primary = `StateFlags & DISPLAY_DEVICE_PRIMARY_DEVICE (0x4)`.
3. For each, `win32api.EnumDisplaySettings(name, win32con.ENUM_CURRENT_SETTINGS)` → `Position_x`, `Position_y`, `PelsWidth`, `PelsHeight`.
4. Status: 1 attached → SINGLE; 2 → OK; >2 → TOO_MANY.
5. **Duplicate detection:** in duplicate (clone) mode Windows reports one attached desktop device for two monitors. Detect it with `QueryDisplayConfig(QDC_ONLY_ACTIVE_PATHS)` via `ctypes`: more active paths than distinct source IDs ⇒ DUPLICATE. If this proves unreliable, the fallback is to report SINGLE and use the combined message "Only one display is active (if two are connected, press Win+P → Extend)" — Coder records which was used in DECISIONS.

### 4.3 Writing

```python
dm = win32api.EnumDisplaySettings(name, win32con.ENUM_CURRENT_SETTINGS)
dm.Position_x, dm.Position_y = x, y
dm.Fields = win32con.DM_POSITION
rc = win32api.ChangeDisplaySettingsEx(name, dm,
        win32con.CDS_UPDATEREGISTRY | win32con.CDS_NORESET)
# also stage the primary at (0, 0) the same way (keeps Windows' layout consistent)
rc = win32api.ChangeDisplaySettingsEx()   # apply all staged changes
```

- Any return code other than `DISP_CHANGE_SUCCESSFUL (0)` → raise `DisplayChangeError(code, message)`.
- After applying, read back with `snapshot()`; if the secondary is not where requested (Windows may adjust), the controller uses the **read-back** position as truth.
- The primary always stays at (0, 0); the app never changes which monitor is primary.

### 4.4 CLI (debug / audit aid)

`python -m display_location --list` prints the snapshot as a table.
`python -m display_location --side right|left|top|bottom` moves the secondary to that side, centred, with **no** revert (developer use only; documented in README). It refuses (exit code 2) unless the status is `ok`.

Implemented in TASK-002. Duplicate detection uses `QueryDisplayConfig` (D-014). Since TASK-003, `--side` gets its centred position from `layout.placed()`.

## 5. Snap and scale maths (`layout.py`)

All values in physical pixels. Primary rectangle `P = (0, 0, Pw, Ph)`, secondary size `Sw × Sh`.

### 5.1 Side selection

Given the dropped secondary top-left `(x, y)`:

```
dx = (x + Sw/2) - Pw/2          dy = (y + Sh/2) - Ph/2
nx = dx / ((Pw + Sw) / 2)       ny = dy / ((Ph + Sh) / 2)
side = RIGHT if nx > 0 else LEFT   when |nx| >= |ny|   (tie → horizontal)
side = BOTTOM if ny > 0 else TOP   otherwise
```

### 5.2 Edge placement

| Side | x | y |
|---|---|---|
| RIGHT | `Pw` | `along(y, Sh, Ph)` |
| LEFT | `-Sw` | `along(y, Sh, Ph)` |
| BOTTOM | `along(x, Sw, Pw)` | `Ph` |
| TOP | `along(x, Sw, Pw)` | `-Sh` |

```
along(v, s, p):
    min_overlap = max(1, round(0.10 * min(s, p)))     # tiles must share ≥10 % of the shorter edge
    lo, hi = -s + min_overlap, p - min_overlap
    v = clamp(v, lo, hi)
    for c in (0, (p - s) / 2, p - s):                  # start-aligned, centred, end-aligned
        if lo <= c <= hi and abs(v - c) <= 0.05 * p:   # magnet threshold = 5 % of primary edge
            v = c; break                               # first match wins (start, centre, end)
    return round(v)
```

Constants `MIN_OVERLAP_RATIO = 0.10` and `MAGNET_RATIO = 0.05` live at the top of `layout.py`.

### 5.3 Side label

`describe(P, S_rect) -> str` e.g. "Right of 1", "Above 1 (centred)" for the popup footer.

### 5.4 Canvas scale

So tile sizes stay constant while dragging to any side:

```
scale = min(canvas_w / (Pw + 2*Sw), canvas_h / (Ph + 2*Sh)) * 0.95
primary tile is centred in the canvas; secondary tile = its physical rect × scale, offset by the primary tile's origin
```

`to_canvas()` / `from_canvas()` helpers convert between physical and canvas coordinates.

### 5.5 Implementation notes (TASK-003)

- **Rounding:** every rounding step rounds half up (`floor(v + 0.5)`), not with Python's `round()`. `round()` rounds halves to the nearest even number, so whether "centred" matched would depend on the parity of `(p - s)`.
- **Extra helpers:** `placed(pw, ph, sw, sh, side, align)` gives the start-aligned, centred or end-aligned top-left, and `--side` uses it. `canvas_origin(cw, ch, pw, ph, scale)` gives the canvas point for physical (0, 0) with the primary tile centred, for TASK-005.
- **`describe` with equal edge lengths:** start, centre and end are then the same position, and the label says "(centred)".
- **`canvas_scale`:** never returns less than `1e-6`, so a zero-size canvas can't cause a division by zero.

## 6. Popup (`popup.py`)

- **Window flags:** `Qt.Popup | Qt.FramelessWindowHint`, `WA_TranslucentBackground`. `Qt.Popup` gives "close on outside click" for free (FR-05). Esc handled in `keyPressEvent`.
- **Look:** custom `paintEvent` draws a rounded rectangle (radius 12, background `#202020`, 1 px border `#3a3a3a`) with a `QGraphicsDropShadowEffect` on the inner frame. Tile 1: `#2d2d2d`, tile 2: accent `#a64dbf` (purple, as in the owner's screenshot); hover/drag: lighter accent. Numbers in Segoe UI, ~28 pt, white. Font: Segoe UI Variable if available, else Segoe UI.
- **Layout:** title "Display arrangement" (top-left, small), canvas (middle), footer label (FR-03), revert bar (hidden by default, FR-07), inline error label (FR-09), or the status message instead of the canvas (FR-15).
- **Positioning (FR-04):** `tray.geometry()` (logical px). Place the popup so its bottom edge is 8 px above the tray icon's top and it is horizontally centred on the icon, then clamp into `primaryScreen().availableGeometry()` with an 8 px margin. If `geometry()` is empty/invalid → bottom-right of the available geometry.
- **Toggle race:** clicking the tray icon while the popup is open first closes the popup (outside click) and then fires `activated`. The popup records the time it closed; if the tray activation arrives within 300 ms of that, the controller does **not** reopen it.
- **As built (TASK-005):** the window is the 360 × 240 panel plus a transparent 14 px shadow margin. `popup_position()` is a pure function (tested). It uses the screen under the tray icon (fallback primary), and opens *below* the icon when there is no room above (taskbar at the top). `AppController.toggle_popup(open_only)` holds the 300 ms guard (`TOGGLE_GUARD_S`); `open_only` (menu Open, second launch) never closes and skips the guard. Revert bar and error label exist hidden for TASK-006.
- **Drag:** `mousePressEvent` on tile 2 → dragging; `mouseMoveEvent` moves the tile freely; `mouseReleaseEvent` → `from_canvas` → `layout.snap` → animate tile (QPropertyAnimation, 120 ms) to the snapped canvas position → emit `positionChosen(x, y)`. During the countdown, tile dragging stays enabled; a new drop applies a new position and restarts the countdown **with the original pre-change position kept as the revert target**.

## 7. Revert manager (`revert.py`)

**As built (TASK-006):** `RevertManager(set_position)` takes the display call as a parameter, so tests use a fake. `start(device_name, previous)` stores the device too. `cancel(reason)` stops without reverting when the monitor has gone; it emits `finished(True)`. `revert_failed(str)` reports a revert that Windows rejected. The crash path is `log_setup.crash_handler`, set by the controller. The popup's bottom row has a fixed height and shows one of: error, then revert bar, then footer.

- `start(previous: tuple[int, int])`: if no countdown is running, store `previous`; (re)start a 1 s `QTimer`, 10 ticks. Emits `tick(seconds_left)`, `finished(kept: bool)`.
- `keep()`: stop, clear stored position, emit `finished(True)`.
- `revert()` / timeout: `DisplayService.set_position(secondary, *previous)`, stop, emit `finished(False)`.
- On app Exit while running → `revert()` first (D-013).

## 8. Tray (`tray.py`)

- `QSystemTrayIcon` with `assets/icon.ico` (loaded via a resource-path helper that works both from source and inside the PyInstaller bundle: `sys._MEIPASS`).
- `activated(Trigger)` → controller toggles popup. `Context` → menu (FR-10). Menu items rebuilt / re-checked on `aboutToShow` so "Start with Windows" reflects the registry (FR-12).
- **As built (TASK-004):** `TrayIcon` only emits signals (`toggle_requested`, `open_requested`, `identify_requested`, `autostart_toggled`, `exit_requested`). `AppController` connects them. On `aboutToShow`, the menu asks `tray.autostart_state()`, which returns True/False, or None meaning "not available" (the item is then greyed out). TASK-007 replaces that callable.
- **Quit path:** every quit goes through `QApplication.aboutToQuit` → `AppController.before_exit()`, which runs once. This covers menu Exit, Ctrl+C and anything else that quits. TASK-006 adds the revert-on-exit to that hook (FR-16).
- **Tray not ready at start** (e.g. Explorer is starting): retry every 2 s, give up after 30 s with exit code 1.
- New tray icons land in the taskbar's **^ overflow** until the user drags them out. `tray.geometry()` then reports the ^ button's rectangle, which is still a good anchor for the popup (§6).

## 9. Identify (`identify.py`)

For each `Display`, find the `QScreen` whose `name()` equals `device_name`; show a frameless, translucent, always-on-top, click-through window centred on that screen with the number (1 = primary, 2 = secondary) at ~120 pt for 3 s.

## 10. Autostart (`autostart.py`)

- Key: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, value name **`DisplayLocation`**.
- Command: frozen exe → `"<sys.executable>"`; from source → `"<pythonw.exe>" -m display_location` (requires `pip install -e .`).
- `is_enabled()`: Run value exists **and** is not disabled in `HKCU\...\Explorer\StartupApproved\Run` (value `DisplayLocation`, first byte `0x03` = disabled by user in Task Manager).
- `enable()`: write the Run value and delete any `StartupApproved` value for it. `disable()`: delete the Run value.

**As built (TASK-007):** all functions take an optional `AutostartKeys` so tests use `HKCU\Software\DisplayLocation-pytest`. "Disabled" means an odd first byte in StartupApproved (0x03 / 0x07). `refresh_stale_path()` runs at start in the packaged exe only.

## 11. Single instance (`single_instance.py`)

Server name `DisplayLocation-<USERNAME>`. At start: `QLocalSocket.connectToServer`; if connected within 300 ms → send `b"show"` → exit with code 0. Otherwise `QLocalServer.removeServer(name)` then `listen(name)`; incoming `show` → controller opens popup (FR-13).

The check runs right after `QApplication` is created and before the icon or tray exists. `<USERNAME>` is cleaned to `[A-Za-z0-9_.-]`. Testing note: from a venv, `python.exe` is a launcher that starts the real interpreter as a child. When the launcher is killed, the child dies a moment later, so a test that restarts straight away must wait for the old server to go.

## 12. Display change handling (FR-14)

Connect `QGuiApplication.screenAdded`, `screenRemoved`, `primaryScreenChanged` and every screen's `geometryChanged` to a debounced (250 ms) `refresh()` that calls `displays.snapshot()` and updates the popup. No polling (NFR-02). If a revert countdown is running and the secondary disappears, the countdown is cancelled (nothing to revert) and logged.

**As built (TASK-008):** `AppController._watch_screens()` / `on_displays_changed()`, debounce `DISPLAY_DEBOUNCE_MS`. A snapshot equal to the one already shown is ignored (our own `set_position` read-back), so it never re-applies or restarts the countdown. During a drag, snap animation or apply the refresh re-arms the timer and runs afterwards. It also runs with the popup closed, so the countdown is cancelled when monitor 2 goes even then. The countdown is also cancelled when its monitor becomes the primary (Windows refuses to move a primary).

## 13. DPI

Qt 6 runs per-monitor-DPI-aware (v2) by default, so `EnumDisplaySettings` returns physical pixels and positions are consistent. Do **not** set `QT_ENABLE_HIGHDPI_SCALING=0`. All maths in `layout.py` uses physical pixels; only the canvas uses logical pixels.

## 14. Logging and errors

`log_setup.py` configures a `RotatingFileHandler` (NFR-07). `sys.excepthook` logs uncaught exceptions; if a revert countdown is active it attempts the revert (NFR-06). Logged events: startup/shutdown, snapshot on popup open, every position change (from → to, result code), revert/keep, autostart changes, errors.

## 15. Build (TASK-010)

`build.ps1`:

```
$root = $PSScriptRoot
pyinstaller --noconfirm --onefile --windowed --name DisplayLocation `
  --icon "$root\assets\icon.ico" --add-data "$root\assets\icon.ico;assets" `
  --distpath "$root\dist" `
  --workpath "$env:LOCALAPPDATA\DisplayLocation\build-tmp" `
  --specpath "$env:LOCALAPPDATA\DisplayLocation\build-tmp" `
  --paths "$root\src" "$root\src\display_location\__main__.py"
```

`__main__.py` must use **absolute** imports (`from display_location.app import main`): PyInstaller runs it as a top-level script, where relative imports fail.

Use **absolute** paths: with `--specpath` outside the project, PyInstaller resolves relative paths against the spec folder. Output: `dist/DisplayLocation.exe`.
