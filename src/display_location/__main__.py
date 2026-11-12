"""Entry point: ``python -m display_location``.

Absolute imports only — PyInstaller runs this file as a top-level script.
"""

import argparse
import sys

from display_location import __version__


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="display_location",
        description="Move the second monitor around the primary from the system tray.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    # --list and --side are added in TASK-002.
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    parse_args(argv)
    from display_location.app import main

    return main()


if __name__ == "__main__":
    sys.exit(run())
