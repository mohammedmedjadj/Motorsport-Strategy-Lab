"""Render the README banner and GitHub social-preview image by compositing
title/subtitle/stats text over a hero photo (assets/source/hero-photo.jpg),
rather than a procedurally generated background. A dark gradient scrim on
the left keeps the text legible over the busy photo; the stats get their
own small opaque backing since they sit further right, over the photo
directly. Run:

    python scripts/generate_banner.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
OUT = ROOT / "assets"
SOURCE_PHOTO = OUT / "source" / "hero-photo.jpg"

RED = (225, 6, 0)
WHITE = (245, 245, 245)
GREY_TEXT = (222, 226, 236)


def _font(path: Path, size: int, weight: float | None = None) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(path), size)
    if weight is not None:
        f.set_variation_by_axes([weight])
    return f


SPACE_GROTESK = FONTS / "SpaceGrotesk-Bold.ttf"
INTER = FONTS / "Inter-Regular.ttf"
JBMONO = FONTS / "JetBrainsMono-Bold.ttf"


def _cropped_photo(w: int, h: int, focus_y: float) -> Image.Image:
    """Crop the source photo to the target aspect ratio, then resize.
    focus_y (0..1) picks where the vertical crop window is centred."""
    src = Image.open(SOURCE_PHOTO).convert("RGB")
    sw, sh = src.size
    target_ratio = w / h
    src_ratio = sw / sh
    if src_ratio > target_ratio:
        # source is relatively wider -- crop its width
        crop_h = sh
        crop_w = int(sh * target_ratio)
    else:
        # source is relatively taller -- crop its height
        crop_w = sw
        crop_h = int(sw / target_ratio)
    cx = sw / 2
    cy = sh * focus_y
    x0 = max(0, min(sw - crop_w, int(cx - crop_w / 2)))
    y0 = max(0, min(sh - crop_h, int(cy - crop_h / 2)))
    crop = src.crop((x0, y0, x0 + crop_w, y0 + crop_h))
    return crop.resize((w, h), Image.LANCZOS)


def _scrim_left(img: Image.Image, extent: float, max_alpha: int = 205) -> Image.Image:
    """Dark gradient overlay, opaque on the left fading to transparent, so
    left-aligned title text stays legible over the photo."""
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = overlay.load()
    cut = int(w * extent)
    for x in range(w):
        alpha = int(max_alpha * (1 - x / cut) ** 1.2) if x < cut else 0
        for y in range(h):
            px[x, y] = (0, 0, 0, alpha)
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def _scrim_box(img: Image.Image, box: tuple[int, int, int, int], alpha: int = 175) -> Image.Image:
    """Small opaque-ish rounded backing behind the stats, which sit directly
    over the photo further right where the left scrim has faded out."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle(box, radius=10, fill=(10, 12, 18, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def _stat_layout(draw, stats: list[tuple[str, str]], right_edge: float, gap: float = 34):
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


def make_banner(w: int, h: int, centered: bool, focus_y: float, tag: str | None = None) -> Image.Image:
    img = _cropped_photo(w, h, focus_y)
    img = _scrim_left(img, extent=0.72 if not centered else 0.58, max_alpha=225)
    draw = ImageDraw.Draw(img)

    title = "MOTORSPORT STRATEGY LAB"
    subtitle = "Race Strategy Simulator & Decision Audit — F1 · WEC · IMSA"

    title_size = 46 if not centered else 52
    title_font = _font(SPACE_GROTESK, title_size, weight=700)
    subtitle_font = _font(INTER, 19 if not centered else 21, weight=400)
    margin = 60

    if not centered:
        top = h * 0.30
        draw.text((margin, top), title, font=title_font, fill=WHITE, stroke_width=2, stroke_fill=(0, 0, 0))
        draw.text((margin, top + title_size + 14), subtitle, font=subtitle_font, fill=GREY_TEXT,
                   stroke_width=3, stroke_fill=(0, 0, 0))

        stats = [("3", "SERIES"), ("140+", "TESTS"), ("289", "RACES ANALYZED")]
        start_y = top + title_size + 14 + 46
        stat_xs, stat_ws = _stat_layout(draw, stats, w - margin)
        pad = 12
        box = (int(stat_xs[0] - pad), int(start_y - pad),
               int(stat_xs[-1] + stat_ws[-1] + pad), int(start_y + 46 + pad))
        img = _scrim_box(img, box)
        draw = ImageDraw.Draw(img)
        for sx, (num, lbl) in zip(stat_xs, stats):
            num_font = _font(JBMONO, 22, weight=700)
            lbl_font = _font(JBMONO, 11, weight=500)
            draw.text((sx, start_y), num, font=num_font, fill=RED)
            draw.text((sx, start_y + 30), lbl, font=lbl_font, fill=GREY_TEXT)

        accent_y = int(top) - 14
        draw.rectangle([margin, accent_y, margin + 90, accent_y + 4], fill=RED)
    else:
        top = h * 0.36
        tb = draw.textbbox((0, 0), title, font=title_font)
        tw = tb[2] - tb[0]
        draw.text(((w - tw) / 2, top), title, font=title_font, fill=WHITE, stroke_width=2, stroke_fill=(0, 0, 0))
        sb = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        sw = sb[2] - sb[0]
        draw.text(((w - sw) / 2, top + title_size + 22), subtitle, font=subtitle_font, fill=GREY_TEXT,
                   stroke_width=3, stroke_fill=(0, 0, 0))
        if tag:
            tag_font = _font(JBMONO, 14, weight=500)
            tgb = draw.textbbox((0, 0), tag, font=tag_font)
            tgw = tgb[2] - tgb[0]
            pad = 10
            img = _scrim_box(img, (int((w - tgw) / 2) - pad, h - 50 - pad, int((w + tgw) / 2) + pad, h - 30 + pad))
            draw = ImageDraw.Draw(img)
            draw.text(((w - tgw) / 2, h - 46), tag, font=tag_font, fill=GREY_TEXT)
        accent_y = int(top) - 16
        draw.rectangle([(w - 220) / 2, accent_y, (w - 220) / 2 + 220, accent_y + 4], fill=RED)

    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    banner = make_banner(1200, 300, centered=False, focus_y=0.56)
    banner.save(OUT / "banner.png", quality=92)
    social = make_banner(
        1280, 640, centered=True, focus_y=0.5,
        tag="github.com/mohammedmedjadj/Motorsport-Strategy-Lab",
    )
    social.save(OUT / "social-preview.png", quality=92)
    print("wrote", OUT / "banner.png", banner.size)
    print("wrote", OUT / "social-preview.png", social.size)


if __name__ == "__main__":
    main()
