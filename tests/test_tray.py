"""Tray menu structure and signals (TASK-004). No real tray interaction."""

import pytest
from PySide6.QtGui import QIcon

from display_location.resources import icon_path
from display_location.tray import TOOLTIP, TrayIcon


@pytest.fixture(scope="module")
def tray(qapp):
    t = TrayIcon(QIcon(str(icon_path())))
    yield t
    t.hide()


def test_icon_loads(qapp):
    icon = QIcon(str(icon_path()))
    assert not icon.isNull()
    sizes = {s.width() for s in icon.availableSizes()}
    assert {16, 24, 32, 48, 256} <= sizes


def test_tooltip(tray):
    assert tray.tray.toolTip() == TOOLTIP == "Display Location"


def test_menu_entries_in_order(tray):
    entries = ["---" if a.isSeparator() else a.text() for a in tray.menu.actions()]
    assert entries == ["Open", "Identify displays", "Start with Windows", "---", "Exit"]
    assert tray.act_autostart.isCheckable()


def test_autostart_item_follows_state_hook(tray):
    tray._refresh_menu()
    assert not tray.act_autostart.isEnabled()
    tray.autostart_state = lambda: True
    tray._refresh_menu()
    assert tray.act_autostart.isEnabled() and tray.act_autostart.isChecked()
    tray.autostart_state = lambda: None


def test_signals(tray):
    seen = []
    tray.open_requested.connect(lambda: seen.append("open"))
    tray.identify_requested.connect(lambda: seen.append("identify"))
    tray.exit_requested.connect(lambda: seen.append("exit"))
    tray.toggle_requested.connect(lambda: seen.append("toggle"))
    tray.act_open.trigger()
    tray.act_identify.trigger()
    tray.act_exit.trigger()
    from PySide6.QtWidgets import QSystemTrayIcon

    tray._on_activated(QSystemTrayIcon.ActivationReason.Trigger)
    tray._on_activated(QSystemTrayIcon.ActivationReason.Context)  # right-click: no toggle
    assert seen == ["open", "identify", "exit", "toggle"]
