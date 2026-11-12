"""Locate bundled files both from source and inside a PyInstaller bundle."""

from __future__ import annotations

import sys
from pathlib import Path


def base_dir() -> Path:
    """Folder that contains ``assets/``: the PyInstaller temp dir, or the project root."""
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        return Path(bundle)
    return Path(__file__).resolve().parents[2]  # src/display_location/ -> project root


def resource_path(relative: str) -> Path:
    return base_dir() / relative


def icon_path() -> Path:
    return resource_path("assets/icon.ico")
