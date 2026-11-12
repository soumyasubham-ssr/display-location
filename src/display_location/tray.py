"""Tray icon and its right-click menu (FR-01, FR-02, FR-10)."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

log = logging.getLogger("display_location.tray")

TOOLTIP = "Display Location"


class TrayIcon(QObject):
    toggle_requested = Signal()  # left-click
    open_requested = Signal()  # menu "Open"
    identify_requested = Signal()
    autostart_toggled = Signal(bool)
    exit_requested = Signal()

    def __init__(self, icon: QIcon, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip(TOOLTIP)

        self.menu = QMenu()
        self.act_open = QAction("Open", self.menu)
        self.act_identify = QAction("Identify displays", self.menu)
        self.act_autostart = QAction("Start with Windows", self.menu, checkable=True)
        self.act_exit = QAction("Exit", self.menu)
        self.menu.addAction(self.act_open)
        self.menu.addAction(self.act_identify)
        self.menu.addAction(self.act_autostart)
        self.menu.addSeparator()
        self.menu.addAction(self.act_exit)
        self.menu.setDefaultAction(self.act_open)

        self.act_open.triggered.connect(self.open_requested)
        self.act_identify.triggered.connect(self.identify_requested)
        self.act_autostart.triggered.connect(self.autostart_toggled)
        self.act_exit.triggered.connect(self.exit_requested)
        self.menu.aboutToShow.connect(self._refresh_menu)
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._on_activated)

        # Hooks the controller can replace; consulted every time the menu opens.
        self.autostart_state = lambda: None  # None = feature not available yet (TASK-007)

    def show(self) -> None:
        self.tray.show()
        log.info("Tray icon shown (geometry %s)", self.tray.geometry().getRect())

    def hide(self) -> None:
        self.tray.hide()

    def geometry(self):
        return self.tray.geometry()

    def _refresh_menu(self) -> None:
        state = self.autostart_state()
        self.act_autostart.setEnabled(state is not None)
        self.act_autostart.setChecked(bool(state))

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_requested.emit()
