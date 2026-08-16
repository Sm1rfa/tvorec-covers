"""Data structures describing a cover generation job."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class PaperType(StrEnum):
    """Interior paper stock, used to compute spine thickness."""

    CREAM = "cream"
    WHITE = "white"
    OFFSET = "offset"


class ColorMode(StrEnum):
    """Output color space for the exported PDF."""

    RGB = "rgb"
    CMYK = "cmyk"


class FitMode(StrEnum):
    """How a source image is fitted to a target panel when their shapes differ.

    - ``CONTAIN``: scale so the whole image is visible, then pad the shorter
      sides with ``fill_color`` to reach the exact panel size. Nothing is
      cropped -- the safe default for a finished design (e.g. a spine strip).
    - ``COVER``: scale to fill the panel edge-to-edge, then center-crop the
      overflow. No padding, but content on the overflowing sides is lost.
    - ``STRETCH``: scale each axis independently to the exact panel size.
      Keeps all content with no padding, but distorts proportions.
    """

    CONTAIN = "contain"
    COVER = "cover"
    STRETCH = "stretch"


# mm of thickness per page, by paper stock.
PAGE_THICKNESS_MM = {
    PaperType.CREAM: 0.065,
    PaperType.WHITE: 0.05,
    # Estimate for a heavier uncoated offset stock, between CREAM and WHITE.
    PaperType.OFFSET: 0.08,
}

MIN_SPINE_MM = 10.0


@dataclass(frozen=True, slots=True)
class TrimSize:
    """A book's trimmed (final, post-cut) page size in millimetres."""

    width_mm: float
    height_mm: float
    label: str = ""


# Common print-on-demand trim size presets.
TRIM_SIZE_PRESETS: list[TrimSize] = [
    TrimSize(127.0, 203.2, "5\" x 8\""),
    TrimSize(139.7, 215.9, "5.5\" x 8.5\""),
    TrimSize(148.0, 210.0, "A5"),
    TrimSize(152.4, 228.6, "6\" x 9\""),
    TrimSize(210.0, 297.0, "A4"),
]


@dataclass(slots=True)
class CoverSpec:
    """All parameters needed to generate one print-ready cover PDF."""

    front_path: Path
    back_path: Path
    output_path: Path
    spine_path: Path | None = None

    pages: int = 220
    paper_type: PaperType = PaperType.CREAM
    trim_size: TrimSize = TRIM_SIZE_PRESETS[2]  # A5
    bleed_mm: float = 3.0
    dpi: int = 300

    title: str = ""
    author: str = ""

    allow_upscale: bool = True
    model_path: Path | None = None

    export_png: bool = False
    color_mode: ColorMode = ColorMode.RGB
    cmyk_profile_path: Path | None = None


@dataclass(slots=True)
class SingleImageSpec:
    """Parameters for making one standalone image print-ready.

    Used by services (e.g. photopis) that take the front and back cover as
    two separate uploads and compute the spine themselves -- so there is no
    wrap-around canvas, just one panel sized to trim (+ bleed) at a target
    DPI, upscaled if needed so it does not print blurry.
    """

    input_path: Path
    output_path: Path

    trim_size: TrimSize = TRIM_SIZE_PRESETS[2]  # A5
    bleed_mm: float = 3.0
    include_bleed: bool = True
    dpi: int = 300

    # Spine mode: size the panel to the computed spine width (from page count
    # and paper stock) x book height, and optionally draw title/author text --
    # so the single-image tool can produce a correctly-sized standalone spine.
    spine_mode: bool = False
    pages: int = 220
    paper_type: PaperType = PaperType.CREAM
    # Override the spine width (mm) instead of deriving it from pages x paper
    # thickness -- e.g. to match a print service's own spine template exactly.
    spine_width_mm: float | None = None
    title: str = ""
    author: str = ""

    allow_upscale: bool = True
    model_path: Path | None = None

    fit_mode: FitMode = FitMode.CONTAIN
    fill_color: str = "white"

    jpg_quality: int = 95
    color_mode: ColorMode = ColorMode.RGB
    cmyk_profile_path: Path | None = None


@dataclass(slots=True)
class MockupSpec:
    """Parameters for rendering a blank, actual-size cover mockup/template PNG.

    Produces a guide image (not real artwork) showing the trim, bleed, and a
    "danger zone" safety margin painted pink, plus printed dimension labels --
    meant to be opened in an editor like Krita or Inkscape as a real-size
    reference layer while designing actual cover art. The danger zone is the
    safety margin drawn just inside the trim edge on the four *outer* edges of
    the whole wrap-around board (top, bottom, back's outer-left edge, front's
    outer-right edge) -- not around the spine-fold seams, since content is
    expected to run right up to those.
    """

    output_path: Path

    trim_size: TrimSize = TRIM_SIZE_PRESETS[2]  # A5
    pages: int = 220
    paper_type: PaperType = PaperType.CREAM
    bleed_mm: float = 3.0
    danger_zone_mm: float = 5.0
    dpi: int = 300
    # Override the spine width (mm) instead of deriving it from pages x paper
    # thickness -- e.g. to match a print service's own spine template exactly.
    spine_width_mm: float | None = None
    # Optional overrides for the text baked into the PNG, so a caller (the
    # GUI) can pass already-localized strings -- core has no i18n of its own.
    # Recognized keys: back, front, trim, bleed, danger_zone, spine, pages,
    # canvas, dpi. Any key left out falls back to its English default.
    labels: dict[str, str] | None = None
