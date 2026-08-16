"""Renders a blank, actual-size mockup/template PNG for a wrap-around cover.

No source images -- just the bleed, trim, spine, and a "danger zone" safety
margin painted pink, plus printed dimension labels. Meant to be opened in an
editor like Krita or Inkscape as a real-size guide layer while designing
actual cover art.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageDraw

from .compositor import draw_spine_text, load_font
from .exporter import export_png
from .geometry import compute_canvas_layout_from_params, compute_spine_width_mm, mm_to_px
from .models import MockupSpec

ProgressCallback = Callable[[str, float], None]

# Soft pastel pink used for the bleed area and the danger-zone safety margin.
BLEED_COLOR = (255, 179, 186)
# Light gray used for the spine trim box (it holds no printable art directly).
SPINE_COLOR = (221, 221, 221)
# Mid-gray for thin divider lines along trim/spine boundaries.
DIVIDER_COLOR = (153, 153, 153)
# Dark gray for printed dimension labels.
LABEL_COLOR = (68, 68, 68)

MAX_CAPTION_FONT_SIZE = 48

# English defaults for the text baked into the PNG; MockupSpec.labels can
# override any subset with already-localized strings from the caller.
DEFAULT_LABELS = {
    "back": "BACK COVER",
    "front": "FRONT COVER",
    "trim": "Trim",
    "bleed": "Bleed",
    "danger_zone": "Danger zone",
    "spine": "Spine",
    "pages": "pages",
    "canvas": "Canvas",
    "dpi": "DPI",
}


def _noop_progress(_message: str, _fraction: float) -> None:
    return None


def _centered_text(
    draw: ImageDraw.ImageDraw,
    center_x: float,
    center_y: float,
    text: str,
    font,
    color: tuple[int, int, int],
) -> None:
    """Draw ``text`` (possibly multi-line) centered on ``(center_x, center_y)``.

    Measures with ``multiline_textbbox`` (the actual rendered ink extent, same
    reasoning as ``compositor.draw_spine_text``'s use of ``textbbox``) rather
    than an advance-width estimate, so centering is accurate.
    """
    left, top, right, bottom = draw.multiline_textbbox((0, 0), text, font=font, align="center")
    text_w = right - left
    text_h = bottom - top
    x = center_x - text_w / 2 - left
    y = center_y - text_h / 2 - top
    draw.multiline_text((x, y), text, font=font, fill=color, align="center")


def generate_mockup(spec: MockupSpec, *, on_progress: ProgressCallback = _noop_progress) -> Path:
    """Render a blank cover mockup/template PNG for a MockupSpec and return its path."""
    on_progress("Computing layout", 0.0)
    labels = {**DEFAULT_LABELS, **(spec.labels or {})}
    layout = compute_canvas_layout_from_params(
        spec.trim_size,
        spec.bleed_mm,
        spec.dpi,
        spec.pages,
        spec.paper_type,
        spine_width_mm=spec.spine_width_mm,
    )
    spine_mm = (
        spec.spine_width_mm
        if spec.spine_width_mm is not None
        else compute_spine_width_mm(spec.pages, spec.paper_type)
    )

    on_progress("Painting trim and bleed", 0.2)
    canvas = Image.new("RGB", (layout.total_w_px, layout.total_h_px), BLEED_COLOR)
    draw = ImageDraw.Draw(canvas)

    back_box = (
        layout.bleed_px,
        layout.bleed_px,
        layout.bleed_px + layout.page_w_px,
        layout.bleed_px + layout.page_h_px,
    )
    spine_box = (
        layout.spine_x,
        layout.bleed_px,
        layout.spine_x + layout.spine_w_px,
        layout.bleed_px + layout.page_h_px,
    )
    front_box = (
        layout.front_x,
        layout.bleed_px,
        layout.front_x + layout.page_w_px,
        layout.bleed_px + layout.page_h_px,
    )
    draw.rectangle(back_box, fill="white")
    draw.rectangle(spine_box, fill=SPINE_COLOR)
    draw.rectangle(front_box, fill="white")

    on_progress("Painting danger zone", 0.35)
    danger_zone_px = mm_to_px(spec.danger_zone_mm, spec.dpi)
    if danger_zone_px > 0:
        trim_left = layout.bleed_px
        trim_top = layout.bleed_px
        trim_right = layout.total_w_px - layout.bleed_px
        trim_bottom = layout.total_h_px - layout.bleed_px

        draw.rectangle(
            (trim_left, trim_top, trim_right, trim_top + danger_zone_px), fill=BLEED_COLOR
        )
        draw.rectangle(
            (trim_left, trim_bottom - danger_zone_px, trim_right, trim_bottom), fill=BLEED_COLOR
        )
        draw.rectangle(
            (trim_left, trim_top, trim_left + danger_zone_px, trim_bottom), fill=BLEED_COLOR
        )
        draw.rectangle(
            (trim_right - danger_zone_px, trim_top, trim_right, trim_bottom), fill=BLEED_COLOR
        )

    # Thin divider lines along the trim/spine boundaries, for crispness when
    # zoomed in an editor.
    draw.rectangle(back_box, outline=DIVIDER_COLOR, width=1)
    draw.rectangle(spine_box, outline=DIVIDER_COLOR, width=1)
    draw.rectangle(front_box, outline=DIVIDER_COLOR, width=1)

    on_progress("Drawing labels", 0.6)
    draw_spine_text(
        canvas,
        spine_w_px=layout.spine_w_px,
        total_h_px=layout.total_h_px,
        title=f"{spine_mm:.1f} mm",
        author="",
        x_offset=layout.spine_x,
    )

    caption_font_size = min(max(int(layout.page_w_px * 0.05), 12), MAX_CAPTION_FONT_SIZE)
    caption_font = load_font(caption_font_size)

    back_center_x = layout.bleed_px + layout.page_w_px / 2
    front_center_x = layout.front_x + layout.page_w_px / 2
    panel_center_y = layout.bleed_px + layout.page_h_px / 2

    _centered_text(
        draw,
        back_center_x,
        panel_center_y,
        f"{labels['back']}\n{spec.trim_size.width_mm:.0f} x {spec.trim_size.height_mm:.0f} mm",
        caption_font,
        LABEL_COLOR,
    )
    _centered_text(
        draw,
        front_center_x,
        panel_center_y,
        f"{labels['front']}\n{spec.trim_size.width_mm:.0f} x {spec.trim_size.height_mm:.0f} mm",
        caption_font,
        LABEL_COLOR,
    )

    on_progress("Drawing info block", 0.75)
    total_w_mm = spec.trim_size.width_mm * 2 + spine_mm + spec.bleed_mm * 2
    total_h_mm = spec.trim_size.height_mm + spec.bleed_mm * 2
    trim_label = f" ({spec.trim_size.label})" if spec.trim_size.label else ""
    info_lines = [
        f"{labels['trim']}: {spec.trim_size.width_mm:.1f} x {spec.trim_size.height_mm:.1f} mm"
        f"{trim_label}",
        f"{labels['bleed']}: {spec.bleed_mm:.1f} mm",
        f"{labels['danger_zone']}: {spec.danger_zone_mm:.1f} mm",
        f"{labels['spine']}: {spine_mm:.1f} mm "
        f"({spec.pages} {labels['pages']}, {spec.paper_type.value})",
        f"{labels['canvas']}: {total_w_mm:.1f} x {total_h_mm:.1f} mm "
        f"/ {layout.total_w_px} x {layout.total_h_px} px",
        f"{labels['dpi']}: {spec.dpi}",
    ]
    info_font_size = max(int(layout.page_w_px * 0.03), 10)
    info_font = load_font(info_font_size)
    padding_px = max(int(layout.page_w_px * 0.01), 4)
    safe_inset = max(danger_zone_px, 0) + padding_px
    draw.multiline_text(
        (layout.bleed_px + safe_inset, layout.bleed_px + safe_inset),
        "\n".join(info_lines),
        font=info_font,
        fill=LABEL_COLOR,
        align="left",
    )

    on_progress("Exporting PNG", 0.9)
    result = export_png(canvas, spec.output_path, spec.dpi)

    on_progress("Done", 1.0)
    return result
