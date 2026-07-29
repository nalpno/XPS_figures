"""Generate assets/xps.ico - the desktop shortcut icon.

Run once after changing the design:  python tools/make_icon.py
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 1024                     # drawn large, then downsampled for each icon size
SCALE = SIZE / 256.0
BACKGROUND = (43, 95, 203, 255)  # the app's primary blue
CURVE = (255, 255, 255, 255)
FILL = (179, 157, 219, 255)      # the pastel violet used for fitted components

ICON_SIZES = [(s, s) for s in (16, 24, 32, 48, 64, 128, 256)]


def rounded_background(draw: ImageDraw.ImageDraw) -> None:
    draw.rounded_rectangle(
        [(0, 0), (SIZE - 1, SIZE - 1)], radius=int(48 * SCALE), fill=BACKGROUND
    )


def spectrum(x: float) -> float:
    """A small XPS-like doublet on a sloping background, normalised to 0..1."""
    def gauss(center: float, width: float, height: float) -> float:
        return height * math.exp(-((x - center) ** 2) / (2 * width ** 2))

    return gauss(0.36, 0.055, 0.62) + gauss(0.62, 0.075, 0.95) + 0.10 * (1 - x)


def main() -> None:
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    rounded_background(draw)

    left, right = 0.14 * SIZE, 0.86 * SIZE
    baseline, top = 0.80 * SIZE, 0.22 * SIZE

    points = []
    steps = 400
    for i in range(steps + 1):
        t = i / steps
        px = left + (right - left) * t
        py = baseline - (baseline - top) * spectrum(t)
        points.append((px, py))

    draw.polygon(points + [(right, baseline), (left, baseline)], fill=FILL)
    draw.line(points, fill=CURVE, width=int(11 * SCALE), joint="curve")
    draw.line([(left, baseline), (right, baseline)], fill=CURVE, width=int(9 * SCALE))

    out = Path(__file__).resolve().parent.parent / "assets" / "xps.ico"
    out.parent.mkdir(exist_ok=True)
    image.save(out, format="ICO", sizes=ICON_SIZES)
    print(f"{out} yazıldı ({out.stat().st_size / 1024:.1f} kB)")


if __name__ == "__main__":
    main()
