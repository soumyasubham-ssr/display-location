"""Live refresh on display changes (TASK-008, FR-14). No real display changes."""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from display_location import log_setup
from display_location.app import DISPLAY_DEBOUNCE_MS, AppController
from display_location.displays import Display, DisplaySnapshot, DisplayStatus
from display_location.popup import STATUS_MESSAGES

from tests.test_revert import DEV, P, FakeDisplays, wait_anim, wait_for


class CountingFake(FakeDisplays):
    """FakeDisplays that counts snapshots and can drop / duplicate the secondary."""

    def __init__(self):
        super().__init__()
        self.snapshots = 0
        self.status = DisplayStatus.OK
        self.size = (1920, 1080)

    def snapshot(self):
        self.snapshots += 1
        if self.status is DisplayStatus.SINGLE:
            return DisplaySnapshot(DisplayStatus.SINGLE, P, None, (P,))
        if self.status is DisplayStatus.DUPLICATE:
            return DisplaySnapshot(DisplayStatus.DUPLICATE, P, None, (P,))
        s = Display(DEV, "Second", *self.pos, *self.size, False)
        return DisplaySnapshot(DisplayStatus.OK, P, s, (P, s))


@pytest.fixture
def ctl(qapp):
    fake = CountingFake()
    c = AppController(qapp, MagicMock(), MagicMock())
    c.snapshot_fn, c.set_position_fn = fake.snapshot, fake.set_position
    c.fake = fake
    c.toggle_popup()
    c.popup.canvas.resize(328, 150)
    fake.snapshots = 0
    yield c
    c._display_timer.stop()
    c.revert._clear()
    c.popup.close()
    c.popup.deleteLater()
    log_setup.crash_handler = None


def settle(ctl):
    """Wait past the debounce."""
    QTest.qWait(DISPLAY_DEBOUNCE_MS + 50)
    wait_for(lambda: not ctl._display_timer.isActive())


def test_burst_of_signals_gives_one_snapshot(ctl):
    for _ in range(5):
        ctl.schedule_display_refresh()
    assert ctl.fake.snapshots == 0  # nothing until the burst is over
    settle(ctl)
    assert ctl.fake.snapshots == 1


def test_no_timer_while_idle(ctl):
    assert not ctl._display_timer.isActive()


def test_moved_in_settings_moves_tile(ctl):
    ctl.fake.pos = (-1920, 0)
    ctl.schedule_display_refresh()
    settle(ctl)
    wait_anim(ctl.popup.canvas)
    r1, r2 = ctl.popup.canvas.tile_rects()
    assert r2.right() == pytest.approx(r1.left(), abs=0.01)
    assert ctl.popup.footer.text().startswith("Display 2: Left of 1")


def test_resolution_change_resizes_tile(ctl):
    _, before = ctl.popup.canvas.tile_rects()
    ctl.fake.size = (1280, 720)
    ctl.schedule_display_refresh()
    settle(ctl)
    _, after = ctl.popup.canvas.tile_rects()
    assert after.width() < before.width()
    assert "1280 × 720" in ctl.popup.footer.text()


def test_unplug_and_replug(ctl):
    ctl.fake.status = DisplayStatus.SINGLE
    ctl.schedule_display_refresh()
    settle(ctl)
    assert ctl.popup.stack.currentWidget() is ctl.popup.message
    assert ctl.popup.message.text() == STATUS_MESSAGES[DisplayStatus.SINGLE]
    ctl.fake.status = DisplayStatus.OK
    ctl.schedule_display_refresh()
    settle(ctl)
    assert ctl.popup.stack.currentWidget() is ctl.popup.canvas


def test_duplicate_message(ctl):
    ctl.fake.status = DisplayStatus.DUPLICATE
    ctl.schedule_display_refresh()
    settle(ctl)
    assert ctl.popup.message.text() == STATUS_MESSAGES[DisplayStatus.DUPLICATE]


def test_unplug_during_countdown_cancels_it(ctl):
    ctl.apply_position(0, 1440)
    assert ctl.revert.active
    ctl.fake.status = DisplayStatus.SINGLE
    ctl.schedule_display_refresh()
    settle(ctl)
    assert not ctl.revert.active
    assert ctl.popup.revert_bar.isHidden()
    assert ctl.fake.calls == [(DEV, 0, 1440)]  # no revert attempted


def test_unplug_cancels_countdown_with_popup_closed(ctl):
    ctl.apply_position(0, 1440)
    ctl.popup.close()
    ctl.fake.status = DisplayStatus.SINGLE
    ctl.schedule_display_refresh()
    settle(ctl)
    assert not ctl.revert.active


def test_primary_swapped_during_countdown_cancels_it(ctl):
    """Owner makes the moved monitor the main one before Keep: Windows can't move a primary."""
    ctl.apply_position(0, 1440)
    swapped_p = Display(DEV, "Second", 0, 0, 1920, 1080, True)
    swapped_s = Display(P.device_name, "Primary", 1920, 0, 2560, 1440, False)
    ctl.snapshot_fn = lambda: DisplaySnapshot(DisplayStatus.OK, swapped_p, swapped_s, (swapped_p, swapped_s))
    ctl.schedule_display_refresh()
    settle(ctl)
    assert not ctl.revert.active
    assert ctl.fake.calls == [(DEV, 0, 1440)]  # no revert attempted


def test_own_move_refresh_is_harmless(ctl):
    ctl.apply_position(0, 1440)
    calls, seconds = list(ctl.fake.calls), ctl.revert.seconds_left
    ctl.revert._on_tick()  # one second passes
    ctl.schedule_display_refresh()  # Windows' signals from our own move
    settle(ctl)
    assert ctl.fake.calls == calls  # no extra apply
    assert ctl.revert.seconds_left == seconds - 1  # countdown not restarted
    assert ctl.revert.previous == (2560, 180)


def test_refresh_waits_for_drag_to_end(ctl):
    canvas = ctl.popup.canvas
    _, r2 = canvas.tile_rects()
    grab = r2.center().toPoint()
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, grab)
    ctl.fake.status = DisplayStatus.SINGLE
    ctl.schedule_display_refresh()
    QTest.qWait(DISPLAY_DEBOUNCE_MS + 100)
    assert canvas._dragging  # not interrupted
    assert ctl.popup.stack.currentWidget() is canvas
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, grab)
    wait_anim(canvas)
    settle(ctl)
    assert ctl.popup.stack.currentWidget() is ctl.popup.message


def test_exit_stops_refresh(ctl):
    ctl.schedule_display_refresh()
    ctl.before_exit()
    assert not ctl._display_timer.isActive()
    ctl._exiting = False  # let the fixture tear down normally
