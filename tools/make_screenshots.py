"""Render the README screenshots from the real widgets (no display changes).

    python tools/make_screenshots.py

Writes PNGs to docs/images/. Uses made-up monitor sizes so the pictures don't
depend on the machine that runs it.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QPoint, QRect, Qt  # noqa: E402
from PySide6.QtGui import QColor, QIcon, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from display_location.displays import Display, DisplaySnapshot, DisplayStatus  # noqa: E402
from display_location.identify import IdentifyOverlay  # noqa: E402
from display_location.popup import Popup  # noqa: E402
from display_location.resources import icon_path  # noqa: E402
from display_location.tray import TrayIcon  # noqa: E402

OUT = ROOT / "docs" / "images"
SCALE = 2  # render at 2× for crisp images on high-DPI screens

P = Display(r"\\.\DISPLAY1", "Main", 0, 0, 2560, 1440, True)


def snap(x: int, y: int, w: int = 1920, h: int = 1080) -> DisplaySnapshot:
    s = Display(r"\\.\DISPLAY2", "Second", x, y, w, h, False)
    return DisplaySnapshot(DisplayStatus.OK, P, s, (P, s))


def grab(widget, name: str) -> None:
    widget.ensurePolished()
    widget.adjustSize()
    img = QImage(widget.size() * SCALE, QImage.Format.Format_ARGB32_Premultiplied)
    img.setDevicePixelRatio(SCALE)
    img.fill(Qt.GlobalColor.transparent)
    widget.render(img, QPoint(), widget.rect())
    path = OUT / name
    img.save(str(path))
    print(f"wrote {path.relative_to(ROOT)}")


def popup_shot(name: str, snapshot: DisplaySnapshot, revert: int | None = None) -> None:
    popup = Popup()
    popup.refresh(snapshot)
    if revert is not None:
        popup.show_revert(revert)
    popup.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    popup.show()  # lay out without appearing on screen
    QApplication.processEvents()
    grab(popup, name)
    popup.close()


def identify_shot() -> None:
    """Both overlays side by side on a dark strip, as a stand-in for two monitors."""
    tiles = []
    for n in ("1", "2"):
        o = IdentifyOverlay(n)
        o.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        o.show()
        QApplication.processEvents()
        img = QImage(o.size() * SCALE, QImage.Format.Format_ARGB32_Premultiplied)
        img.setDevicePixelRatio(SCALE)
        img.fill(Qt.GlobalColor.transparent)
        o.render(img, QPoint(), o.rect())
        tiles.append(img)
        o.close()
    # Two monitors in proportion (2560×1440 and 1920×1080 at 1/4), the box at the same 1/4 scale
    # it would have on a real 100 % screen (220 px), so the picture looks like the real thing.
    k = 0.25
    screens = [QRect(0, 0, int(2560 * k), int(1440 * k)), QRect(int(2560 * k) + 24, int(360 * k), int(1920 * k), int(1080 * k))]
    w, h = screens[1].right() + 1, screens[0].height()
    out = QImage(w * SCALE, h * SCALE, QImage.Format.Format_ARGB32_Premultiplied)
    out.setDevicePixelRatio(SCALE)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    box = int(220 * k * 1.6)  # a little larger than true scale so the number stays readable
    for i, (img, screen) in enumerate(zip(tiles, screens)):
        p.setPen(QColor("#3a3a3a"))
        p.setBrush(QColor("#1b3a5c") if i == 0 else QColor("#1f4d4a"))  # stand-in wallpapers
        p.drawRoundedRect(screen, 6, 6)
        c = screen.center()
        p.drawImage(QRect(c.x() - box // 2, c.y() - box // 2, box, box), img)
    p.end()
    path = OUT / "identify.png"
    out.save(str(path))
    print(f"wrote {path.relative_to(ROOT)}")


def menu_shot() -> None:
    tray = TrayIcon(QIcon(str(icon_path())))
    tray.autostart_state = lambda: True
    tray._refresh_menu()
    menu = tray.menu
    menu.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    menu.show()
    QApplication.processEvents()
    grab(menu, "tray-menu.png")
    menu.hide()


def logo_shot() -> None:
    """256 px README logo from the owner's artwork (assets/icon-source.png, D-015)."""
    src = QImage(str(ROOT / "assets" / "icon-source.png"))
    logo = src.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    path = OUT / "logo.png"
    logo.save(str(path))
    print(f"wrote {path.relative_to(ROOT)}")


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    OUT.mkdir(parents=True, exist_ok=True)
    logo_shot()
    popup_shot("popup-right.png", snap(2560, 180))
    popup_shot("popup-below.png", snap(320, 1440))
    popup_shot("popup-revert.png", snap(-1920, 0), revert=8)
    identify_shot()
    menu_shot()
    app.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
