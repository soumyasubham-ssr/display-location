"""Application controller and Qt event loop."""

from __future__ import annotations

import logging
import signal
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from display_location import __version__
from display_location.log_setup import setup_logging

log = logging.getLogger("display_location.app")


class AppController:
    """Wires the components together (tray, popup, revert, ...). Filled in by later tasks."""

    def __init__(self, app: QApplication) -> None:
        self.app = app

    def start(self) -> None:
        pass

    def shutdown(self) -> None:
        pass


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

    sigint_timer = _install_sigint_handler(app)  # noqa: F841 — keep a reference

    controller = AppController(app)
    controller.start()
    code = 1
    try:
        code = app.exec()
    finally:
        controller.shutdown()
        log.info("Display Location exiting (code %s)", code)
    return code
