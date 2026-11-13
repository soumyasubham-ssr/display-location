"""Application controller and Qt event loop."""

from __future__ import annotations

import logging
import signal
import sys
import time

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from display_location import __version__, autostart, displays
from display_location import log_setup
from display_location.log_setup import setup_logging
from display_location.popup import Popup
from display_location.resources import icon_path
from display_location.revert import RevertManager
from display_location.single_instance import SingleInstance
from display_location.tray import TrayIcon

log = logging.getLogger("display_location.app")

TRAY_RETRY_MS = 2000
TRAY_RETRY_LIMIT_S = 30
TOGGLE_GUARD_S = 0.3  # ignore a tray click this soon after the popup closed itself (§6)


class AppController:
    """Owns the components and connects them. Holds no display logic itself."""

    def __init__(self, app: QApplication, single: SingleInstance, icon: QIcon) -> None:
        self.app = app
        self.single = single
        self.icon = icon
        self.tray: TrayIcon | None = None
        self.popup: Popup | None = None
        self.snapshot_fn = displays.snapshot  # replaceable in tests
        self.set_position_fn = displays.set_position  # replaceable in tests
        self.snapshot: displays.DisplaySnapshot | None = None  # last one shown
        self.revert = RevertManager(lambda name, x, y: self.set_position_fn(name, x, y))
        self.revert.tick.connect(self._on_revert_tick)
        self.revert.finished.connect(self._on_revert_finished)
        self.revert.revert_failed.connect(self._on_revert_failed)
        self._applying = False
        self._tray_waited_s = 0
        self._exiting = False

    # ------------------------------------------------------------------ startup

    def start(self) -> None:
        self.single.show_requested.connect(lambda: self.toggle_popup(open_only=True))
        self.app.aboutToQuit.connect(self.before_exit)
        log_setup.crash_handler = self._revert_on_crash  # NFR-06
        try:
            autostart.refresh_stale_path()  # exe moved since it was enabled (packaged exe only)
        except OSError as exc:
            log.error("Could not check the Start with Windows entry: %s", exc)
        self._create_tray_when_available()

    def _create_tray_when_available(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            if self._tray_waited_s >= TRAY_RETRY_LIMIT_S:
                log.error("System tray not available after %d s; exiting", TRAY_RETRY_LIMIT_S)
                self.app.exit(1)
                return
            log.warning("System tray not available yet; retrying in %d s", TRAY_RETRY_MS // 1000)
            self._tray_waited_s += TRAY_RETRY_MS // 1000
            QTimer.singleShot(TRAY_RETRY_MS, self._create_tray_when_available)
            return

        self.tray = TrayIcon(self.icon)
        self.tray.toggle_requested.connect(self.toggle_popup)
        self.tray.open_requested.connect(lambda: self.toggle_popup(open_only=True))
        self.tray.identify_requested.connect(self.identify_displays)
        self.tray.autostart_toggled.connect(self.set_autostart)
        self.tray.exit_requested.connect(self.exit)
        self.tray.autostart_state = self.autostart_state
        self.tray.show()

    # ------------------------------------------------------------------ actions

    def toggle_popup(self, open_only: bool = False) -> None:
        """Left-click toggles; menu Open / second launch only open (FR-02, FR-13)."""
        popup = self._ensure_popup()
        if popup.isVisible():
            if not open_only:
                popup.close()
            return
        # Clicking the tray icon while the popup is open closes it (outside click)
        # and then delivers `activated`: don't reopen straight away.
        if (
            not open_only
            and popup.closed_at is not None
            and time.monotonic() - popup.closed_at < TOGGLE_GUARD_S
        ):
            log.info("tray click right after the popup closed; not reopening")
            return
        snap = self._take_snapshot()
        log.info("Opening popup: %s", snap)
        anchor = self.tray.geometry() if self.tray is not None else None
        popup.open(snap, anchor)

    def _ensure_popup(self) -> Popup:
        if self.popup is None:
            self.popup = Popup()
            self.popup.position_chosen.connect(self.apply_position)
            self.popup.keep_clicked.connect(self.revert.keep)
            self.popup.revert_clicked.connect(self.revert.revert)
        return self.popup

    def _take_snapshot(self) -> displays.DisplaySnapshot:
        snap = self.snapshot_fn()
        self.snapshot = snap
        # The monitor we would revert is gone: nothing to revert (TASK-008 does this live).
        if self.revert.active and all(d.device_name != self.revert.device_name for d in snap.all):
            self.revert.cancel(f"{self.revert.device_name} is no longer active")
        return snap

    # ------------------------------------------------------------------ apply / revert (FR-06 … FR-09)

    def apply_position(self, x: int, y: int) -> None:
        """Move the secondary to physical (x, y) and start / restart the countdown."""
        snap = self.snapshot
        if self._applying or snap is None or snap.status is not displays.DisplayStatus.OK:
            return
        secondary, primary = snap.secondary, snap.primary
        previous = (secondary.x - primary.x, secondary.y - primary.y)
        self._applying = True
        if self.popup is not None:
            self.popup.canvas.drag_enabled = False  # set_position is synchronous (req. 4)
        try:
            self.set_position_fn(secondary.device_name, x, y)
        except displays.DisplayChangeError as exc:
            log.error("Apply failed: %s", exc)
            if self.popup is not None:
                self.popup.show_error(f"Couldn't move display: {exc.message}")
        else:
            self.revert.start(secondary.device_name, previous)
        finally:
            self._applying = False
            # Draw the read-back position (Windows may adjust it) or animate back on failure.
            self._refresh_popup(animate=True)
            if self.popup is not None:
                self.popup.canvas.drag_enabled = True

    def _refresh_popup(self, animate: bool = False) -> None:
        snap = self._take_snapshot()
        if self.popup is not None:
            self.popup.refresh(snap, animate=animate)

    def _on_revert_tick(self, seconds: int) -> None:
        if self.popup is not None:
            self.popup.show_revert(seconds)

    def _on_revert_finished(self, kept: bool) -> None:
        if self.popup is not None:
            self.popup.hide_revert()
        if not kept and not self._exiting:
            self._refresh_popup(animate=True)

    def _on_revert_failed(self, message: str) -> None:
        if self.popup is not None:
            self.popup.show_error(f"Couldn't revert display: {message}")

    def _revert_on_crash(self) -> None:
        if self.revert.active:
            log.critical("Reverting the unconfirmed display change after an error")
            self.revert.revert()

    def identify_displays(self) -> None:
        log.info("identify displays requested (not implemented until TASK-009)")

    def autostart_state(self) -> bool | None:
        """Read on every menu open (FR-12). None = registry unreadable (item greyed out)."""
        try:
            return autostart.is_enabled()
        except OSError as exc:
            log.error("Could not read the Start with Windows entry: %s", exc)
            return None

    def set_autostart(self, enabled: bool) -> None:
        try:
            autostart.set_enabled(enabled)
        except OSError as exc:
            log.error("Could not change Start with Windows to %s: %s", enabled, exc)

    def exit(self) -> None:
        log.info("Exit requested from the tray menu")
        self.app.quit()

    def before_exit(self) -> None:
        """Runs once on every quit path (menu Exit, Ctrl+C, ...).

        An unconfirmed display change is reverted first (FR-16, D-013).
        """
        if self._exiting:
            return
        self._exiting = True
        if self.revert.active:
            log.info("Exiting during the countdown: reverting first")
            self.revert.revert()
        log_setup.crash_handler = None
        if self.popup is not None:
            self.popup.close()
        if self.tray is not None:
            self.tray.hide()
        self.single.close()


def _install_sigint_handler(app: QApplication) -> QTimer:
    """Let Ctrl+C (and Ctrl+Break) in the terminal quit the Qt loop cleanly."""
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    if hasattr(signal, "SIGBREAK"):  # Windows only
        signal.signal(signal.SIGBREAK, lambda *_: app.quit())
    # Qt's C++ loop blocks Python signal handling; wake the interpreter periodically.
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(200)
    return timer


def main() -> int:
    setup_logging()
    log.info("Display Location %s starting", __version__)

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Display Location")
    app.setApplicationVersion(__version__)
    app.setQuitOnLastWindowClosed(False)

    # Single-instance check runs before any tray icon exists (TASK-004 req. 2).
    single = SingleInstance()
    if single.notify_running():
        log.info("Display Location exiting: already running")
        return 0
    single.listen()

    icon = QIcon(str(icon_path()))
    if icon.isNull():
        log.error("Icon not found at %s", icon_path())
    app.setWindowIcon(icon)

    sigint_timer = _install_sigint_handler(app)  # noqa: F841 — keep a reference

    controller = AppController(app, single, icon)
    controller.start()
    code = 1
    try:
        code = app.exec()
    finally:
        controller.before_exit()
        log.info("Display Location exiting (code %s)", code)
    return code
