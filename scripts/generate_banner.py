"""Render the README banner and GitHub social-preview image directly with
Pillow (no cairosvg/rsvg-convert/Inkscape available in this environment).

Pixel-mosaic background, split by the rectangle's own diagonal into two
right triangles: the upper-right triangle (most of the right side, plus a
chunk of the middle) is tiled with chunky rectangular mosaic blocks in a
flowing dark-blue -> purple -> light-blue gradient; the lower-left triangle
(where the title text sits) is plain white. Text still gets a minimal, tight
safety clearing in case a block's corner grazes the boundary near it. Both
raster images share one drawing routine parameterised by size and layout, so
the banner and the social preview never visually drift apart. Run:

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
LIGHT_BLUE = (36, 140, 224)  # punchy azure
PURPLE = (124, 58, 237)      # vivid violet
RED = (225, 6, 0)
WHITE = (255, 255, 255)
INK = (18, 20, 28)           # near-black text on the white ground
INK_SOFT = (74, 78, 92)

SEED = 20260723
CELL = 36
SHAPES = (
    (1, 1), (1, 1), (1, 1),
    (2, 1), (1, 2), (2, 1), (1, 2),
    (2, 2), (2, 2),
    (3, 1), (1, 3), (3, 2), (2, 3),
)

# (x0, y0, x1, y1, fade_radius_px) -- a hard-clear rect that smoothly fades
# back up to full density over `fade_radius_px` beyond its edge.
Void = tuple[float, float, float, float, float]


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
    """3-stop gradient across the pixel triangle: light blue at the far
    corner (deepest into the triangle, away from the text), through purple,
    down to dark blue right at the boundary with the white triangle."""
    t = max(0.0, min(1.0, u * 0.6 + v * 0.4))
    if t < 0.5:
        return _lerp(LIGHT_BLUE, PURPLE, t / 0.5)
    return _lerp(PURPLE, DARK_BLUE, (t - 0.5) / 0.5)


def _smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


DEADZONE = 8  # px of guaranteed-pure-white just beyond a void's core rect,
               # so no fade-tinted pixel ever sits under the text itself
TEXT_CLEAR_RADIUS = 14  # tight -- a safety margin, not a dissolve halo


def _whiteness_at(x: float, y: float, voids: list[Void]) -> float:
    """0 = full-strength mosaic colour, 1 = pure white, from proximity to a
    text-clearing void. Smallest (most-white) value wins across overlaps."""
    whiteness = 0.0
    for x0, y0, x1, y1, radius in voids:
        dx = max(x0 - x, 0.0, x - x1)
        dy = max(y0 - y, 0.0, y - y1)
        dist = max(0.0, math.hypot(dx, dy) - DEADZONE)
        local_white = 1.0 - (_smoothstep(dist / radius) if radius > 0 else (0.0 if dist > 0 else 1.0))
        whiteness = max(whiteness, local_white)
    return whiteness


def _diagonal_whiteness(x: float, y: float, w: float, h: float) -> float:
    """Split the rectangle along its own diagonal (top-left to bottom-right)
    into two right triangles: 0 (full colour) in the upper-right triangle,
    1 (white) in the lower-left one where the title text lives. A few
    pixels of antialiasing at the boundary, not a wide fade -- this is meant
    to read as a clean triangle, not a gradient."""
    boundary_y = x * (h / w)
    return 0.0 if y < boundary_y - 3 else (1.0 if y > boundary_y + 3 else (y - (boundary_y - 3)) / 6)


def _tile_blocks(w: int, h: int, voids: list[Void], cell: int = CELL) -> list[tuple[int, int, int, int, tuple[int, int, int]]]:
    """Pack varying-size rectangles (1-3 cells) over the *entire* canvas --
    full coverage, no gaps -- then flip each block to white if it falls in
    the lower-left triangle (plus a tight text-clearing safety margin),
    leaving the upper-right triangle as solid mosaic colour. Returns
    (x, y, w, h, color) in pixels."""
    rng = random.Random(SEED)
    cols, rows = math.ceil(w / cell), math.ceil(h / cell)
    occupied = [[False] * cols for _ in range(rows)]

    positions = [(r, c) for r in range(rows) for c in range(cols)]
    rng.shuffle(positions)

    blocks: list[tuple[int, int, int, int, tuple[int, int, int]]] = []
    for r, c in positions:
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
            px0, py0 = c * cell, r * cell
            pw, ph = bw * cell, bh * cell
            cx, cy = px0 + pw / 2, py0 + ph / 2
            col = _gradient_color(cx / w, cy / h)
            jitter = rng.uniform(-0.08, 0.08)
            col = tuple(max(0, min(255, int(ch * (1 + jitter)))) for ch in col)
            whiteness = max(_diagonal_whiteness(cx, cy, w, h), _whiteness_at(cx, cy, voids))
            col = _lerp(col, WHITE, whiteness)
            blocks.append((px0, py0, pw, ph, col))
            break
    return blocks


def _draw_blocks(img: Image.Image, blocks: list[tuple[int, int, int, int, tuple[int, int, int]]]) -> None:
    draw = ImageDraw.Draw(img)
    for x, y, bw, bh, col in blocks:
        draw.rectangle([x, y, x + bw - 1, y + bh - 1], fill=col)


def _stat_label(draw, x, y, number, label):
    num_font = _font(JBMONO, 22, weight=700)
    lbl_font = _font(JBMONO, 11, weight=500)
    draw.text((x, y), number, font=num_font, fill=RED)
    draw.text((x, y + 30), label, font=lbl_font, fill=INK_SOFT)


def _stat_layout(draw, stats: list[tuple[str, str]], right_edge: float, gap: float = 34):
    """Right-align a row of (number, label) stats with real measured widths,
    so items never overlap regardless of label length."""
    num_font = _font(JBMONO, 22, weight=700)
    lbl_font = _font(JBMONO, 11, weight=500)
    widths = []
    for num, lbl in stats:
        nb = draw.textbbox((0, 0), num, font=num_font)
        lb = draw.textbbox((0, 0), lbl, font=lbl_font)
        widths.append(max(nb[2] - nb[0], lb[2] - lb[0]))
    total = sum(widths) + gap * (len(stats) - 1)
    xs = []
    x = right_edge - total
    for wdt in widths:
        xs.append(x)
        x += wdt + gap
    return xs, widths


def make_banner(w: int, h: int, centered: bool, tag: str | None = None) -> Image.Image:
    img = Image.new("RGB", (w, h), WHITE)
    draw = ImageDraw.Draw(img)

    title = "MOTORSPORT STRATEGY LAB"
    subtitle = "Bayesian & Monte Carlo Race Strategy Research — F1 · WEC · IMSA"

    title_size = 46 if not centered else 52
    title_font = _font(SPACE_GROTESK, title_size, weight=700)
    subtitle_font = _font(INTER, 19 if not centered else 21, weight=400)
    margin = 60

    voids: list[Void] = []
    if not centered:
        top = h * 0.30
        tb = draw.textbbox((0, 0), title, font=title_font)
        sb = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        # separate voids per text line -- lets the mosaic show through the
        # gap between title and subtitle instead of one big blank rectangle
        voids.append((0, top - 4, margin + (tb[2] - tb[0]), top + title_size + 2, TEXT_CLEAR_RADIUS))
        sub_top = top + title_size + 14
        voids.append((0, sub_top - 2, margin + (sb[2] - sb[0]), sub_top + 22, TEXT_CLEAR_RADIUS))

        stats = [("3", "SERIES"), ("140+", "TESTS"), ("289", "RACE-SEASONS")]
        start_y = top + title_size + 14 + 46
        stat_xs, stat_ws = _stat_layout(draw, stats, w - margin)
        for sx, sw in zip(stat_xs, stat_ws):
            voids.append((sx - 6, start_y - 6, sx + sw + 6, start_y + 46, TEXT_CLEAR_RADIUS))
    else:
        tb = draw.textbbox((0, 0), title, font=title_font)
        tw = tb[2] - tb[0]
        sb = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        sw = sb[2] - sb[0]
        top = h * 0.36
        voids.append(((w - tw) / 2, top - 4, (w + tw) / 2, top + title_size + 2, TEXT_CLEAR_RADIUS))
        sub_top = top + title_size + 22
        voids.append(((w - sw) / 2, sub_top - 2, (w + sw) / 2, sub_top + 24, TEXT_CLEAR_RADIUS))
        if tag:
            tag_font = _font(JBMONO, 14, weight=500)
            tgb = draw.textbbox((0, 0), tag, font=tag_font)
            tgw = tgb[2] - tgb[0]
            voids.append(((w - tgw) / 2, h - 50, (w + tgw) / 2, h - 30, TEXT_CLEAR_RADIUS))

    blocks = _tile_blocks(w, h, voids)
    _draw_blocks(img, blocks)

    if not centered:
        draw.text((margin, h * 0.30), title, font=title_font, fill=INK)
        draw.text((margin, h * 0.30 + title_size + 14), subtitle, font=subtitle_font, fill=INK_SOFT)
        stats = [("3", "SERIES"), ("140+", "TESTS"), ("289", "RACE-SEASONS")]
        start_y = h * 0.30 + title_size + 14 + 46
        stat_xs, _ = _stat_layout(draw, stats, w - margin)
        for sx, (num, lbl) in zip(stat_xs, stats):
            _stat_label(draw, sx, start_y, num, lbl)
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

    top = h * 0.30
    voids: list[Void] = [(0, top - 4, margin + (tb[2] - tb[0]), top + title_size + 2, TEXT_CLEAR_RADIUS)]
    sub_top = top + title_size + 14
    voids.append((0, sub_top - 2, margin + (sb[2] - sb[0]), sub_top + 22, TEXT_CLEAR_RADIUS))
    stats_labels = [("3", "SERIES"), ("140+", "TESTS"), ("289", "RACE-SEASONS")]
    start_y = top + title_size + 14 + 46
    stat_xs, stat_ws = _stat_layout(dummy, stats_labels, w - margin)
    for sx, sw in zip(stat_xs, stat_ws):
        voids.append((sx - 6, start_y - 6, sx + sw + 6, start_y + 46, TEXT_CLEAR_RADIUS))

    blocks = _tile_blocks(w, h, voids)
    rects = "".join(
        f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="#{c[0]:02x}{c[1]:02x}{c[2]:02x}"/>'
        for x, y, bw, bh, c in blocks
    )

    stat_svg = "".join(
        f'<g><text x="{sx}" y="{start_y + 22}" font-size="22" font-weight="700" fill="#E10600">{num}</text>'
        f'<text x="{sx}" y="{start_y + 52}" font-size="11" fill="#4A4E5C">{lbl}</text></g>'
        for sx, (num, lbl) in zip(stat_xs, stats_labels)
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
  <g font-family="JetBrains Mono, Consolas, monospace">{stat_svg}</g>
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
