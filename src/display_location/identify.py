""""Identify displays" overlays (FR-11; ARCHITECTURE §9).

Shows a big "1" on the primary and "2" on the secondary — the same numbers as
the popup tiles — for 3 s. The overlays are click-through, always on top and
never take focus. Calling ``show`` again while they are up reuses the windows
and restarts the timer.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence

from PySide6.QtCore import QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QScreen
from PySide6.QtWidgets import QWidget

from display_location.displays import Display, DisplaySnapshot
from display_location.popup import TEXT, ui_font_family

log = logging.getLogger("display_location.identify")

SHOW_MS = 3000
BOX_SIZE = 220  # logical px, square
BOX_RADIUS = 16
BOX_BG = QColor(32, 32, 32, 215)  # translucent version of the popup background
BOX_BORDER = QColor(255, 255, 255, 40)
NUMBER_PT = 120


def numbered(snap: DisplaySnapshot) -> list[tuple[str, Display]]:
    """("1", primary) and ("2", secondary) when present — exactly the tile numbers."""
    out = []
    if snap.primary is not None:
        out.append(("1", snap.primary))
    if snap.secondary is not None:
        out.append(("2", snap.secondary))
    return out


def _physical_rect(screen) -> tuple[int, int]:
    """Physical-pixel size of a screen (Qt geometry is logical)."""
    g, dpr = screen.geometry(), screen.devicePixelRatio()
    return round(g.width() * dpr), round(g.height() * dpr)


def find_screen(display: Display, screens: Sequence, primary_screen=None):
    """The QScreen for ``display``: by name (``\\\\.\\DISPLAYn``), else by physical
    size (preferring the one whose primary-ness matches). None if nothing fits."""
    for s in screens:
        if s.name() == display.device_name:
            return s
    same_size = [s for s in screens if _physical_rect(s) == (display.width, display.height)]
    if not same_size:
        log.warning("No screen found for %s", display.device_name)
        return None
    pick = next((s for s in same_size if (s is primary_screen) == display.is_primary), same_size[0])
    log.warning("No screen named %s; matched %s by size", display.device_name, pick.name())
    return pick


def centred(box: int, area: QRect) -> QRect:
    """A ``box`` × ``box`` square centred in ``area``."""
    return QRect(area.x() + (area.width() - box) // 2, area.y() + (area.height() - box) // 2, box, box)


class IdentifyOverlay(QWidget):
    """One rounded translucent box with a number."""

    def __init__(self, number: str) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.number = number
        self.font_family = ui_font_family()
        self.resize(BOX_SIZE, BOX_SIZE)

    def place_on(self, screen: QScreen) -> None:
        self.setScreen(screen)  # take that screen's scale before sizing (mixed DPI)
        self.setGeometry(centred(BOX_SIZE, screen.geometry()))

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(BOX_BORDER)
        painter.setBrush(BOX_BG)
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), BOX_RADIUS, BOX_RADIUS)
        font = QFont(self.font_family)
        font.setPixelSize(min(int(NUMBER_PT * self.logicalDpiY() / 72), int(self.height() * 0.8)))
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(TEXT)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.number)
        painter.end()


class Identifier:
    """Owns the overlays and the 3 s timer."""

    def __init__(self) -> None:
        self.overlays: dict[str, IdentifyOverlay] = {}
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(SHOW_MS)
        self.timer.timeout.connect(self.hide)

    @property
    def visible(self) -> bool:
        return any(o.isVisible() for o in self.overlays.values())

    def show(self, snap: DisplaySnapshot, screens: Iterable[QScreen] | None = None) -> None:
        screens = list(screens if screens is not None else QGuiApplication.screens())
        wanted = set()
        for number, display in numbered(snap):
            screen = find_screen(display, screens, QGuiApplication.primaryScreen())
            if screen is None:
                continue
            overlay = self.overlays.get(number) or self.overlays.setdefault(number, IdentifyOverlay(number))
            overlay.place_on(screen)
            overlay.show()
            overlay.raise_()
            wanted.add(number)
            log.info("Identify: %s on %s", number, screen.name())
        for number, overlay in self.overlays.items():
            if number not in wanted:
                overlay.hide()  # e.g. "2" left over after monitor 2 went
        self.timer.start()

    def hide(self) -> None:
        self.timer.stop()
        for overlay in self.overlays.values():
            overlay.hide()

    def close(self) -> None:
        self.hide()
        for overlay in self.overlays.values():
            overlay.deleteLater()
        self.overlays.clear()
