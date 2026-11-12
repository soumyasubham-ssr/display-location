"""Entry point: ``python -m display_location``.

Absolute imports only — PyInstaller runs this file as a top-level script.
"""

import argparse
import sys

from display_location import __version__

SIDES = ("left", "right", "top", "bottom")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="display_location",
        description="Move the second monitor around the primary from the system tray.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--list", action="store_true", help="print the active displays and exit")
    group.add_argument(
        "--side",
        choices=SIDES,
        help="developer tool: move monitor 2 to this side of monitor 1, centred (NO revert)",
    )
    return parser.parse_args(argv)


def _cli_list() -> int:
    from display_location import displays

    print(displays.format_snapshot(displays.snapshot()))
    return 0


def _cli_side(side: str) -> int:
    from display_location import displays
    from display_location.log_setup import setup_logging

    setup_logging()
    snap = displays.snapshot()
    if snap.status is not displays.DisplayStatus.OK:
        print(displays.format_snapshot(snap))
        print(f"error: need exactly two extended displays (status: {snap.status.value})", file=sys.stderr)
        return 2
    x, y = displays.centred_position(snap.primary, snap.secondary, side)
    try:
        displays.set_position(snap.secondary.device_name, x, y)
    except displays.DisplayChangeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(displays.format_snapshot(displays.snapshot()))
    return 0


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.list:
        return _cli_list()
    if args.side:
        return _cli_side(args.side)

    from display_location.app import main

    return main()


if __name__ == "__main__":
    sys.exit(run())
