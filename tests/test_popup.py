"""Popup view, positioning and toggle guard (TASK-005)."""

import time
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt
from PySide6.QtGui import QKeyEvent

from display_location.app import TOGGLE_GUARD_S, AppController
from display_location.displays import Display, DisplaySnapshot, DisplayStatus
from display_location.popup import (
    FRAME_SIZE,
    STATUS_MESSAGES,
    Popup,
    footer_text,
    popup_position,
)

P = Display(r"\\.\DISPLAY1", "Primary", 0, 0, 2560, 1440, True)


def ok(x, y, w=1920, h=1080):
    s = Display(r"\\.\DISPLAY2", "Second", x, y, w, h, False)
    return DisplaySnapshot(DisplayStatus.OK, P, s, (P, s))


def status(st):
    return DisplaySnapshot(st, P if st is not DisplayStatus.DUPLICATE else P, None, (P,))


# --------------------------------------------------------------------------- positioning

AVAIL = QRect(0, 0, 1920, 1032)  # taskbar at the bottom, 48 px


def test_centred_above_icon():
    icon = QRect(1500, 900, 24, 24)  # icon well inside the area: no clamping
    pt = popup_position(QSize(360, 240), icon, AVAIL)
    assert pt == QPoint(1500 + 12 - 180, 900 - 8 - 240)


def test_icon_in_bottom_taskbar_clamped_into_work_area():
    icon = QRect(1500, 1044, 24, 24)
    pt = popup_position(QSize(360, 240), icon, AVAIL)
    assert pt == QPoint(1332, 1032 - 8 - 240)


def test_clamped_to_right_edge():
    icon = QRect(1900, 1040, 24, 24)
    pt = popup_position(QSize(360, 240), icon, AVAIL)
    assert pt.x() + 360 == 1920 - 8


def test_invalid_anchor_bottom_right():
    pt = popup_position(QSize(360, 240), QRect(), AVAIL)
    assert pt == QPoint(1920 - 8 - 360, 1032 - 8 - 240)
    assert popup_position(QSize(360, 240), None, AVAIL) == pt


def test_taskbar_on_top_opens_below():
    avail = QRect(0, 48, 1920, 1032)
    icon = QRect(1500, 12, 24, 24)
    pt = popup_position(QSize(360, 240), icon, avail)
    assert pt.y() == avail.top() + 8  # below the icon, clamped under the top taskbar


def test_taskbar_on_left_clamped_on_screen():
    avail = QRect(48, 0, 1872, 1080)
    icon = QRect(12, 1000, 24, 24)
    pt = popup_position(QSize(360, 240), icon, avail)
    assert pt.x() >= 48 + 8
    assert pt.y() + 240 <= 1080 - 8


def test_negative_origin_screen():
    avail = QRect(-1920, -200, 1920, 1032)
    pt = popup_position(QSize(360, 240), None, avail)
    assert pt == QPoint(-8 - 360, -200 + 1032 - 8 - 240)


# --------------------------------------------------------------------------- content


@pytest.fixture
def popup(qapp):
    p = Popup()
    yield p
    p.close()
    p.deleteLater()


def test_footer_text():
    assert footer_text(ok(2560, 180)) == "Display 2: Right of 1 (centred) · 1920 × 1080"
    assert footer_text(ok(0, -1080)) == "Display 2: Above 1 (left-aligned) · 1920 × 1080"


def test_refresh_ok_shows_canvas(popup):
    popup.refresh(ok(2560, 180))
    assert popup.stack.currentWidget() is popup.canvas
    assert not popup.footer.isHidden()
    assert popup.revert_bar.isHidden() and popup.error_label.isHidden()


@pytest.mark.parametrize("st", [DisplayStatus.SINGLE, DisplayStatus.DUPLICATE, DisplayStatus.TOO_MANY])
def test_refresh_status_message(popup, st):
    popup.refresh(status(st))
    assert popup.stack.currentWidget() is popup.message
    assert popup.message.text() == STATUS_MESSAGES[st]
    assert popup.footer.isHidden()
    assert popup.canvas.tile_rects() is None


def test_status_back_to_ok(popup):
    popup.refresh(status(DisplayStatus.DUPLICATE))
    popup.refresh(ok(-1920, 0))
    assert popup.stack.currentWidget() is popup.canvas


def test_tiles_real_proportions_and_primary_centred(popup):
    popup.refresh(ok(-1920, 180))  # left, centred
    popup.canvas.resize(328, 150)
    r1, r2 = popup.canvas.tile_rects()
    assert r1.width() / r1.height() == pytest.approx(2560 / 1440, rel=1e-6)
    assert r2.width() / r1.width() == pytest.approx(1920 / 2560, rel=1e-6)
    assert r1.center().x() == pytest.approx(164, abs=0.01)
    assert r1.center().y() == pytest.approx(75, abs=0.01)
    assert r2.right() == pytest.approx(r1.left(), abs=0.01)  # touching on the left
    assert r2.center().y() == pytest.approx(r1.center().y(), abs=0.01)
    # Fits the canvas even if moved to any side.
    assert r1.width() + 2 * r2.width() <= 328 and r1.height() + 2 * r2.height() <= 150


def test_open_positions_and_esc_closes(popup):
    popup.open(ok(2560, 0), QRect(-10000, -10000, 0, 0))  # empty anchor -> bottom-right
    assert popup.isVisible()
    assert popup.panel.width() == FRAME_SIZE.width()
    popup.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))
    assert not popup.isVisible()
    assert popup.closed_at is not None


# --------------------------------------------------------------------------- toggle guard


@pytest.fixture
def controller(qapp):
    c = AppController(qapp, MagicMock(), MagicMock())
    c.snapshot_fn = MagicMock(return_value=ok(2560, 0))
    yield c
    if c.popup is not None:
        c.popup.close()
        c.popup.deleteLater()


def test_toggle_opens_then_closes(controller):
    controller.toggle_popup()
    assert controller.popup.isVisible()
    controller.toggle_popup()
    assert not controller.popup.isVisible()


def test_click_right_after_close_does_not_reopen(controller):
    controller.toggle_popup()
    controller.popup.close()  # outside click (the tray icon itself)
    controller.toggle_popup()  # `activated` arrives just after
    assert not controller.popup.isVisible()


def test_click_after_guard_reopens_with_fresh_snapshot(controller):
    controller.toggle_popup()
    controller.popup.close()
    controller.popup.closed_at = time.monotonic() - TOGGLE_GUARD_S - 0.05
    controller.toggle_popup()
    assert controller.popup.isVisible()
    assert controller.snapshot_fn.call_count == 2


def test_open_only_ignores_guard_and_never_closes(controller):
    controller.toggle_popup()
    controller.popup.close()
    controller.toggle_popup(open_only=True)
    assert controller.popup.isVisible()
    controller.toggle_popup(open_only=True)
    assert controller.popup.isVisible()
