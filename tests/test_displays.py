"""Read-only tests for the display backend — they never change the layout."""

import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows-only backend")

if sys.platform == "win32":
    from display_location import displays
    from display_location.displays import Display, DisplayStatus


def test_snapshot_has_status_and_sane_displays():
    snap = displays.snapshot()
    assert isinstance(snap.status, DisplayStatus)
    assert snap.all, "at least one active display expected"
    for d in snap.all:
        assert d.width > 0 and d.height > 0
        assert d.device_name.startswith("\\\\.\\")


def test_primary_is_at_origin():
    snap = displays.snapshot()
    assert snap.primary is not None
    assert (snap.primary.x, snap.primary.y) == (0, 0)


def test_secondary_only_when_ok():
    snap = displays.snapshot()
    if snap.status is DisplayStatus.OK:
        assert snap.secondary is not None and not snap.secondary.is_primary
    else:
        assert snap.secondary is None


def test_duplicate_check_does_not_raise():
    assert isinstance(displays._is_duplicated(), bool)


def test_set_position_rejects_primary_and_unknown():
    snap = displays.snapshot()
    with pytest.raises(displays.DisplayChangeError):
        displays.set_position(snap.primary.device_name, 100, 0)
    with pytest.raises(displays.DisplayChangeError):
        displays.set_position(r"\\.\DISPLAY99", 100, 0)


def test_error_message_mapping():
    with pytest.raises(displays.DisplayChangeError) as info:
        displays._check(-2, "Staging")
    assert info.value.code == -2
    assert "not supported" in str(info.value)


def test_format_snapshot_lists_primary_first():
    P = Display(r"\\.\DISPLAY1", "A", 0, 0, 1920, 1080, True)
    S = Display(r"\\.\DISPLAY2", "B", 0, 0, 1280, 1024, False)
    snap = displays.DisplaySnapshot(DisplayStatus.OK, P, S, (S, P))
    lines = displays.format_snapshot(snap).splitlines()
    assert lines[0] == "status: ok"
    assert lines[2].startswith("1") and "DISPLAY1" in lines[2]
    assert lines[3].startswith("2") and "DISPLAY2" in lines[3]
