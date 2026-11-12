"""RevertManager, apply / revert wiring and tile dragging (TASK-006). No real display changes."""

from unittest.mock import MagicMock

import time

import pytest
from PySide6.QtCore import QCoreApplication, QPoint, QPointF, Qt
from PySide6.QtTest import QSignalSpy, QTest

from display_location import log_setup
from display_location.app import AppController
from display_location.displays import Display, DisplayChangeError, DisplaySnapshot, DisplayStatus
from display_location.revert import COUNTDOWN_S, RevertManager

P = Display(r"\\.\DISPLAY1", "Primary", 0, 0, 2560, 1440, True)
DEV = r"\\.\DISPLAY2"


class FakeDisplays:
    """Stands in for displays.snapshot / set_position: keeps the secondary's position."""

    def __init__(self, x=2560, y=180, fail=None):
        self.pos = (x, y)
        self.fail = fail  # DisplayChangeError to raise, or None
        self.calls = []

    def snapshot(self):
        s = Display(DEV, "Second", *self.pos, 1920, 1080, False)
        return DisplaySnapshot(DisplayStatus.OK, P, s, (P, s))

    def set_position(self, name, x, y):
        self.calls.append((name, x, y))
        if self.fail is not None:
            raise self.fail
        self.pos = (x, y)


# --------------------------------------------------------------------------- RevertManager


@pytest.fixture
def mgr(qapp):
    fake = MagicMock()
    m = RevertManager(fake)
    m.fake = fake
    yield m
    m._clear()


def ticks(m, n):
    for _ in range(n):
        m._on_tick()


def test_start_emits_full_countdown(mgr):
    spy = QSignalSpy(mgr.tick)
    mgr.start(DEV, (2560, 0))
    assert mgr.active and mgr.seconds_left == COUNTDOWN_S == 10
    assert spy.count() == 1 and spy.at(0) == [10]
    assert mgr._timer.isActive()


def test_keep(mgr):
    spy = QSignalSpy(mgr.finished)
    mgr.start(DEV, (2560, 0))
    mgr.keep()
    assert not mgr.active and not mgr._timer.isActive()
    assert spy.at(0) == [True]
    mgr.fake.assert_not_called()


def test_revert(mgr):
    spy = QSignalSpy(mgr.finished)
    mgr.start(DEV, (2560, 0))
    mgr.revert()
    mgr.fake.assert_called_once_with(DEV, 2560, 0)
    assert spy.at(0) == [False] and not mgr.active


def test_timeout_reverts(mgr):
    spy = QSignalSpy(mgr.tick)
    mgr.start(DEV, (2560, 0))
    ticks(mgr, 9)
    mgr.fake.assert_not_called()
    ticks(mgr, 1)
    mgr.fake.assert_called_once_with(DEV, 2560, 0)
    assert [spy.at(i)[0] for i in range(spy.count())] == list(range(10, -1, -1))


def test_second_start_keeps_original_target(mgr):
    mgr.start(DEV, (2560, 0))
    ticks(mgr, 6)
    mgr.start(DEV, (0, 1440))  # second drop: (0, 1440) is the *intermediate* layout
    assert mgr.seconds_left == 10 and mgr.previous == (2560, 0)
    mgr.revert()
    mgr.fake.assert_called_once_with(DEV, 2560, 0)


def test_revert_failure_reported(mgr):
    mgr.fake.side_effect = DisplayChangeError(-1, "nope")
    failed, finished = QSignalSpy(mgr.revert_failed), QSignalSpy(mgr.finished)
    mgr.start(DEV, (2560, 0))
    mgr.revert()
    assert failed.at(0) == ["nope"] and finished.at(0) == [False] and not mgr.active


def test_cancel_does_not_touch_displays(mgr):
    mgr.start(DEV, (2560, 0))
    mgr.cancel("unplugged")
    assert not mgr.active
    mgr.fake.assert_not_called()


def test_keep_and_revert_when_idle_do_nothing(mgr):
    spy = QSignalSpy(mgr.finished)
    mgr.keep()
    mgr.revert()
    assert spy.count() == 0
    mgr.fake.assert_not_called()


# --------------------------------------------------------------------------- controller wiring


@pytest.fixture
def ctl(qapp):
    fake = FakeDisplays()
    c = AppController(qapp, MagicMock(), MagicMock())
    c.snapshot_fn, c.set_position_fn = fake.snapshot, fake.set_position
    c.fake = fake
    c.toggle_popup()
    c.popup.canvas.resize(328, 150)
    yield c
    c.revert._clear()
    c.popup.close()
    c.popup.deleteLater()
    log_setup.crash_handler = None


def test_apply_starts_countdown_and_shows_bar(ctl):
    ctl.apply_position(0, 1440)
    assert ctl.fake.pos == (0, 1440)
    assert ctl.revert.active and ctl.revert.previous == (2560, 180)
    assert not ctl.popup.revert_bar.isHidden() and ctl.popup.footer.isHidden()
    assert ctl.popup.revert_button.text() == "Revert (10)"
    assert ctl.snapshot.secondary.y == 1440  # read back
    assert ctl.popup.canvas.drag_enabled


