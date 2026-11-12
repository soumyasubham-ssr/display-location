"""Win32 display backend — the ONLY module that reads or changes display positions.

All coordinates are virtual-screen *physical* pixels (ARCHITECTURE §4, §13).
No Qt imports here.
"""

from __future__ import annotations

import ctypes
import logging
from ctypes import wintypes
from dataclasses import dataclass
from enum import Enum

import pywintypes
import win32api
import win32con

log = logging.getLogger("display_location.displays")

DISPLAY_DEVICE_ATTACHED_TO_DESKTOP = 0x1
DISPLAY_DEVICE_PRIMARY_DEVICE = 0x4


# --------------------------------------------------------------------------- model


@dataclass(frozen=True)
class Display:
    device_name: str  # r"\\.\DISPLAY1" (matches QScreen.name() on Windows)
    friendly_name: str  # monitor name, e.g. "DELL P2419H"
    x: int  # top-left in virtual-screen physical pixels
    y: int
    width: int  # physical pixels (current mode)
    height: int
    is_primary: bool


class DisplayStatus(Enum):
    OK = "ok"  # exactly two active, extended
    SINGLE = "single"
    DUPLICATE = "duplicate"
    TOO_MANY = "too_many"


@dataclass(frozen=True)
class DisplaySnapshot:
    status: DisplayStatus
    primary: Display | None
    secondary: Display | None
    all: tuple[Display, ...]


_DISP_CHANGE_MESSAGES = {
    win32con.DISP_CHANGE_RESTART: "The computer must be restarted for the change to take effect",
    win32con.DISP_CHANGE_FAILED: "The display driver failed the requested change",
    win32con.DISP_CHANGE_BADMODE: "The display mode is not supported",
    win32con.DISP_CHANGE_NOTUPDATED: "Unable to write the settings to the registry",
    win32con.DISP_CHANGE_BADFLAGS: "An invalid set of flags was passed",
    win32con.DISP_CHANGE_BADPARAM: "An invalid parameter was passed",
    getattr(win32con, "DISP_CHANGE_BADDUALVIEW", -6): "The change failed because the system is DualView capable",
}


class DisplayChangeError(Exception):
    """Windows rejected a display change. ``code`` is the DISP_CHANGE_* value (or None)."""

    def __init__(self, code: int | None, message: str) -> None:
        super().__init__(message if code is None else f"{message} (code {code})")
        self.code = code
        self.message = message


def _check(rc: int, step: str) -> None:
    if rc != win32con.DISP_CHANGE_SUCCESSFUL:
        msg = _DISP_CHANGE_MESSAGES.get(rc, "Unknown display change error")
        raise DisplayChangeError(rc, f"{step}: {msg}")


# --------------------------------------------------------------------------- reading


def _enum_attached() -> list[Display]:
    displays: list[Display] = []
    i = 0
    while True:
        try:
            dev = win32api.EnumDisplayDevices(None, i)
        except pywintypes.error:
            break
        i += 1
        if not dev.StateFlags & DISPLAY_DEVICE_ATTACHED_TO_DESKTOP:
            continue  # disconnected / inactive adapter output
        try:
            mode = win32api.EnumDisplaySettings(dev.DeviceName, win32con.ENUM_CURRENT_SETTINGS)
        except pywintypes.error:
            log.warning("No current settings for %s; skipped", dev.DeviceName)
            continue
        try:
            friendly = win32api.EnumDisplayDevices(dev.DeviceName, 0).DeviceString
        except pywintypes.error:
            friendly = ""
        displays.append(
            Display(
                device_name=dev.DeviceName,
                friendly_name=friendly or dev.DeviceString,
                x=mode.Position_x,
                y=mode.Position_y,
                width=mode.PelsWidth,
                height=mode.PelsHeight,
                is_primary=bool(dev.StateFlags & DISPLAY_DEVICE_PRIMARY_DEVICE),
            )
        )
    return displays


# QueryDisplayConfig structures (wingdi.h) — only what duplicate detection needs.
class _LUID(ctypes.Structure):
    _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]


class _PATH_SOURCE_INFO(ctypes.Structure):
    _fields_ = [
        ("adapterId", _LUID),
        ("id", ctypes.c_uint32),
        ("modeInfoIdx", ctypes.c_uint32),
        ("statusFlags", ctypes.c_uint32),
    ]


class _RATIONAL(ctypes.Structure):
    _fields_ = [("Numerator", ctypes.c_uint32), ("Denominator", ctypes.c_uint32)]


class _PATH_TARGET_INFO(ctypes.Structure):
    _fields_ = [
        ("adapterId", _LUID),
        ("id", ctypes.c_uint32),
        ("modeInfoIdx", ctypes.c_uint32),
        ("outputTechnology", ctypes.c_uint32),
        ("rotation", ctypes.c_uint32),
        ("scaling", ctypes.c_uint32),
        ("refreshRate", _RATIONAL),
        ("scanLineOrdering", ctypes.c_uint32),
        ("targetAvailable", wintypes.BOOL),
        ("statusFlags", ctypes.c_uint32),
    ]


class _PATH_INFO(ctypes.Structure):
    _fields_ = [
        ("sourceInfo", _PATH_SOURCE_INFO),
        ("targetInfo", _PATH_TARGET_INFO),
        ("flags", ctypes.c_uint32),
    ]


class _MODE_INFO(ctypes.Structure):
    _fields_ = [
        ("infoType", ctypes.c_uint32),
        ("id", ctypes.c_uint32),
        ("adapterId", _LUID),
        ("info", ctypes.c_byte * 48),  # union; contents not needed
    ]


