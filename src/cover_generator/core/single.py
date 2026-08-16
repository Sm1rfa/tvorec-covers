"""Makes one standalone image print-ready: size -> upscale/crop -> export JPG.

The counterpart to ``pipeline.generate_cover`` for print services that take
the front and back cover as two separate uploads and compute the spine
themselves. No wrap-around canvas -- just a single panel sized to trim
(+ bleed) at the target DPI, upscaled if needed so it does not print blurry.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .compositor import draw_spine_text
from .exporter import export_jpg
from .geometry import compute_single_panel_size, compute_spine_panel_size
from .models import SingleImageSpec
from .upscale import fit_image

ProgressCallback = Callable[[str, float], None]


def _noop_progress(_message: str, _fraction: float) -> None:
    return None


def process_single_image(
    spec: SingleImageSpec, *, on_progress: ProgressCallback = _noop_progress
) -> Path:
    """Run the single-image pipeline for a SingleImageSpec and return the output path."""
    on_progress("Computing size", 0.0)
    if spec.spine_mode:
        target_w, target_h = compute_spine_panel_size(
            spec.trim_size,
            spec.bleed_mm,
            spec.dpi,
            spec.pages,
            spec.paper_type,
            include_bleed=spec.include_bleed,
            spine_width_mm=spec.spine_width_mm,
        )
    else:
        target_w, target_h = compute_single_panel_size(
            spec.trim_size, spec.bleed_mm, spec.dpi, include_bleed=spec.include_bleed
        )

    on_progress("Preparing image", 0.2)
    image = fit_image(
        spec.input_path,
        target_w,
        target_h,
        mode=spec.fit_mode,
        fill_color=spec.fill_color,
        allow_ai_upscale=spec.allow_upscale,
        model_path=spec.model_path,
    )

    if spec.spine_mode and spec.pages >= 100 and (spec.title or spec.author):
        draw_spine_text(
            image,
            spine_w_px=target_w,
            total_h_px=target_h,
            title=spec.title,
            author=spec.author,
        )

    on_progress("Exporting JPG", 0.85)
    result = export_jpg(
        image,
        spec.output_path,
        spec.dpi,
        spec.jpg_quality,
        color_mode=spec.color_mode,
        cmyk_profile_path=spec.cmyk_profile_path,
    )

    on_progress("Done", 1.0)
    return result
