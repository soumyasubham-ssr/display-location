"""Popup window and arrangement canvas (FR-02 … FR-05, FR-15; ARCHITECTURE §6).

TASK-005 builds the static view. Dragging, applying and the revert bar
behaviour come in TASK-006; live refresh while open in TASK-008.
"""

from __future__ import annotations

import logging
import time

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QKeyEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from display_location import layout
from display_location.displays import DisplaySnapshot, DisplayStatus

log = logging.getLogger("display_location.popup")

# --------------------------------------------------------------------------- look (§6)

FRAME_SIZE = QSize(360, 240)  # logical px, the visible rounded panel
RADIUS = 12
SHADOW_MARGIN = 14  # transparent room around the panel for the drop shadow
SCREEN_MARGIN = 8  # gap to the screen edge and to the tray icon

BG = QColor("#202020")
BORDER = QColor("#3a3a3a")
TILE_1 = QColor("#2d2d2d")
TILE_1_BORDER = QColor("#4a4a4a")
TILE_2 = QColor("#a64dbf")
TILE_2_HOVER = QColor("#bd6fd3")  # lighter accent, used by TASK-006 (hover / drag)
TEXT = QColor("#ffffff")
TEXT_DIM = QColor("#c8c8c8")
ERROR = QColor("#ff99a4")

NUMBER_PT = 28
TILE_RADIUS = 4

TITLE = "Display arrangement"
STATUS_MESSAGES = {
    DisplayStatus.SINGLE: "Only one display is connected",
    DisplayStatus.DUPLICATE: "Displays are duplicated — press Win+P and choose Extend",
    DisplayStatus.TOO_MANY: "More than two displays are not supported yet",
}


def ui_font_family() -> str:
    """Segoe UI Variable if installed, else Segoe UI (§6)."""
    families = set(QFontDatabase.families())
    for name in ("Segoe UI Variable Text", "Segoe UI Variable", "Segoe UI"):
        if name in families:
            return name
    return "Segoe UI"


def footer_text(snap: DisplaySnapshot) -> str:
    """e.g. "Display 2: Right of 1 · 1920 × 1080" (FR-03)."""
    p, s = snap.primary, snap.secondary
    side = layout.describe(layout.Rect(0, 0, p.width, p.height), layout.Rect(s.x - p.x, s.y - p.y, s.width, s.height))
    return f"Display 2: {side} · {s.width} × {s.height}"


# --------------------------------------------------------------------------- positioning (FR-04)


def popup_position(frame: QSize, anchor: QRect | None, available: QRect, margin: int = SCREEN_MARGIN) -> QPoint:
    """Top-left of the visible panel.

    Centred above ``anchor`` (the tray icon) with ``margin`` between them; if
    there is no room above (taskbar at the top), below it instead. Then clamped
    into ``available`` with ``margin``. No valid anchor → bottom-right corner.
    """
    w, h = frame.width(), frame.height()
    left_min, top_min = available.left() + margin, available.top() + margin
    left_max = available.left() + available.width() - margin - w
    top_max = available.top() + available.height() - margin - h

    if anchor is None or not anchor.isValid() or anchor.isEmpty():
        return QPoint(max(left_min, left_max), max(top_min, top_max))

    x = anchor.left() + (anchor.width() - w) // 2
    y = anchor.top() - margin - h
    if y < top_min:  # taskbar at the top: open below the icon
        y = anchor.top() + anchor.height() + margin
    x = min(max(x, left_min), max(left_min, left_max))
    y = min(max(y, top_min), max(top_min, top_max))
    return QPoint(x, y)


# --------------------------------------------------------------------------- canvas