def test_revert_button_restores_and_hides_bar(ctl):
    ctl.apply_position(0, 1440)
    ctl.popup.revert_button.click()
    assert ctl.fake.pos == (2560, 180)
    assert ctl.popup.revert_bar.isHidden() and not ctl.popup.footer.isHidden()


def test_keep_button(ctl):
    ctl.apply_position(0, 1440)
    ctl.popup.keep_button.click()
    assert ctl.fake.pos == (0, 1440) and not ctl.revert.active
    assert ctl.popup.revert_bar.isHidden()


def test_second_drop_then_revert_returns_to_original(ctl):
    ctl.apply_position(0, 1440)
    ctl.apply_position(-1920, 0)
    assert ctl.revert.previous == (2560, 180)
    ctl.revert.revert()
    assert ctl.fake.pos == (2560, 180)


def test_countdown_continues_with_popup_closed_and_shows_on_reopen(ctl):
    ctl.apply_position(0, 1440)
    ctl.popup.close()
    ticks(ctl.revert, 4)
    ctl.popup.closed_at = None
    ctl.toggle_popup()
    assert ctl.popup.isVisible()
    assert not ctl.popup.revert_bar.isHidden() and ctl.popup.revert_button.text() == "Revert (6)"
    ctl.popup.close()
    ticks(ctl.revert, 6)
    assert ctl.fake.pos == (2560, 180)


def test_apply_failure_shows_error_no_countdown(ctl):
    ctl.fake.fail = DisplayChangeError(-1, "The display driver failed the requested change")
    ctl.apply_position(0, 1440)
    assert not ctl.revert.active
    assert not ctl.popup.error_label.isHidden()
    assert ctl.popup.error_label.text() == "Couldn't move display: The display driver failed the requested change"
    ctl.popup.clear_error()  # after 5 s
    assert ctl.popup.error_label.isHidden() and not ctl.popup.footer.isHidden()


def test_exit_during_countdown_reverts(ctl):
    ctl.apply_position(0, 1440)
    ctl.before_exit()
    assert ctl.fake.pos == (2560, 180) and not ctl.revert.active


def test_crash_handler_reverts(ctl):
    log_setup.crash_handler = ctl._revert_on_crash  # what AppController.start() sets
    ctl.apply_position(0, 1440)
    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        log_setup._excepthook(type(exc), exc, exc.__traceback__)
    assert ctl.fake.pos == (2560, 180)


def test_secondary_gone_cancels_countdown(ctl):
    ctl.apply_position(0, 1440)
    ctl.snapshot_fn = lambda: DisplaySnapshot(DisplayStatus.SINGLE, P, None, (P,))
    ctl.popup.close()
    ctl.popup.closed_at = None
    ctl.toggle_popup()
    assert not ctl.revert.active
    assert ctl.fake.calls == [(DEV, 0, 1440)]  # no revert attempted


# --------------------------------------------------------------------------- dragging


def wait_for(cond, timeout=2.0):
    end = time.monotonic() + timeout
    while not cond() and time.monotonic() < end:
        QCoreApplication.processEvents()
        QTest.qWait(10)
    assert cond()


def wait_anim(canvas):
    wait_for(lambda: not canvas.busy)


def test_drag_to_bottom_emits_snapped_position(ctl):
    canvas = ctl.popup.canvas
    spy = QSignalSpy(canvas.position_chosen)
    r1, r2 = canvas.tile_rects()
    grab = r2.center().toPoint()
    target = QPoint(int(r1.center().x()), int(r1.bottom() + r2.height() / 2 + 3))
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, grab)
    assert canvas.cursor().shape() == Qt.CursorShape.ClosedHandCursor
    QTest.mouseMove(canvas, target)
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, target)
    wait_for(lambda: spy.count() == 1)
    x, y = spy.at(0)
    assert y == 1440  # below the primary
    assert x == (2560 - 1920) // 2  # magnet: centred


def test_drop_in_same_place_does_nothing(ctl):
    canvas = ctl.popup.canvas
    spy = QSignalSpy(canvas.position_chosen)
    _, r2 = canvas.tile_rects()
    canvas.drop(r2.topLeft() + QPointF(0.4, 0.4))
    wait_anim(canvas)
    assert spy.count() == 0 and ctl.fake.calls == []


def test_drop_applies_and_redraws_read_back(ctl):
    canvas = ctl.popup.canvas
    r1, r2 = canvas.tile_rects()
    canvas.drop(QPointF(r1.left() - r2.width() - 20, r1.top()))  # left, top-aligned
    wait_for(lambda: ctl.fake.calls != [])
    assert ctl.fake.calls == [(DEV, -1920, 0)]
    wait_anim(canvas)
    assert canvas.tile_rects()[0] == r1  # tile size unchanged although the revert bar is showing
    _, r2 = canvas.tile_rects()
    assert r2.right() == pytest.approx(r1.left(), abs=0.01)
    assert canvas._override is None
    assert ctl.popup.footer.text().startswith("Display 2: Left of 1")


def test_no_drag_while_disabled(ctl):
    canvas = ctl.popup.canvas
    canvas.drag_enabled = False
    _, r2 = canvas.tile_rects()
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, r2.center().toPoint())
    assert not canvas._dragging
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, r2.center().toPoint())
    canvas.drag_enabled = True
