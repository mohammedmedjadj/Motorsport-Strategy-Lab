"""Render the README banner and GitHub social-preview image directly with
Pillow (no cairosvg/rsvg-convert/Inkscape available in this environment).

Both images share one drawing routine parameterised by size and layout, so the
banner and the social preview never visually drift apart. Run:

    python scripts/generate_banner.py
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
OUT = ROOT / "assets"

BG_TOP = (11, 14, 20)       # #0B0E14
BG_BOTTOM = (5, 7, 12)
GRID = (42, 47, 58)         # #2A2F3A
CYAN = (0, 217, 255)        # #00D9FF
RED = (225, 6, 0)           # #E10600
AMBER = (255, 184, 0)       # #FFB800
WHITE = (245, 245, 245)     # #F5F5F5
GREY_TEXT = (168, 174, 188)


def _font(path: Path, size: int, weight: float | None = None) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(path), size)
    if weight is not None:
        f.set_variation_by_axes([weight])
    return f


SPACE_GROTESK = FONTS / "SpaceGrotesk-Bold.ttf"
INTER = FONTS / "Inter-Regular.ttf"
JBMONO = FONTS / "JetBrainsMono-Bold.ttf"


def _background(w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h), BG_TOP)
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        for x in range(w):
            px[x, y] = (r, g, b)
    return img


def _grid(base: Image.Image, w: int, h: int, step: int = 48) -> Image.Image:
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for x in range(0, w, step):
        od.line([(x, 0), (x, h)], fill=(*GRID, 40), width=1)
    for y in range(0, h, step):
        od.line([(0, y), (w, y)], fill=(*GRID, 25), width=1)
    return Image.alpha_composite(base.convert("RGBA"), overlay)


def _curves(base: Image.Image, w: int, h: int, n: int = 4) -> Image.Image:
    """Degradation/distribution-style curves in cyan, low opacity, as watermark."""
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    rng_seed = [0.6, 1.3, 2.1, 0.9]
    for i in range(n):
        phase = rng_seed[i % len(rng_seed)]
        amp = h * (0.10 + 0.04 * i)
        base_y = h * (0.25 + 0.18 * i)
        alpha = int(255 * (0.22 - 0.03 * i))
        alpha = max(alpha, 20)
        pts = []
        for x in range(0, w + 1, 4):
            t = x / w
            # decaying-exponential-ish curve modulated by a slow sine, like a
            # tyre-degradation trace riding a lap-time distribution
            y = base_y - amp * math.exp(-2.2 * t) * math.sin(2 * math.pi * (t * 1.4 + phase))
            pts.append((x, y))
        od.line(pts, fill=(*CYAN, alpha), width=2)
    return Image.alpha_composite(base.convert("RGBA"), overlay)


def _stat_card(draw, x, y, w, h, number, label):
    draw.rectangle([x, y, x + w, y + h], outline=(*GRID,), width=1, fill=(18, 21, 29))
    num_font = _font(JBMONO, 22, weight=700)
    lbl_font = _font(JBMONO, 11, weight=500)
    draw.text((x + 14, y + 10), number, font=num_font, fill=RED)
    draw.text((x + 14, y + h - 26), label, font=lbl_font, fill=GREY_TEXT)


def make_banner(w: int, h: int, centered: bool, tag: str | None = None) -> Image.Image:
    bg = _background(w, h)
    bg = _curves(bg, w, h)
    bg = _grid(bg, w, h)
    img = bg.convert("RGB")
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

    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    banner = make_banner(1200, 300, centered=False)
    banner.save(OUT / "banner.png")
    social = make_banner(
        1280, 640, centered=True,
        tag="github.com/mohammedmedjadj/Motorsport-Strategy-Lab",
    )
    social.save(OUT / "social-preview.png")
    print("wrote", OUT / "banner.png", banner.size)
    print("wrote", OUT / "social-preview.png", social.size)


if __name__ == "__main__":
    main()