QDC_ONLY_ACTIVE_PATHS = 0x2
_ERROR_SUCCESS = 0
_ERROR_INSUFFICIENT_BUFFER = 122


def _active_paths() -> list[tuple[tuple[int, int, int], int]] | None:
    """Return ((adapter low, adapter high, source id), target id) per active path, or None on failure."""
    try:
        user32 = ctypes.WinDLL("user32")
    except OSError:
        return None
    n_paths, n_modes = ctypes.c_uint32(), ctypes.c_uint32()
    for _ in range(3):  # topology can change between the two calls
        rc = user32.GetDisplayConfigBufferSizes(
            QDC_ONLY_ACTIVE_PATHS, ctypes.byref(n_paths), ctypes.byref(n_modes)
        )
        if rc != _ERROR_SUCCESS:
            log.warning("GetDisplayConfigBufferSizes failed: %s", rc)
            return None
        paths = (_PATH_INFO * n_paths.value)()
        modes = (_MODE_INFO * n_modes.value)()
        rc = user32.QueryDisplayConfig(
            QDC_ONLY_ACTIVE_PATHS,
            ctypes.byref(n_paths),
            paths,
            ctypes.byref(n_modes),
            modes,
            None,
        )
        if rc == _ERROR_INSUFFICIENT_BUFFER:
            continue
        if rc != _ERROR_SUCCESS:
            log.warning("QueryDisplayConfig failed: %s", rc)
            return None
        result = []
        for p in paths[: n_paths.value]:
            s = p.sourceInfo
            result.append(((s.adapterId.LowPart, s.adapterId.HighPart, s.id), p.targetInfo.id))
        return result
    return None


def _is_duplicated() -> bool:
    """True when two or more active monitors share one desktop source (Win+P → Duplicate)."""
    paths = _active_paths()
    if not paths:
        return False
    sources = {src for src, _ in paths}
    return len(paths) > len(sources)


def snapshot() -> DisplaySnapshot:
    """Read the current display layout."""
    displays = tuple(_enum_attached())
    primary = next((d for d in displays if d.is_primary), None)
    others = [d for d in displays if not d.is_primary]

    if len(displays) > 2:
        status = DisplayStatus.TOO_MANY
    elif len(displays) == 2:
        status = DisplayStatus.OK
    elif _is_duplicated():
        status = DisplayStatus.DUPLICATE
    else:
        status = DisplayStatus.SINGLE

    secondary = others[0] if status is DisplayStatus.OK and others else None
    return DisplaySnapshot(status=status, primary=primary, secondary=secondary, all=displays)


# --------------------------------------------------------------------------- writing


def _stage(device_name: str, x: int, y: int) -> int:
    dm = win32api.EnumDisplaySettings(device_name, win32con.ENUM_CURRENT_SETTINGS)
    dm.Position_x, dm.Position_y = x, y
    dm.Fields = win32con.DM_POSITION
    return win32api.ChangeDisplaySettingsEx(
        device_name, dm, win32con.CDS_UPDATEREGISTRY | win32con.CDS_NORESET
    )


def set_position(device_name: str, x: int, y: int) -> None:
    """Move display ``device_name`` so its top-left is at (x, y); the primary stays at (0, 0).

    Raises ``DisplayChangeError`` if Windows rejects the change. Windows may adjust the
    requested position (e.g. to close a gap), so callers must read back the real position
    with ``snapshot()`` and treat that as the truth.
    """
    before = snapshot()
    target = next((d for d in before.all if d.device_name == device_name), None)
    if target is None:
        raise DisplayChangeError(None, f"Display {device_name} is not active")
    if target.is_primary:
        raise DisplayChangeError(None, "The primary display cannot be moved")

    log.info("set_position %s: (%d, %d) -> (%d, %d)", device_name, target.x, target.y, x, y)
    try:
        _check(_stage(device_name, x, y), f"Staging {device_name}")
        if before.primary is not None:
            _check(_stage(before.primary.device_name, 0, 0), f"Staging {before.primary.device_name}")
        _check(win32api.ChangeDisplaySettingsEx(), "Applying the layout")
    except DisplayChangeError as exc:
        log.error("set_position %s failed: %s", device_name, exc)
        raise
    except pywintypes.error as exc:
        log.error("set_position %s failed: %s", device_name, exc)
        raise DisplayChangeError(None, f"Windows error: {exc.strerror}") from exc

    after = next((d for d in snapshot().all if d.device_name == device_name), None)
    if after is None:
        log.warning("set_position %s: display vanished after the change", device_name)
    else:
        log.info("set_position %s: result OK, now at (%d, %d)", device_name, after.x, after.y)


# --------------------------------------------------------------------------- CLI helpers


def format_snapshot(snap: DisplaySnapshot) -> str:
    rows = [("#", "device", "name", "primary", "x", "y", "width", "height")]
    ordered = sorted(snap.all, key=lambda d: (not d.is_primary, d.device_name))
    for n, d in enumerate(ordered, 1):
        rows.append(
            (str(n), d.device_name, d.friendly_name, "yes" if d.is_primary else "no",
             str(d.x), str(d.y), str(d.width), str(d.height))
        )
    widths = [max(len(r[c]) for r in rows) for c in range(len(rows[0]))]
    lines = [f"status: {snap.status.value}"]
    lines += ["  ".join(cell.ljust(w) for cell, w in zip(r, widths)).rstrip() for r in rows]
    return "\n".join(lines)
