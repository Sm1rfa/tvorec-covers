"""Assembles the wrap-around cover canvas from sized panel images."""

from __future__ import annotations

import logging
import os

from PIL import Image, ImageDraw, ImageFont

from .geometry import CanvasLayout

logger = logging.getLogger(__name__)

# Fonts to try, in order, for spine text -- first one found wins.
_SPINE_FONT_CANDIDATES = [
    "C:\\Windows\\Fonts\\arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _SPINE_FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    logger.warning("No TrueType font found for spine text; using Pillow's default bitmap font.")
    return ImageFont.load_default()


def _flatten_to_rgb(img: Image.Image) -> Image.Image:
    """Flatten any alpha channel onto black before compositing.

    Prevents transparent edges from leaking raw RGB into the composited image.
    """
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        background = Image.new("RGB", img.size, "black")
        background.paste(img, mask=img.convert("RGBA").split()[-1])
        return background
    return img.convert("RGB")


def build_canvas(
    layout: CanvasLayout,
    front_img: Image.Image,
    back_img: Image.Image,
    spine_img: Image.Image | None,
    *,
    title: str = "",
    author: str = "",
    pages: int = 0,
) -> Image.Image:
    """Paste front/back/spine panels onto one full-bleed canvas and draw spine text."""
    canvas = Image.new("RGB", (layout.total_w_px, layout.total_h_px), "black")
    canvas.paste(_flatten_to_rgb(back_img), (layout.back_x, 0))
    canvas.paste(_flatten_to_rgb(front_img), (layout.front_x, 0))

    if spine_img is not None:
        canvas.paste(_flatten_to_rgb(spine_img), (layout.spine_x, 0))
    else:
        draw = ImageDraw.Draw(canvas)
        draw.rectangle(
            [layout.spine_x, 0, layout.spine_x + layout.spine_w_px, layout.total_h_px],
            fill="black",
        )

    if pages >= 100 and (title or author):
        draw_spine_text(
            canvas,
            spine_w_px=layout.spine_w_px,
            total_h_px=layout.total_h_px,
            title=title,
            author=author,
            x_offset=layout.spine_x,
        )

    return canvas


def draw_spine_text(
    image: Image.Image,
    *,
    spine_w_px: int,
    total_h_px: int,
    title: str,
    author: str,
    x_offset: int = 0,
) -> None:
    """Draw ``author - title`` rotated 270deg, centered on a spine column, in place.

    ``spine_w_px`` x ``total_h_px`` describe the spine column; ``x_offset`` is
    where that column starts inside ``image`` (0 for a standalone spine strip,
    or the spine's x on a full wrap-around canvas). Shared by the full-cover
    compositor and the single-image spine mode so both look identical.
    """
    font_size = max(int(spine_w_px * 0.45), 1)
    font = load_font(font_size)

    full_text = f"{author}   -   {title}" if author else title
    measurer = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    # textbbox gives the actual rendered ink extent -- textlength only gives the
    # glyph advance width, which some fonts' end-of-string glyphs render past,
    # clipping the last character against the layer edge.
    left, top, right, bottom = measurer.textbbox((0, 0), full_text, font=font)
    text_w = right - left
    text_h = bottom - top

    text_y = (total_h_px - text_w) // 2

    text_layer = Image.new("RGBA", (text_w or 1, text_h + 20), (0, 0, 0, 0))
    ImageDraw.Draw(text_layer).text((-left, -top), full_text, fill="white", font=font)

    rotated = text_layer.rotate(270, expand=True)
    paste_x = x_offset + int(spine_w_px * 0.25)
    image.paste(rotated, (paste_x, int(text_y)), rotated)
