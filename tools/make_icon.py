"""Regenerate assets/icon.ico from the owner's artwork, assets/icon-source.png (D-015).

Usage:  python tools/make_icon.py
Crops the artwork to its visible pixels, centres it on a transparent square and
writes a multi-size .ico (16 ... 256 px). Requires Pillow (dev dependency).
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "icon-source.png"
TARGET = ROOT / "assets" / "icon.ico"
SIZES = [16, 20, 24, 32, 40, 48, 64, 256]
ALPHA_CUTOFF = 16  # ignore near-transparent fringe pixels when cropping


def square_master(src: Path) -> Image.Image:
    im = Image.open(src).convert("RGBA")
    alpha = im.getchannel("A").point(lambda a: 255 if a > ALPHA_CUTOFF else 0)
    im = im.crop(alpha.getbbox())
    side = max(im.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - im.width) // 2, (side - im.height) // 2), im)
    return canvas


def main() -> None:
    master = square_master(SOURCE)
    master.resize((256, 256), Image.LANCZOS).save(TARGET, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"wrote {TARGET.relative_to(ROOT)} ({', '.join(map(str, SIZES))} px)")


if __name__ == "__main__":
    main()
