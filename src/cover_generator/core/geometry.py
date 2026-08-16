"""Pure mm<->px and layout math, with no file or image I/O.

Kept dependency-free so it can be unit tested without Pillow/OpenCV installed.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import MIN_SPINE_MM, PAGE_THICKNESS_MM, CoverSpec, PaperType

MM_PER_INCH = 25.4

# Conversion factors to millimetres, for unit-aware inputs (e.g. a mockup tool
# letting the user pick mm/cm/in/pt for bleed or danger-zone margins).
MM_PER_UNIT: dict[str, float] = {
    "mm": 1.0,
    "cm": 10.0,
    "in": MM_PER_INCH,
    "pt": MM_PER_INCH / 72,
}


def unit_to_mm(value: float, unit: str) -> float:
    """Convert ``value`` in ``unit`` (one of ``MM_PER_UNIT``'s keys) to millimetres."""
    return value * MM_PER_UNIT[unit]


def mm_to_px(mm: float, dpi: int) -> int:
    """Convert a millimetre measurement to whole pixels at the given DPI."""
    return int(round((mm / MM_PER_INCH) * dpi))


def compute_spine_width_mm(pages: int, paper_type) -> float:
    """Estimate spine thickness in mm from page count and paper stock."""
    thickness = PAGE_THICKNESS_MM[paper_type]
    return max(round(pages * thickness, 1), MIN_SPINE_MM)


def compute_single_panel_size(
    trim_size, bleed_mm: float, dpi: int, *, include_bleed: bool = True
) -> tuple[int, int]:
    """Pixel size of one standalone cover panel at the given DPI.

    With ``include_bleed``, adds ``bleed_mm`` on all four sides (so the trim
    box sits ``bleed_mm`` in from every edge); otherwise returns exactly the
    trim size in pixels.
    """
    margin_mm = bleed_mm if include_bleed else 0.0
    width_px = mm_to_px(trim_size.width_mm + margin_mm * 2, dpi)
    height_px = mm_to_px(trim_size.height_mm + margin_mm * 2, dpi)
    return width_px, height_px


def compute_spine_panel_size(
    trim_size,
    bleed_mm: float,
    dpi: int,
    pages: int,
    paper_type: PaperType,
    *,
    include_bleed: bool = True,
    spine_width_mm: float | None = None,
) -> tuple[int, int]:
    """Pixel size of a standalone spine panel at the given DPI.

    The width is the spine thickness derived from ``pages`` and ``paper_type``
    (the same calculation the full wrap-around cover uses); the height is the
    book's trim height, plus ``bleed_mm`` top and bottom when ``include_bleed``.
    This lets the single-image tool output a correctly-sized spine strip.

    Pass ``spine_width_mm`` to override the computed thickness with an exact
    value -- e.g. to match a print service's own spine template, which may use
    a different per-page thickness than this tool estimates.
    """
    spine_mm = spine_width_mm if spine_width_mm is not None else compute_spine_width_mm(
        pages, paper_type
    )
    margin_mm = bleed_mm if include_bleed else 0.0
    width_px = mm_to_px(spine_mm, dpi)
    height_px = mm_to_px(trim_size.height_mm + margin_mm * 2, dpi)
    return width_px, height_px


@dataclass(frozen=True, slots=True)
class CanvasLayout:
    """Pixel geometry of the full wrap-around cover canvas."""

    bleed_px: int
    page_w_px: int
    page_h_px: int
    spine_w_px: int

    total_w_px: int
    total_h_px: int

    back_x: int
    spine_x: int
    front_x: int

    panel_w_px: int  # width of front/back panel including bleed
    panel_h_px: int  # height of any panel including bleed


def compute_canvas_layout_from_params(
    trim_size,
    bleed_mm: float,
    dpi: int,
    pages: int,
    paper_type: PaperType,
    *,
    spine_width_mm: float | None = None,
) -> CanvasLayout:
    """Compute the full pixel layout for a cover from its raw parameters.

    Pass ``spine_width_mm`` to override the computed pages x paper thickness
    estimate with an exact value -- same override pattern as
    ``compute_spine_panel_size``.
    """
    spine_mm = (
        spine_width_mm if spine_width_mm is not None else compute_spine_width_mm(pages, paper_type)
    )

    bleed_px = mm_to_px(bleed_mm, dpi)
    page_w_px = mm_to_px(trim_size.width_mm, dpi)
    page_h_px = mm_to_px(trim_size.height_mm, dpi)
    spine_w_px = mm_to_px(spine_mm, dpi)

    total_h_px = page_h_px + (bleed_px * 2)
    total_w_px = (bleed_px * 2) + (page_w_px * 2) + spine_w_px

    back_x = 0
    spine_x = bleed_px + page_w_px
    front_x = bleed_px + page_w_px + spine_w_px

    panel_w_px = page_w_px + bleed_px
    panel_h_px = total_h_px

    return CanvasLayout(
        bleed_px=bleed_px,
        page_w_px=page_w_px,
        page_h_px=page_h_px,
        spine_w_px=spine_w_px,
        total_w_px=total_w_px,
        total_h_px=total_h_px,
        back_x=back_x,
        spine_x=spine_x,
        front_x=front_x,
        panel_w_px=panel_w_px,
        panel_h_px=panel_h_px,
    )


def compute_canvas_layout(spec: CoverSpec) -> CanvasLayout:
    """Compute the full pixel layout for a cover, given a CoverSpec."""
    return compute_canvas_layout_from_params(
        spec.trim_size, spec.bleed_mm, spec.dpi, spec.pages, spec.paper_type
    )
