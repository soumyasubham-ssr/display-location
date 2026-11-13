"""Start with Windows via the HKCU Run key (FR-12, D-006; ARCHITECTURE §10).

``winreg`` only. Every function takes an optional ``keys`` (``AutostartKeys``) so
tests can work under a throwaway key and never touch the real Run value.
"""

from __future__ import annotations

import logging
import sys
import winreg
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("display_location.autostart")

VALUE_NAME = "DisplayLocation"


@dataclass(frozen=True)
class AutostartKeys:
    run: str = r"Software\Microsoft\Windows\CurrentVersion\Run"
    approved: str = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
    value_name: str = VALUE_NAME


REAL = AutostartKeys()


def command() -> str:
    """What the Run value should contain for the running app."""
    if getattr(sys, "frozen", False):  # PyInstaller exe
        return f'"{sys.executable}"'
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    return f'"{pythonw if pythonw.exists() else exe}" -m display_location'


def _read(path: str, name: str):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            return winreg.QueryValueEx(key, name)[0]
    except FileNotFoundError:
        return None


def _delete(path: str, name: str) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, name)
        return True
    except FileNotFoundError:
        return False


def stored_command(keys: AutostartKeys = REAL) -> str | None:
    value = _read(keys.run, keys.value_name)
    return value if isinstance(value, str) else None


def disabled_in_task_manager(keys: AutostartKeys = REAL) -> bool:
    """Task Manager → Startup apps writes a binary value whose first byte is odd
    (0x03, sometimes 0x07) when the user disables the entry, even (0x02 / 0x06) when enabled."""
    data = _read(keys.approved, keys.value_name)
    return isinstance(data, bytes) and len(data) > 0 and data[0] & 1 == 1


def is_enabled(keys: AutostartKeys = REAL) -> bool:
    return stored_command(keys) is not None and not disabled_in_task_manager(keys)


def enable(keys: AutostartKeys = REAL) -> None:
    cmd = command()
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, keys.run, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, keys.value_name, 0, winreg.REG_SZ, cmd)
    # Remove a Task Manager "disabled" mark so the entry is really active again.
    _delete(keys.approved, keys.value_name)
    log.info("Start with Windows enabled: %s", cmd)


def disable(keys: AutostartKeys = REAL) -> None:
    removed = _delete(keys.run, keys.value_name)
    log.info("Start with Windows disabled (%s)", "value removed" if removed else "was not set")


def set_enabled(enabled: bool, keys: AutostartKeys = REAL) -> None:
    enable(keys) if enabled else disable(keys)


def refresh_stale_path(keys: AutostartKeys = REAL, frozen: bool | None = None) -> bool:
    """If enabled but pointing at another location (exe moved), rewrite it. Returns True if rewritten.

    Only for the packaged exe: running from source must not silently repoint an
    exe entry at python."""
    if not (getattr(sys, "frozen", False) if frozen is None else frozen):
        return False
    stored = stored_command(keys)
    if stored is None or disabled_in_task_manager(keys):
        return False
    current = command()
    if stored.strip().lower() == current.lower():
        return False
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, keys.run, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, keys.value_name, 0, winreg.REG_SZ, current)
    log.info("Start with Windows path updated: %s -> %s", stored, current)
    return True
