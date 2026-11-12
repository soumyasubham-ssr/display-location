"""Keep / Revert countdown after a display change (FR-07, FR-16, D-004, D-013; ARCHITECTURE §7).

Owned by the AppController, not the popup, so it keeps running while the
popup is closed. Display access goes through the injected ``set_position``
(``displays.set_position`` in the app, a fake in tests).
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal

from display_location.displays import DisplayChangeError

log = logging.getLogger("display_location.revert")

COUNTDOWN_S = 10


class RevertManager(QObject):
    tick = Signal(int)  # seconds left (COUNTDOWN_S … 0)
    finished = Signal(bool)  # True = kept (or cancelled), False = reverted
    revert_failed = Signal(str)  # Windows rejected the revert itself

    def __init__(
        self,
        set_position: Callable[[str, int, int], None],
        seconds: int = COUNTDOWN_S,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._set_position = set_position
        self._seconds = seconds
        self.seconds_left = 0
        self.device_name: str | None = None
        self.previous: tuple[int, int] | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

    @property
    def active(self) -> bool:
        return self.previous is not None

    def start(self, device_name: str, previous: tuple[int, int]) -> None:
        """(Re)start the countdown. The first ``previous`` is kept until keep/revert,
        so a second drop still reverts to the layout from before the first one."""
        if not self.active:
            self.device_name, self.previous = device_name, tuple(previous)
            log.info("Countdown started; revert target %s at %s", device_name, self.previous)
        else:
            log.info("Countdown restarted; revert target stays %s", self.previous)
        self.seconds_left = self._seconds
        self._timer.start()
        self.tick.emit(self.seconds_left)

    def keep(self) -> None:
        if not self.active:
            return
        log.info("Change kept")
        self._clear()
        self.finished.emit(True)

    def revert(self) -> None:
        if not self.active:
            return
        device, (x, y) = self.device_name, self.previous
        self._clear()
        log.info("Reverting %s to (%d, %d)", device, x, y)
        try:
            self._set_position(device, x, y)
        except DisplayChangeError as exc:
            log.error("Revert failed: %s", exc)
            self.revert_failed.emit(exc.message)
        self.finished.emit(False)

    def cancel(self, reason: str) -> None:
        """Stop without reverting (e.g. the secondary monitor is gone)."""
        if not self.active:
            return
        log.warning("Countdown cancelled: %s", reason)
        self._clear()
        self.finished.emit(True)

    def _on_tick(self) -> None:
        self.seconds_left -= 1
        self.tick.emit(self.seconds_left)
        if self.seconds_left <= 0:
            log.info("Countdown reached 0")
            self.revert()

    def _clear(self) -> None:
        self._timer.stop()
        self.seconds_left = 0
        self.device_name = None
        self.previous = None
