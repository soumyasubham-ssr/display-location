"""Start with Windows (TASK-007).

All registry work happens under HKCU\\Software\\DisplayLocation-pytest, never in
the real Run / StartupApproved keys. The whole test key is removed afterwards.
"""

import sys
import winreg
from unittest.mock import MagicMock

import pytest

from display_location import autostart
from display_location.autostart import AutostartKeys

ROOT = r"Software\DisplayLocation-pytest"
KEYS = AutostartKeys(run=ROOT + r"\Run", approved=ROOT + r"\StartupApproved\Run", value_name="DisplayLocation-pytest")


def _delete_tree(path):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_ALL_ACCESS) as key:
            while True:
                try:
                    sub = winreg.EnumKey(key, 0)
                except OSError:
                    break
                _delete_tree(path + "\\" + sub)
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
    except FileNotFoundError:
        pass


def _exists(path):
    try:
        winreg.OpenKey(winreg.HKEY_CURRENT_USER, path).Close()
        return True
    except FileNotFoundError:
        return False


@pytest.fixture
def keys():
    _delete_tree(ROOT)
    yield KEYS
    _delete_tree(ROOT)
    assert not _exists(ROOT)


def _set_approved(first_byte):
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, KEYS.approved, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, KEYS.value_name, 0, winreg.REG_BINARY, bytes([first_byte]) + bytes(11))


def test_real_keys_match_architecture():
    assert autostart.REAL.run == r"Software\Microsoft\Windows\CurrentVersion\Run"
    assert autostart.REAL.approved == r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
    assert autostart.REAL.value_name == "DisplayLocation"


def test_default_off(keys):
    assert not autostart.is_enabled(keys)
    assert autostart.stored_command(keys) is None


def test_enable_writes_command(keys):
    autostart.enable(keys)
    assert autostart.is_enabled(keys)
    assert autostart.stored_command(keys) == autostart.command()


def test_disable_removes_value(keys):
    autostart.enable(keys)
    autostart.disable(keys)
    assert not autostart.is_enabled(keys)
    assert autostart.stored_command(keys) is None
    autostart.disable(keys)  # already off: no error


@pytest.mark.parametrize("byte,disabled", [(0x02, False), (0x06, False), (0x03, True), (0x07, True)])
def test_task_manager_state(keys, byte, disabled):
    autostart.enable(keys)
    _set_approved(byte)
    assert autostart.disabled_in_task_manager(keys) is disabled
    assert autostart.is_enabled(keys) is not disabled


def test_enable_clears_task_manager_disable(keys):
    autostart.enable(keys)
    _set_approved(0x03)
    assert not autostart.is_enabled(keys)
    autostart.enable(keys)  # owner re-checks the menu item
    assert autostart.is_enabled(keys)
    assert autostart._read(keys.approved, keys.value_name) is None


def test_set_enabled(keys):
    autostart.set_enabled(True, keys)
    assert autostart.is_enabled(keys)
    autostart.set_enabled(False, keys)
    assert not autostart.is_enabled(keys)


def test_command_from_source(monkeypatch, tmp_path):
    scripts = tmp_path / "venv" / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "python.exe").write_bytes(b"")
    (scripts / "pythonw.exe").write_bytes(b"")
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(sys, "executable", str(scripts / "python.exe"))
    assert autostart.command() == f'"{scripts / "pythonw.exe"}" -m display_location'


def test_command_frozen(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Tools\DisplayLocation.exe")
    assert autostart.command() == r'"C:\Tools\DisplayLocation.exe"'


def test_refresh_stale_path_rewrites_moved_exe(keys, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Old\DisplayLocation.exe")
    autostart.enable(keys)
    monkeypatch.setattr(sys, "executable", r"D:\New\DisplayLocation.exe")
    assert autostart.refresh_stale_path(keys)
    assert autostart.stored_command(keys) == r'"D:\New\DisplayLocation.exe"'
    assert not autostart.refresh_stale_path(keys)  # now current


def test_refresh_stale_path_skips_source_disabled_and_off(keys, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Old\DisplayLocation.exe")
    assert not autostart.refresh_stale_path(keys)  # not enabled
    autostart.enable(keys)
    monkeypatch.setattr(sys, "executable", r"D:\New\DisplayLocation.exe")
    assert not autostart.refresh_stale_path(keys, frozen=False)  # running from source
    _set_approved(0x03)
    assert not autostart.refresh_stale_path(keys)  # disabled in Task Manager: leave alone
    assert autostart.stored_command(keys) == r'"C:\Old\DisplayLocation.exe"'


# --------------------------------------------------------------------------- controller wiring (no registry)


@pytest.fixture
def ctl(qapp, monkeypatch):
    from display_location.app import AppController

    return AppController(qapp, MagicMock(), MagicMock())


def test_controller_state_and_toggle(ctl, monkeypatch):
    calls = []
    monkeypatch.setattr(autostart, "is_enabled", lambda: True)
    monkeypatch.setattr(autostart, "set_enabled", lambda on: calls.append(on))
    assert ctl.autostart_state() is True
    ctl.set_autostart(False)
    assert calls == [False]


def test_controller_registry_error_greys_out(ctl, monkeypatch):
    def boom(*_):
        raise PermissionError("denied")

    monkeypatch.setattr(autostart, "is_enabled", boom)
    monkeypatch.setattr(autostart, "set_enabled", boom)
    assert ctl.autostart_state() is None
    ctl.set_autostart(True)  # logged, not raised
