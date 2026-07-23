"""Render an original, abstract project mark (no team livery, no series logo):
a lap loop with a live position marker, on the project's own dark card
background. Works as a small icon (GitHub social avatar, favicon-style use).

    python scripts/generate_logo.py
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"

BG_TOP = (11, 14, 20)      # #0B0E14
BG_BOTTOM = (5, 7, 12)
CYAN = (0, 217, 255)       # #00D9FF
RED = (225, 6, 0)          # #E10600
AMBER = (255, 184, 0)      # #FFB800


def _rounded_square_bg(size: int, radius: int) -> Image.Image:
    img = Image.new("RGB", (size, size), BG_TOP)
    px = img.load()
    for y in range(size):
        t = y / (size - 1)
        col = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3))
        for x in range(size):
            px[x, y] = col
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def make_logo(size: int = 512) -> Image.Image:
    img = _rounded_square_bg(size, radius=int(size * 0.20))
    draw = ImageDraw.Draw(img, "RGBA")

    cx, cy = size * 0.5, size * 0.52
    r = size * 0.28
    width = max(int(size * 0.045), 4)

    # the lap loop: a ring with a deliberate gap (pit entry), not a closed
    # circle -- avoids reading as a wheel/tyre and keeps it a "track" motif
    gap_start, gap_end = 25, 70  # degrees
    draw.arc(
        [cx - r, cy - r, cx + r, cy + r],
        start=gap_end, end=360 + gap_start,
        fill=(*CYAN, 255), width=width,
    )

    # position marker: a filled dot riding the loop, the live "car"
    marker_angle = math.radians(200)
    mx = cx + r * math.cos(marker_angle)
    my = cy + r * math.sin(marker_angle)
    mr = size * 0.052
    draw.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=RED)

    # a small amber tick just ahead of the marker: a pit-window flag
    tick_angle = math.radians(230)
    tx = cx + r * math.cos(tick_angle)
    ty = cy + r * math.sin(tick_angle)
    tw = size * 0.03
    draw.line(
        [(tx - tw, ty - tw), (tx + tw, ty + tw)],
        fill=AMBER, width=max(int(size * 0.018), 3),
    )

    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    logo = make_logo(512)
    logo.save(OUT / "logo.png")
    logo.resize((192, 192), Image.LANCZOS).save(OUT / "logo-192.png")
    logo.resize((32, 32), Image.LANCZOS).save(OUT / "logo-32.png")
    print("wrote", OUT / "logo.png", logo.size)


if __name__ == "__main__":
    main()
