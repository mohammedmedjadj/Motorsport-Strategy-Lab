"""Render the README banner and GitHub social-preview image directly with
Pillow (no cairosvg/rsvg-convert/Inkscape available in this environment).

Pixel-mosaic style background (chunky quantised tiles along a flowing
diagonal gradient, dark blue -> purple -> light blue), inspired by the
"Mistral" mosaic-gradient look but in this project's own palette. Both
raster images share one drawing routine parameterised by size and layout,
so the banner and the social preview never visually drift apart. Run:

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
WHITE = (245, 245, 245)
GREY_TEXT = (222, 226, 236)

SEED = 20260723


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


def _pixel_mosaic(w: int, h: int, tile: int = 18) -> Image.Image:
    rng = random.Random(SEED)
    img = Image.new("RGB", (w, h))
    px = img.load()
    for ty in range(0, h, tile):
        for tx in range(0, w, tile):
            u = (tx + tile / 2) / w
            v = (ty + tile / 2) / h
            r, g, b = _gradient_color(u, v)
            jitter = rng.uniform(-0.08, 0.08)
            r = max(0, min(255, int(r * (1 + jitter))))
            g = max(0, min(255, int(g * (1 + jitter))))
            b = max(0, min(255, int(b * (1 + jitter))))
            for y in range(ty, min(ty + tile, h)):
                for x in range(tx, min(tx + tile, w)):
                    px[x, y] = (r, g, b)
    return img


def _scrim_left(base: Image.Image, w: int, h: int, extent: float = 0.6) -> Image.Image:
    """Dark gradient overlay, opaque on the left fading to transparent, so
    left-aligned title text stays legible over the mosaic."""
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = overlay.load()
    cut = int(w * extent)
    for x in range(w):
        if x < cut:
            alpha = int(200 * (1 - x / cut) ** 1.3)
        else:
            alpha = 0
        for y in range(h):
            px[x, y] = (0, 0, 0, alpha)
    return Image.alpha_composite(base.convert("RGBA"), overlay)


def _scrim_radial(base: Image.Image, w: int, h: int, cx: float, cy: float, radius: float) -> Image.Image:
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = overlay.load()
    for y in range(h):
        for x in range(w):
            d = math.hypot((x - cx) / radius, (y - cy) / (radius * 0.55))
            alpha = int(190 * max(0.0, 1 - d))
            px[x, y] = (0, 0, 0, alpha)
    return Image.alpha_composite(base.convert("RGBA"), overlay)


def _stat_card(draw, x, y, w, h, number, label):
    draw.rectangle([x, y, x + w, y + h], outline=(255, 255, 255, 60), width=1, fill=(8, 10, 20, 210))
    num_font = _font(JBMONO, 22, weight=700)
    lbl_font = _font(JBMONO, 11, weight=500)
    draw.text((x + 14, y + 10), number, font=num_font, fill=WHITE)
    draw.text((x + 14, y + h - 26), label, font=lbl_font, fill=GREY_TEXT)


def make_banner(w: int, h: int, centered: bool, tag: str | None = None) -> Image.Image:
    bg = _pixel_mosaic(w, h)
    if centered:
        img = _scrim_radial(bg, w, h, cx=w / 2, cy=h * 0.44, radius=w * 0.42)
    else:
        img = _scrim_left(bg, w, h, extent=0.62)
    draw = ImageDraw.Draw(img, "RGBA")

    title = "MOTORSPORT STRATEGY LAB"
    subtitle = "Bayesian & Monte Carlo Race Strategy Research — F1 · WEC · IMSA"

    title_size = 46 if not centered else 52
    title_font = _font(SPACE_GROTESK, title_size, weight=700)
    subtitle_font = _font(INTER, 19 if not centered else 21, weight=400)

    margin = 60
    if not centered:
        draw.text((margin, h * 0.30), title, font=title_font, fill=WHITE)
        draw.text((margin, h * 0.30 + title_size + 14), subtitle, font=subtitle_font, fill=GREY_TEXT)

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
        draw.text(((w - tw) / 2, h * 0.36), title, font=title_font, fill=WHITE)
        sb = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        sw = sb[2] - sb[0]
        draw.text(((w - sw) / 2, h * 0.36 + title_size + 22), subtitle, font=subtitle_font, fill=GREY_TEXT)
        if tag:
            tag_font = _font(JBMONO, 14, weight=500)
            tgb = draw.textbbox((0, 0), tag, font=tag_font)
            tgw = tgb[2] - tgb[0]
            draw.text(((w - tgw) / 2, h - 46), tag, font=tag_font, fill=GREY_TEXT)

    # thin red accent underline beneath the title, a nod to a start-lights bar
    accent_y = int(h * 0.30) - 14 if not centered else int(h * 0.36) - 16
    accent_x0 = margin if not centered else (w - 220) / 2
    accent_w = 90 if not centered else 220
    draw.rectangle([accent_x0, accent_y, accent_x0 + accent_w, accent_y + 4], fill=RED)

    return img.convert("RGB")


def make_banner_svg(w: int, h: int, tile: int = 18) -> str:
    """Vector source counterpart of make_banner(w, h, centered=False): same
    tile grid, same RNG seed, so it can't visually drift from the PNG."""
    rng = random.Random(SEED)
    tiles = []
    for ty in range(0, h, tile):
        for tx in range(0, w, tile):
            u = (tx + tile / 2) / w
            v = (ty + tile / 2) / h
            r, g, b = _gradient_color(u, v)
            jitter = rng.uniform(-0.08, 0.08)
            r = max(0, min(255, int(r * (1 + jitter))))
            g = max(0, min(255, int(g * (1 + jitter))))
            b = max(0, min(255, int(b * (1 + jitter))))
            tiles.append(f'<rect x="{tx}" y="{ty}" width="{tile}" height="{tile}" fill="#{r:02x}{g:02x}{b:02x}"/>')

    title = "MOTORSPORT STRATEGY LAB"
    subtitle = "Bayesian &amp; Monte Carlo Race Strategy Research — F1 · WEC · IMSA"
    margin = 60

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img"
     aria-label="Motorsport Strategy Lab -- Bayesian and Monte Carlo race strategy research across F1, WEC and IMSA">
  <title>Motorsport Strategy Lab</title>
  <defs>
    <linearGradient id="scrim" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#000000" stop-opacity="0.78"/>
      <stop offset="62%" stop-color="#000000" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <g>{"".join(tiles)}</g>
  <rect width="{w}" height="{h}" fill="url(#scrim)"/>
  <rect x="{margin}" y="76" width="90" height="4" fill="#E10600"/>
  <text x="{margin}" y="140" font-family="Space Grotesk, Arial, sans-serif" font-weight="700"
        font-size="46" fill="#F5F5F5" letter-spacing="0.5">{title}</text>
  <text x="{margin}" y="172" font-family="Inter, Arial, sans-serif" font-weight="400"
        font-size="19" fill="#DEE2EC">{subtitle}</text>
  <g font-family="JetBrains Mono, Consolas, monospace">
    <g><rect x="658" y="200" width="150" height="78" fill="#080a14" fill-opacity="0.82" stroke="#ffffff" stroke-opacity="0.24"/>
      <text x="672" y="228" font-size="22" font-weight="700" fill="#F5F5F5">3</text>
      <text x="672" y="264" font-size="11" fill="#DEE2EC">SERIES</text></g>
    <g><rect x="824" y="200" width="150" height="78" fill="#080a14" fill-opacity="0.82" stroke="#ffffff" stroke-opacity="0.24"/>
      <text x="838" y="228" font-size="22" font-weight="700" fill="#F5F5F5">140+</text>
      <text x="838" y="264" font-size="11" fill="#DEE2EC">TESTS</text></g>
    <g><rect x="990" y="200" width="150" height="78" fill="#080a14" fill-opacity="0.82" stroke="#ffffff" stroke-opacity="0.24"/>
      <text x="1004" y="228" font-size="22" font-weight="700" fill="#F5F5F5">5</text>
      <text x="1004" y="264" font-size="11" fill="#DEE2EC">AUDITED RACES</text></g>
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
