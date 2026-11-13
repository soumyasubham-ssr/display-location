"""Identify displays overlays (TASK-009, FR-11). Uses fake screens where the real ones don't matter."""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QGuiApplication

from display_location.app import AppController
from display_location.displays import Display, DisplaySnapshot, DisplayStatus
from display_location.identify import BOX_SIZE, SHOW_MS, Identifier, IdentifyOverlay, centred, find_screen, numbered

P = Display(r"\\.\DISPLAY1", "Primary", 0, 0, 1920, 1080, True)
S = Display(r"\\.\DISPLAY5", "Second", 1920, 0, 1680, 1050, False)
OK = DisplaySnapshot(DisplayStatus.OK, P, S, (P, S))
SINGLE = DisplaySnapshot(DisplayStatus.SINGLE, P, None, (P,))
TOO_MANY = DisplaySnapshot(DisplayStatus.TOO_MANY, P, None, (P, S, S))


class FakeScreen:
    def __init__(self, name, rect, dpr=1.0):
        self._name, self._rect, self._dpr = name, rect, dpr

    def name(self):
        return self._name

    def geometry(self):
        return self._rect

    def devicePixelRatio(self):
        return self._dpr


# --------------------------------------------------------------------------- pure helpers


def test_numbering_matches_tiles():
    assert numbered(OK) == [("1", P), ("2", S)]
    assert numbered(SINGLE) == [("1", P)]
    assert numbered(TOO_MANY) == [("1", P)]


def test_find_by_name():
    a = FakeScreen(r"\\.\DISPLAY1", QRect(0, 0, 1920, 1080))
    b = FakeScreen(r"\\.\DISPLAY5", QRect(1920, 0, 1344, 840), 1.25)
    assert find_screen(S, [a, b]) is b
    assert find_screen(P, [a, b]) is a


def test_find_by_physical_size_when_names_differ(caplog):
    a = FakeScreen("A", QRect(0, 0, 1920, 1080))
    b = FakeScreen("B", QRect(1920, 0, 1344, 840), 1.25)  # 1680 × 1050 physical at 125 %
    with caplog.at_level("WARNING"):
        assert find_screen(S, [a, b]) is b
    assert "matched B by size" in caplog.text


def test_find_same_size_prefers_matching_primary():
    a = FakeScreen("A", QRect(0, 0, 1920, 1080))
    b = FakeScreen("B", QRect(1920, 0, 1920, 1080))
    s2 = Display("X", "Second", 1920, 0, 1920, 1080, False)
    assert find_screen(s2, [a, b], primary_screen=a) is b
    p2 = Display("Y", "Primary", 0, 0, 1920, 1080, True)
    assert find_screen(p2, [a, b], primary_screen=a) is a


def test_find_none():
    assert find_screen(S, [FakeScreen("A", QRect(0, 0, 800, 600))]) is None


def test_centred():
    assert centred(220, QRect(1920, -84, 1344, 840)) == QRect(1920 + 562, -84 + 310, 220, 220)


# --------------------------------------------------------------------------- overlay windows


def test_overlay_flags(qapp):
    o = IdentifyOverlay("1")
    flags = o.windowFlags()
    for f in (
        Qt.WindowType.FramelessWindowHint,
        Qt.WindowType.WindowStaysOnTopHint,
        Qt.WindowType.Tool,
        Qt.WindowType.WindowTransparentForInput,
    ):
        assert flags & f
    assert o.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert o.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    o.deleteLater()


@pytest.fixture
def ident(qapp):
    i = Identifier()
    yield i
    i.close()


def real_snapshot_for_screens():
    """A snapshot naming the real QScreens, so overlays land on real monitors."""
    screens = QGuiApplication.screens()
    primary = QGuiApplication.primaryScreen()
    others = [s for s in screens if s is not primary]

    def disp(s, is_primary):
        w, h = round(s.geometry().width() * s.devicePixelRatio()), round(s.geometry().height() * s.devicePixelRatio())
        return Display(s.name(), s.name(), 0, 0, w, h, is_primary)

    p = disp(primary, True)
    if not others:
        return DisplaySnapshot(DisplayStatus.SINGLE, p, None, (p,)), screens
    s = disp(others[0], False)
    return DisplaySnapshot(DisplayStatus.OK, p, s, (p, s)), screens


def test_show_centres_one_overlay_per_display(ident):
    snap, screens = real_snapshot_for_screens()
    ident.show(snap)
    for number, display in numbered(snap):
        o = ident.overlays[number]
        screen = next(s for s in screens if s.name() == display.device_name)
        assert o.isVisible()
        assert o.geometry() == centred(BOX_SIZE, screen.geometry())
    assert ident.timer.isActive() and ident.timer.interval() == SHOW_MS


def test_show_again_reuses_windows_and_restarts_timer(ident):
    snap, _ = real_snapshot_for_screens()
    ident.show(snap)
    first = dict(ident.overlays)
    ident.timer.stop()
    ident.show(snap)
    assert ident.overlays == first  # same window objects, no duplicates
    assert ident.timer.isActive()


def test_timeout_hides(ident):
    snap, _ = real_snapshot_for_screens()
    ident.show(snap)
    ident.timer.timeout.emit()
    assert not ident.visible


def test_single_shows_only_one(ident):
    snap, _ = real_snapshot_for_screens()
    single = DisplaySnapshot(DisplayStatus.SINGLE, snap.primary, None, (snap.primary,))
    ident.show(single)
    assert list(ident.overlays) == ["1"] and ident.overlays["1"].isVisible()


def test_two_hidden_when_monitor_2_gone(ident):
    snap, _ = real_snapshot_for_screens()
    if snap.secondary is None:
        pytest.skip("needs two real screens")
    ident.show(snap)
    single = DisplaySnapshot(DisplayStatus.SINGLE, snap.primary, None, (snap.primary,))
    ident.show(single)
    assert ident.overlays["1"].isVisible() and not ident.overlays["2"].isVisible()


# --------------------------------------------------------------------------- controller


def test_menu_identify_shows_overlays_without_touching_popup_snapshot(qapp):
    snap, _ = real_snapshot_for_screens()
    c = AppController(qapp, MagicMock(), MagicMock())
    c.snapshot_fn = MagicMock(return_value=snap)
    c.identify_displays()
    assert c.identifier.visible
    assert c.snapshot is None  # popup state untouched
    c.before_exit()
    assert c.identifier.overlays == {}
