"""Popup window and arrangement canvas (FR-02 … FR-05, FR-15; ARCHITECTURE §6).

TASK-005 built the static view; TASK-006 adds dragging tile 2 (FR-06), the
Keep/Revert bar (FR-07) and the inline error (FR-09). The popup never changes
displays itself: it emits ``position_chosen`` and the controller applies it.
Live refresh while open comes in TASK-008.
"""

from __future__ import annotations

import logging
import time

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
    Signal,
)
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
TILE_2_HOVER = QColor("#bd6fd3")  # lighter accent while hovered / dragged
TEXT = QColor("#ffffff")
TEXT_DIM = QColor("#c8c8c8")
ERROR = QColor("#ff99a4")

NUMBER_PT = 28
TILE_RADIUS = 4
SNAP_ANIMATION_MS = 120
ERROR_SHOW_MS = 5000
BOTTOM_ROW_H = 34  # fits the revert buttons or a two-line error

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
    """Draws tile 1 (primary) and tile 2 (secondary) in their real relative positions.

    Tile 2 can be dragged (FR-06). On release the drop is snapped with
    ``layout.snap``, the tile animates there and ``position_chosen(x, y)`` is
    emitted with the secondary's new physical top-left, unless it equals the
    current position (FR-08).
    """

    position_chosen = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.snapshot: DisplaySnapshot | None = None
        self.font_family = ui_font_family()
        self.drag_enabled = True
        self._dragging = False
        self._hover = False
        self._grab_offset = QPointF()
        # Canvas rect drawn for tile 2 instead of the real one (while dragging / animating).
        self._override: QRectF | None = None
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(SNAP_ANIMATION_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim_value)
        self._anim.finished.connect(self._on_anim_finished)
        self._after_anim = None
        self.setMinimumSize(200, 100)
        self.setMouseTracking(True)

    def set_snapshot(self, snap: DisplaySnapshot | None, animate: bool = False) -> None:
        """Show ``snap``. With ``animate``, tile 2 glides from where it is drawn now
        to its new real position (used after apply, revert and failures)."""
        old = self._drawn_tile2()
        self.snapshot = snap
        if self._dragging:
            return  # keep following the mouse; the drop decides
        rects = self.tile_rects()
        if animate and old is not None and rects is not None and old != rects[1]:
            self._animate(old, rects[1], None)
        else:
            self._anim.stop()
            self._after_anim = None
            self._override = None
        self.update()

    @property
    def busy(self) -> bool:
        """Dragging or animating."""
        return self._dragging or self._anim.state() == QVariantAnimation.State.Running

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

    def _drawn_tile2(self) -> QRectF | None:
        if self._override is not None:
            return QRectF(self._override)
        rects = self.tile_rects()
        return rects[1] if rects else None

    # ------------------------------------------------------------------ drag (FR-06)

    def _can_drag(self) -> bool:
        return self.drag_enabled and self.tile_rects() is not None and not self.busy

    def _update_cursor(self, pos: QPointF) -> None:
        r2 = self._drawn_tile2()
        over = r2 is not None and r2.contains(pos) and self.drag_enabled
        if self._dragging:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif over:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.unsetCursor()
        if over != self._hover:
            self._hover = over
            self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        pos = event.position()
        r2 = self._drawn_tile2()
        if event.button() == Qt.MouseButton.LeftButton and self._can_drag() and r2.contains(pos):
            self._dragging = True
            self._grab_offset = pos - r2.topLeft()
            self._override = r2
            self._update_cursor(pos)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        pos = event.position()
        if self._dragging:
            self._override = QRectF(pos - self._grab_offset, self._override.size())
            self.update()
        self._update_cursor(pos)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if not (self._dragging and event.button() == Qt.MouseButton.LeftButton):
            super().mouseReleaseEvent(event)
            return
        self._dragging = False
        self._override = QRectF(event.position() - self._grab_offset, self._override.size())
        self._update_cursor(event.position())
        self.drop(self._override.topLeft())

    def drop(self, canvas_top_left: QPointF) -> None:
        """Snap a tile-2 drop whose top-left is at ``canvas_top_left`` and emit the result."""
        rects = self.tile_rects()
        if rects is None:
            self._override = None
            self.update()
            return
        scale, ox, oy = self.transform()
        p, s = self.snapshot.primary, self.snapshot.secondary
        px, py = layout.from_canvas(canvas_top_left.x(), canvas_top_left.y(), scale, ox, oy)
        side, x, y = layout.snap(p.width, p.height, s.width, s.height, px, py)
        current = (s.x - p.x, s.y - p.y)
        target = QRectF(*layout.to_canvas(layout.Rect(x, y, s.width, s.height), scale, ox, oy))
        start = self._override if self._override is not None else rects[1]
        log.info("Tile 2 dropped at %s -> snapped %s (%d, %d)", (px, py), side.value, x, y)
        if (x, y) == current:
            log.info("Same position as now; nothing to apply (FR-08)")
            self._animate(start, target, None)
        else:
            # Keep drawing the snapped spot until the controller sends the read-back snapshot.
            self._animate(start, target, lambda: self.position_chosen.emit(x, y), keep=True)

    # ------------------------------------------------------------------ animation

    def _animate(self, start: QRectF, end: QRectF, after, keep: bool = False) -> None:
        self._anim.stop()
        self._after_anim = (after, keep)
        self._override = QRectF(start)
        self._anim.setStartValue(QRectF(start))
        self._anim.setEndValue(QRectF(end))
        self._anim.start()

    def _on_anim_value(self, value) -> None:
        self._override = QRectF(value)
        self.update()

    def _on_anim_finished(self) -> None:
        after, keep = self._after_anim or (None, False)
        self._after_anim = None
        if not keep:
            self._override = None
            self.update()
        if after is not None:
            after()

    # ------------------------------------------------------------------ paint

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt name)
        rects = self.tile_rects()
        if rects is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_tile(painter, rects[0], TILE_1, TILE_1_BORDER, "1")
        accent = TILE_2_HOVER if (self._hover or self._dragging) else TILE_2
        self._draw_tile(painter, self._drawn_tile2(), accent, accent, "2")
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
    position_chosen = Signal(int, int)  # secondary's new physical top-left
    keep_clicked = Signal()
    revert_clicked = Signal()

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
        self.panel.setFixedSize(FRAME_SIZE)  # the bottom row swaps content, so the size never changes
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
        self.canvas.position_chosen.connect(self.position_chosen)
        self.message = QLabel()
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message.setWordWrap(True)
        self.message.setFont(QFont(family, 11))
        self.message.setStyleSheet(f"color: {TEXT.name()};")
        self.stack.addWidget(self.canvas)
        self.stack.addWidget(self.message)
        box.addWidget(self.stack, 1)

        # Bottom row: fixed height so the canvas (and tile size) never changes when
        # it swaps between footer, revert bar and error.
        self.bottom = QWidget()
        self.bottom.setFixedHeight(BOTTOM_ROW_H)
        bottom = QVBoxLayout(self.bottom)
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(0)
        box.addWidget(self.bottom)

        self.footer = QLabel()
        self.footer.setFont(QFont(family, 9))
        self.footer.setStyleSheet(f"color: {TEXT_DIM.name()};")
        bottom.addWidget(self.footer)

        # Bottom row shows one of: inline error (FR-09) > revert bar (FR-07) > footer.
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
        bottom.addWidget(self.revert_bar)

        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setFont(QFont(family, 9))
        self.error_label.setStyleSheet(f"color: {ERROR.name()};")
        self.error_label.hide()
        bottom.addWidget(self.error_label)

        self._show_footer = False
        self._revert_seconds: int | None = None
        self._error_timer = QTimer(self)
        self._error_timer.setSingleShot(True)
        self._error_timer.setInterval(ERROR_SHOW_MS)
        self._error_timer.timeout.connect(self.clear_error)

    # ------------------------------------------------------------------ bottom row

    def _update_bottom(self) -> None:
        error = self._error_timer.isActive()
        bar = not error and self._revert_seconds is not None
        self.error_label.setVisible(error)
        self.revert_bar.setVisible(bar)
        self.footer.setVisible(not error and not bar and self._show_footer)

    def show_revert(self, seconds: int) -> None:
        """Show / update "Keep changes?  [Keep]  [Revert (n)]" (works while hidden too)."""
        self._revert_seconds = seconds
        self.revert_button.setText(f"Revert ({seconds})")
        self._update_bottom()

    def hide_revert(self) -> None:
        self._revert_seconds = None
        self._update_bottom()

    def show_error(self, text: str) -> None:
        """Red inline message for 5 s (FR-09)."""
        self.error_label.setText(text)
        self._error_timer.start()
        self._update_bottom()

    def clear_error(self) -> None:
        self._error_timer.stop()
        self._update_bottom()

    # ------------------------------------------------------------------ content

    def refresh(self, snap: DisplaySnapshot, animate: bool = False) -> None:
        """Show ``snap``: tiles + footer when OK, else the FR-15 message (TASK-008 calls this live).

        ``animate`` glides tile 2 from where it is drawn to the new real position."""
        if snap.status is DisplayStatus.OK:
            self.canvas.set_snapshot(snap, animate=animate and self.isVisible())
            self.footer.setText(footer_text(snap))
            self._show_footer = True
            self.stack.setCurrentWidget(self.canvas)
        else:
            self.canvas.set_snapshot(None)
            self.message.setText(STATUS_MESSAGES[snap.status])
            self._show_footer = False
            self.stack.setCurrentWidget(self.message)
        self._update_bottom()

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
        """Position the panel above the tray icon."""
        screen = None
        if self._anchor is not None and self._anchor.isValid() and not self._anchor.isEmpty():
            screen = QGuiApplication.screenAt(self._anchor.center())
        screen = screen or QGuiApplication.primaryScreen()
        top_left = popup_position(FRAME_SIZE, self._anchor, screen.availableGeometry())
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
