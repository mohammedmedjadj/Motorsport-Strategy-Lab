"""Render the README banner and GitHub social-preview image directly with
Pillow (no cairosvg/rsvg-convert/Inkscape available in this environment).

Scattered pixel-mosaic style background: chunky rectangular blocks (not just
squares) in varying sizes, covering roughly 65% of the canvas along a
flowing dark-blue -> purple -> light-blue gradient, on plain white for the
rest. Inspired by the "Mistral" mosaic-gradient look but in this project's
own palette and with white negative space instead of full-bleed tiling.
Both raster images share one drawing routine parameterised by size and
layout, so the banner and the social preview never visually drift apart.
Run:

    python scripts/generate_banner.py
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
OUT = ROOT / "assets"

DARK_BLUE = (10, 14, 46)     # deep navy-indigo
LIGHT_BLUE = (130, 209, 255) # bright sky blue
PURPLE = (124, 58, 237)      # vivid violet
RED = (225, 6, 0)
WHITE = (255, 255, 255)
INK = (18, 20, 28)           # near-black text on the white ground
INK_SOFT = (74, 78, 92)

SEED = 20260723
CELL = 26
COVERAGE = 0.65
SHAPES = (
    (1, 1), (1, 1), (1, 1),
    (2, 1), (1, 2), (2, 1), (1, 2),
    (2, 2), (2, 2),
    (3, 1), (1, 3), (3, 2), (2, 3),
)


def _font(path: Path, size: int, weight: float | None = None) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(path), size)
    if weight is not None:
        f.set_variation_by_axes([weight])
    return f


SPACE_GROTESK = FONTS / "SpaceGrotesk-Bold.ttf"
INTER = FONTS / "Inter-Regular.ttf"
JBMONO = FONTS / "JetBrainsMono-Bold.ttf"


def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _gradient_color(u: float, v: float) -> tuple[int, int, int]:
    """3-stop diagonal gradient (dark blue -> purple -> light blue) with a
    gentle sinusoidal wobble so the bands flow instead of running dead
    straight."""
    diag = (u * 0.75 + v * 0.25)
    wobble = 0.07 * math.sin(v * math.pi * 2.2 + u * 1.5)
    t = max(0.0, min(1.0, diag + wobble))
    if t < 0.5:
        return _lerp(DARK_BLUE, PURPLE, t / 0.5)
    return _lerp(PURPLE, LIGHT_BLUE, (t - 0.5) / 0.5)


def _scatter_blocks(w: int, h: int, keepouts: list[tuple[int, int, int, int]],
                     cell: int = CELL, coverage: float = COVERAGE) -> list[tuple[int, int, int, int, tuple[int, int, int]]]:
    """Pack random 1-3 cell rectangles onto a grid until ~coverage of the
    full canvas is filled, skipping any cell that falls inside a keepout
    rect (reserved for text). Returns (x, y, w, h, color) in pixels."""
    rng = random.Random(SEED)
    cols, rows = math.ceil(w / cell), math.ceil(h / cell)

    def in_keepout(c: int, r: int) -> bool:
        x0, y0 = c * cell, r * cell
        x1, y1 = x0 + cell, y0 + cell
        for kx0, ky0, kx1, ky1 in keepouts:
            if x0 < kx1 and x1 > kx0 and y0 < ky1 and y1 > ky0:
                return True
        return False

    occupied = [[in_keepout(c, r) for c in range(cols)] for r in range(rows)]
    target_cells = int(cols * rows * coverage)
    filled = 0  # keepout cells are pre-marked occupied but don't count toward the budget

    positions = [(r, c) for r in range(rows) for c in range(cols)]
    rng.shuffle(positions)

    blocks: list[tuple[int, int, int, int, tuple[int, int, int]]] = []
    for r, c in positions:
        if filled >= target_cells:
            break
        if occupied[r][c]:
            continue
        shapes = list(SHAPES)
        rng.shuffle(shapes)
        for bw, bh in shapes:
            if c + bw > cols or r + bh > rows:
                continue
            if any(occupied[rr][cc] for rr in range(r, r + bh) for cc in range(c, c + bw)):
                continue
            for rr in range(r, r + bh):
                for cc in range(c, c + bw):
                    occupied[rr][cc] = True
            filled += bw * bh
            px0, py0 = c * cell, r * cell
            pw, ph = bw * cell, bh * cell
            u = (px0 + pw / 2) / w
            v = (py0 + ph / 2) / h
            col = _gradient_color(u, v)
            jitter = rng.uniform(-0.08, 0.08)
            col = tuple(max(0, min(255, int(ch * (1 + jitter)))) for ch in col)
            blocks.append((px0, py0, pw, ph, col))
            break
    return blocks


def _draw_blocks(img: Image.Image, blocks: list[tuple[int, int, int, int, tuple[int, int, int]]]) -> None:
    draw = ImageDraw.Draw(img)
    for x, y, bw, bh, col in blocks:
        draw.rectangle([x, y, x + bw - 1, y + bh - 1], fill=col)


def _stat_card(draw, x, y, w, h, number, label):
    draw.rectangle([x, y, x + w, y + h], outline=(210, 213, 222), width=1, fill=WHITE)
    num_font = _font(JBMONO, 22, weight=700)
    lbl_font = _font(JBMONO, 11, weight=500)
    draw.text((x + 14, y + 10), number, font=num_font, fill=RED)
    draw.text((x + 14, y + h - 26), label, font=lbl_font, fill=INK_SOFT)


def make_banner(w: int, h: int, centered: bool, tag: str | None = None) -> Image.Image:
    img = Image.new("RGB", (w, h), WHITE)
    draw = ImageDraw.Draw(img)

    title = "MOTORSPORT STRATEGY LAB"
    subtitle = "Bayesian & Monte Carlo Race Strategy Research — F1 · WEC · IMSA"

    title_size = 46 if not centered else 52
    title_font = _font(SPACE_GROTESK, title_size, weight=700)
    subtitle_font = _font(INTER, 19 if not centered else 21, weight=400)
    margin = 60

    # compute text keepout rects up front so the mosaic never overlaps them
    keepouts: list[tuple[int, int, int, int]] = []
    if not centered:
        top = h * 0.30
        tb = draw.textbbox((0, 0), title, font=title_font)
        sb = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        text_right = margin + max(tb[2] - tb[0], sb[2] - sb[0]) + 14
        keepouts.append((0, int(top) - 10, int(text_right), int(top) + title_size + 42))
        stats = [("3", "SERIES"), ("140+", "TESTS"), ("5", "AUDITED RACES")]
        card_w, card_h, gap = 150, 78, 16
        total_w = card_w * 3 + gap * 2
        start_x = w - margin - total_w
        start_y = top + title_size + 14 + 46
        keepouts.append((int(start_x) - 10, int(start_y) - 10, w, int(start_y + card_h) + 10))
    else:
        tb = draw.textbbox((0, 0), title, font=title_font)
        tw = tb[2] - tb[0]
        sb = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        sw = sb[2] - sb[0]
        top = h * 0.36
        keepouts.append((int((w - max(tw, sw)) / 2) - 14, int(top) - 18,
                          int((w + max(tw, sw)) / 2) + 14, int(top) + title_size + 34))
        if tag:
            tag_font = _font(JBMONO, 14, weight=500)
            tgb = draw.textbbox((0, 0), tag, font=tag_font)
            tgw = tgb[2] - tgb[0]
            keepouts.append((int((w - tgw) / 2) - 10, h - 56, int((w + tgw) / 2) + 10, h - 26))

    blocks = _scatter_blocks(w, h, keepouts)
    _draw_blocks(img, blocks)

    if not centered:
        draw.text((margin, h * 0.30), title, font=title_font, fill=INK)
        draw.text((margin, h * 0.30 + title_size + 14), subtitle, font=subtitle_font, fill=INK_SOFT)
        stats = [("3", "SERIES"), ("140+", "TESTS"), ("5", "AUDITED RACES")]
        card_w, card_h, gap = 150, 78, 16
        total_w = card_w * 3 + gap * 2
        start_x = w - margin - total_w
        start_y = h * 0.30 + title_size + 14 + 46
        for i, (num, lbl) in enumerate(stats):
            _stat_card(draw, start_x + i * (card_w + gap), start_y, card_w, card_h, num, lbl)
    else:
        tb = draw.textbbox((0, 0), title, font=title_font)
        tw = tb[2] - tb[0]
        draw.text(((w - tw) / 2, h * 0.36), title, font=title_font, fill=INK)
        sb = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        sw = sb[2] - sb[0]
        draw.text(((w - sw) / 2, h * 0.36 + title_size + 22), subtitle, font=subtitle_font, fill=INK_SOFT)
        if tag:
            tag_font = _font(JBMONO, 14, weight=500)
            tgb = draw.textbbox((0, 0), tag, font=tag_font)
            tgw = tgb[2] - tgb[0]
            draw.text(((w - tgw) / 2, h - 46), tag, font=tag_font, fill=INK_SOFT)

    # thin red accent underline beneath the title, a nod to a start-lights bar
    accent_y = int(h * 0.30) - 14 if not centered else int(h * 0.36) - 16
    accent_x0 = margin if not centered else (w - 220) / 2
    accent_w = 90 if not centered else 220
    draw.rectangle([accent_x0, accent_y, accent_x0 + accent_w, accent_y + 4], fill=RED)

    return img


def make_banner_svg(w: int, h: int) -> str:
    """Vector source counterpart of make_banner(w, h, centered=False): same
    block layout, same RNG seed, so it can't visually drift from the PNG."""
    title = "MOTORSPORT STRATEGY LAB"
    subtitle_plain = "Bayesian & Monte Carlo Race Strategy Research — F1 · WEC · IMSA"
    subtitle = "Bayesian &amp; Monte Carlo Race Strategy Research — F1 · WEC · IMSA"
    margin = 60
    title_size = 46

    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    tb = dummy.textbbox((0, 0), title, font=_font(SPACE_GROTESK, title_size, weight=700))
    sb = dummy.textbbox((0, 0), subtitle_plain, font=_font(INTER, 19, weight=400))
    text_right = margin + max(tb[2] - tb[0], sb[2] - sb[0]) + 30

    top = h * 0.30
    keepouts = [(0, int(top) - 10, int(text_right), int(top) + title_size + 42)]
    card_w, card_h, gap = 150, 78, 16
    total_w = card_w * 3 + gap * 2
    start_x = w - margin - total_w
    start_y = top + title_size + 14 + 46
    keepouts.append((int(start_x) - 10, int(start_y) - 10, w, int(start_y + card_h) + 10))

    blocks = _scatter_blocks(w, h, keepouts)
    rects = "".join(
        f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="#{c[0]:02x}{c[1]:02x}{c[2]:02x}"/>'
        for x, y, bw, bh, c in blocks
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img"
     aria-label="Motorsport Strategy Lab -- Bayesian and Monte Carlo race strategy research across F1, WEC and IMSA">
  <title>Motorsport Strategy Lab</title>
  <rect width="{w}" height="{h}" fill="#ffffff"/>
  <g>{rects}</g>
  <rect x="{margin}" y="76" width="90" height="4" fill="#E10600"/>
  <text x="{margin}" y="140" font-family="Space Grotesk, Arial, sans-serif" font-weight="700"
        font-size="46" fill="#12141C" letter-spacing="0.5">{title}</text>
  <text x="{margin}" y="172" font-family="Inter, Arial, sans-serif" font-weight="400"
        font-size="19" fill="#4A4E5C">{subtitle}</text>
  <g font-family="JetBrains Mono, Consolas, monospace">
    <g><rect x="658" y="200" width="150" height="78" fill="#ffffff" stroke="#D2D5DE"/>
      <text x="672" y="228" font-size="22" font-weight="700" fill="#E10600">3</text>
      <text x="672" y="264" font-size="11" fill="#4A4E5C">SERIES</text></g>
    <g><rect x="824" y="200" width="150" height="78" fill="#ffffff" stroke="#D2D5DE"/>
      <text x="838" y="228" font-size="22" font-weight="700" fill="#E10600">140+</text>
      <text x="838" y="264" font-size="11" fill="#4A4E5C">TESTS</text></g>
    <g><rect x="990" y="200" width="150" height="78" fill="#ffffff" stroke="#D2D5DE"/>
      <text x="1004" y="228" font-size="22" font-weight="700" fill="#E10600">5</text>
      <text x="1004" y="264" font-size="11" fill="#4A4E5C">AUDITED RACES</text></g>
  </g>
</svg>
'''


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    banner = make_banner(1200, 300, centered=False)
    banner.save(OUT / "banner.png")
    social = make_banner(
        1280, 640, centered=True,
        tag="github.com/mohammedmedjadj/Motorsport-Strategy-Lab",
    )
    social.save(OUT / "social-preview.png")
    (OUT / "banner.svg").write_text(make_banner_svg(1200, 300), encoding="utf-8")
    print("wrote", OUT / "banner.png", banner.size)
    print("wrote", OUT / "social-preview.png", social.size)
    print("wrote", OUT / "banner.svg")


if __name__ == "__main__":
    main()
