"""Logging setup: rotating file log plus stderr when a console is attached (NFR-07)."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_MAX_BYTES = 1_000_000
LOG_BACKUP_COUNT = 3
LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"

log = logging.getLogger("display_location")


def log_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "DisplayLocation" / "logs"


def log_file() -> Path:
    return log_dir() / "app.log"


def _has_console() -> bool:
    # Under pythonw / a windowed PyInstaller exe, sys.stderr is None.
    stream = sys.stderr
    if stream is None:
        return False
    try:
        stream.fileno()
    except (AttributeError, OSError, ValueError):
        return False
    return True


def _excepthook(exc_type, exc_value, exc_tb) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    log.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))
    # TASK-006: if a revert countdown is active, attempt the revert here (NFR-06).


def setup_logging(level: int = logging.INFO) -> Path:
    """Configure the package logger once. Returns the log file path."""
    path = log_file()
    if getattr(log, "_display_location_configured", False):
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(LOG_FORMAT)

    file_handler = RotatingFileHandler(
        path, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    log.addHandler(file_handler)

    if _has_console():
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(formatter)
        log.addHandler(console)

    log.setLevel(level)
    log.propagate = False
    sys.excepthook = _excepthook
    log._display_location_configured = True  # type: ignore[attr-defined]
    return path