class ArrangementCanvas(QWidget):
    """Draws tile 1 (primary) and tile 2 (secondary) in their real relative positions."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.snapshot: DisplaySnapshot | None = None
        self.font_family = ui_font_family()
        self.setMinimumSize(200, 120)

    def set_snapshot(self, snap: DisplaySnapshot | None) -> None:
        self.snapshot = snap
        self.update()

    # Geometry helpers (also for TASK-006: hit-testing and from_canvas).

    def _sizes(self) -> tuple[int, int, int, int] | None:
        snap = self.snapshot
        if snap is None or snap.status is not DisplayStatus.OK:
            return None
        return snap.primary.width, snap.primary.height, snap.secondary.width, snap.secondary.height

    def transform(self) -> tuple[float, float, float] | None:
        """(scale, origin_x, origin_y) for the current widget size, or None."""
        sizes = self._sizes()
        if sizes is None:
            return None
        pw, ph, sw, sh = sizes
        scale = layout.canvas_scale(self.width(), self.height(), pw, ph, sw, sh)
        ox, oy = layout.canvas_origin(self.width(), self.height(), pw, ph, scale)
        return scale, ox, oy

    def tile_rects(self) -> tuple[QRectF, QRectF] | None:
        """Canvas rects of tile 1 and tile 2."""
        t = self.transform()
        if t is None:
            return None
        scale, ox, oy = t
        p, s = self.snapshot.primary, self.snapshot.secondary
        r1 = layout.to_canvas(layout.Rect(0, 0, p.width, p.height), scale, ox, oy)
        r2 = layout.to_canvas(layout.Rect(s.x - p.x, s.y - p.y, s.width, s.height), scale, ox, oy)
        return QRectF(*r1), QRectF(*r2)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt name)
        rects = self.tile_rects()
        if rects is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_tile(painter, rects[0], TILE_1, TILE_1_BORDER, "1")
        self._draw_tile(painter, rects[1], TILE_2, TILE_2, "2")
        painter.end()

    def _draw_tile(self, painter: QPainter, rect: QRectF, fill: QColor, border: QColor, number: str) -> None:
        # Inset by 1 px so touching tiles show a thin dark seam, like Windows Settings.
        r = rect.adjusted(1, 1, -1, -1)
        painter.setPen(QPen(border, 1))
        painter.setBrush(fill)
        painter.drawRoundedRect(r, TILE_RADIUS, TILE_RADIUS)
        font = QFont(self.font_family)
        # ~28 pt, but never taller than about half the tile.
        px = min(NUMBER_PT * self.logicalDpiY() / 72, r.height() * 0.55, r.width() * 0.55)
        font.setPixelSize(max(8, int(px)))
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(TEXT)
        painter.drawText(r, Qt.AlignmentFlag.AlignCenter, number)


# --------------------------------------------------------------------------- popup


class _Panel(QWidget):
    """The visible rounded dark panel (custom paint; carries the drop shadow)."""

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(BORDER, 1))
        painter.setBrush(BG)
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), RADIUS, RADIUS)
        painter.end()


class Popup(QWidget):
    """Frameless popup anchored above the tray icon. Not movable (D-005)."""

    closed = Signal()
    keep_clicked = Signal()  # TASK-006
    revert_clicked = Signal()  # TASK-006

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("Display Location")
        self.closed_at: float | None = None  # time.monotonic() of the last close
        self._anchor: QRect | None = None
        family = ui_font_family()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(SHADOW_MARGIN, SHADOW_MARGIN, SHADOW_MARGIN, SHADOW_MARGIN)
        self.panel = _Panel(self)
        self.panel.setFixedWidth(FRAME_SIZE.width())
        self.panel.setMinimumHeight(FRAME_SIZE.height())
        shadow = QGraphicsDropShadowEffect(self.panel)
        shadow.setBlurRadius(SHADOW_MARGIN * 2)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.panel.setGraphicsEffect(shadow)
        outer.addWidget(self.panel)

        box = QVBoxLayout(self.panel)
        box.setContentsMargins(16, 12, 16, 12)
        box.setSpacing(8)

        self.title = QLabel(TITLE)
        self.title.setFont(QFont(family, 10))
        self.title.setStyleSheet(f"color: {TEXT.name()};")
        box.addWidget(self.title)

        self.stack = QStackedWidget()
        self.canvas = ArrangementCanvas()
        self.message = QLabel()
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message.setWordWrap(True)
        self.message.setFont(QFont(family, 11))
        self.message.setStyleSheet(f"color: {TEXT.name()};")
        self.stack.addWidget(self.canvas)
        self.stack.addWidget(self.message)
        box.addWidget(self.stack, 1)

        self.footer = QLabel()
        self.footer.setFont(QFont(family, 9))
        self.footer.setStyleSheet(f"color: {TEXT_DIM.name()};")
        box.addWidget(self.footer)

        # Reserved for TASK-006: revert bar (FR-07) and inline error (FR-09).
        self.revert_bar = QWidget()
        bar = QHBoxLayout(self.revert_bar)
        bar.setContentsMargins(0, 0, 0, 0)
        self.revert_label = QLabel("Keep changes?")
        self.revert_label.setFont(QFont(family, 9))
        self.revert_label.setStyleSheet(f"color: {TEXT.name()};")
        self.keep_button = QPushButton("Keep")
        self.revert_button = QPushButton("Revert")
        for b in (self.keep_button, self.revert_button):
            b.setFont(QFont(family, 9))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
        self.keep_button.setStyleSheet(
            f"QPushButton {{ background: {TILE_2.name()}; color: white; border: none; border-radius: 4px;"
            f" padding: 4px 12px; }} QPushButton:hover {{ background: {TILE_2_HOVER.name()}; }}"
        )
        self.revert_button.setStyleSheet(
            "QPushButton { background: #3a3a3a; color: white; border: none; border-radius: 4px;"
            " padding: 4px 12px; } QPushButton:hover { background: #4a4a4a; }"
        )
        self.keep_button.clicked.connect(self.keep_clicked)
        self.revert_button.clicked.connect(self.revert_clicked)
        bar.addWidget(self.revert_label, 1)
        bar.addWidget(self.keep_button)
        bar.addWidget(self.revert_button)
        self.revert_bar.hide()
        box.addWidget(self.revert_bar)

        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setFont(QFont(family, 9))
        self.error_label.setStyleSheet(f"color: {ERROR.name()};")
        self.error_label.hide()
        box.addWidget(self.error_label)

    # ------------------------------------------------------------------ content

    def refresh(self, snap: DisplaySnapshot) -> None:
        """Show ``snap``: tiles + footer when OK, else the FR-15 message (TASK-008 calls this live)."""
        if snap.status is DisplayStatus.OK:
            self.canvas.set_snapshot(snap)
            self.footer.setText(footer_text(snap))
            self.footer.show()
            self.stack.setCurrentWidget(self.canvas)
        else:
            self.canvas.set_snapshot(None)
            self.message.setText(STATUS_MESSAGES[snap.status])
            self.footer.hide()
            self.stack.setCurrentWidget(self.message)

    # ------------------------------------------------------------------ open / close

    def open(self, snap: DisplaySnapshot, anchor: QRect | None) -> None:
        self.refresh(snap)
        self._anchor = QRect(anchor) if anchor is not None else None
        self.adjustSize()
        self.place()
        self.show()
        self.raise_()
        self.activateWindow()

    def place(self) -> None:
        """Position the panel above the tray icon (call again if the popup's size changes)."""
        screen = None
        if self._anchor is not None and self._anchor.isValid() and not self._anchor.isEmpty():
            screen = QGuiApplication.screenAt(self._anchor.center())
        screen = screen or QGuiApplication.primaryScreen()
        panel = QSize(FRAME_SIZE.width(), max(FRAME_SIZE.height(), self.sizeHint().height() - 2 * SHADOW_MARGIN))
        top_left = popup_position(panel, self._anchor, screen.availableGeometry())
        self.move(top_left - QPoint(SHADOW_MARGIN, SHADOW_MARGIN))

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def hideEvent(self, event) -> None:  # noqa: N802
        self.closed_at = time.monotonic()
        log.info("Popup closed")
        self.closed.emit()
        super().hideEvent(event)
