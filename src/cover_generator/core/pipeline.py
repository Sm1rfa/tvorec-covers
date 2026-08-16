"""Orchestrates geometry -> upscale -> compositor -> exporter for one CoverSpec."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .compositor import build_canvas
from .exporter import export_pdf, export_preview_image
from .geometry import compute_canvas_layout
from .models import CoverSpec
from .upscale import ensure_min_size, fit_to_cover

ProgressCallback = Callable[[str, float], None]


def _noop_progress(_message: str, _fraction: float) -> None:
    return None


def generate_cover(spec: CoverSpec, *, on_progress: ProgressCallback = _noop_progress) -> Path:
    """Run the full pipeline for a CoverSpec and return the path to the generated PDF."""
    on_progress("Computing layout", 0.0)
    layout = compute_canvas_layout(spec)

    on_progress("Preparing front cover", 0.15)
    front_img = fit_to_cover(
        spec.front_path,
        layout.panel_w_px,
        layout.panel_h_px,
        allow_ai_upscale=spec.allow_upscale,
        model_path=spec.model_path,
    )

    on_progress("Preparing back cover", 0.4)
    back_img = fit_to_cover(
        spec.back_path,
        layout.panel_w_px,
        layout.panel_h_px,
        allow_ai_upscale=spec.allow_upscale,
        model_path=spec.model_path,
    )

    spine_img = None
    if spec.spine_path is not None:
        on_progress("Preparing spine", 0.6)
        spine_img = ensure_min_size(
            spec.spine_path,
            layout.spine_w_px,
            layout.total_h_px,
            allow_ai_upscale=spec.allow_upscale,
            model_path=spec.model_path,
        ).resize((layout.spine_w_px, layout.total_h_px))

    on_progress("Assembling cover", 0.75)
    canvas = build_canvas(
        layout,
        front_img,
        back_img,
        spine_img,
        title=spec.title,
        author=spec.author,
        pages=spec.pages,
    )

    on_progress("Exporting PDF", 0.9)
    result = export_pdf(
        canvas, spec.output_path, spec.dpi, spec.color_mode, spec.cmyk_profile_path
    )

    if spec.export_png:
        on_progress("Exporting PNG preview", 0.95)
        export_preview_image(canvas, spec.output_path, spec.dpi)

    on_progress("Done", 1.0)
    return result
