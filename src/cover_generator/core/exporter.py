"""Writes the assembled cover canvas out as a print-ready PDF."""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageCms

from .models import ColorMode

logger = logging.getLogger(__name__)


def _icc_kwargs(image: Image.Image) -> dict[str, bytes]:
    """save() kwargs that embed the image's ICC profile, or empty if it has none.

    A profile-based CMYK conversion tags the result with the destination
    profile in ``image.info["icc_profile"]``; embedding it on save is what lets
    viewers and the press interpret the CMYK numbers correctly. Without it, a
    CMYK JPEG in particular renders with shifted/inverted colours in most
    colour-managed viewers -- the file looks broken even though the pixels are
    right for the wrong assumed profile. The uncalibrated fallback conversion
    carries no profile, so this yields no kwargs and nothing is embedded.
    """
    icc = image.info.get("icc_profile")
    return {"icc_profile": icc} if icc else {}


def _convert_to_cmyk(canvas: Image.Image, profile_path: Path | None) -> Image.Image:
    """Convert to CMYK, using a real ICC profile transform when one is given.

    On the profile path the result is tagged with the destination profile in
    ``info["icc_profile"]`` so exporters can embed it (see ``_icc_kwargs``).

    Falls back to Pillow's built-in (uncalibrated, no ICC profile) RGB->CMYK
    formula if no profile is supplied, the file is missing, or the transform
    fails for any reason -- this conversion must never block an export.
    """
    if profile_path is None:
        return canvas.convert("CMYK")

    try:
        srgb_profile = ImageCms.createProfile("sRGB")
        cmyk_profile = ImageCms.getOpenProfile(str(profile_path))
        transform = ImageCms.buildTransform(
            srgb_profile, cmyk_profile, "RGB", "CMYK", renderingIntent=0
        )
        converted = ImageCms.applyTransform(canvas.convert("RGB"), transform)
        # applyTransform tags the result with the destination profile, but be
        # explicit so the bytes are always present for embedding on save.
        if "icc_profile" not in converted.info:
            converted.info["icc_profile"] = cmyk_profile.tobytes()
        return converted
    except (OSError, ImageCms.PyCMSError) as exc:
        logger.warning(
            "ICC profile conversion failed (%s); falling back to basic CMYK conversion.", exc
        )
        return canvas.convert("CMYK")


def export_pdf(
    canvas: Image.Image,
    output_path: Path,
    dpi: int,
    color_mode: ColorMode = ColorMode.RGB,
    cmyk_profile_path: Path | None = None,
) -> Path:
    """Save the canvas as a single-page PDF at the given DPI. Returns output_path.

    Without a profile, CMYK conversion uses Pillow's built-in (uncalibrated,
    no ICC profile) RGB->CMYK formula -- a reasonable approximation for
    proofing, but colors may shift against what a commercial press produces.
    Pass cmyk_profile_path (a print house's .icc file) for an accurate,
    profile-based conversion instead.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    to_save = (
        _convert_to_cmyk(canvas, cmyk_profile_path) if color_mode == ColorMode.CMYK else canvas
    )
    to_save.save(output_path, "PDF", resolution=dpi, quality=100, **_icc_kwargs(to_save))
    return output_path


def export_jpg(
    image: Image.Image,
    output_path: Path,
    dpi: int,
    quality: int = 95,
    color_mode: ColorMode = ColorMode.RGB,
    cmyk_profile_path: Path | None = None,
) -> Path:
    """Save an image as a high-quality JPEG with the DPI embedded. Returns output_path.

    Uses no chroma subsampling (``subsampling=0``) so fine coloured detail and
    text edges stay crisp -- important for print uploads.

    In CMYK mode the pixels are written as a CMYK JPEG, using a real ICC
    profile transform when ``cmyk_profile_path`` points at a valid .icc file
    and falling back to Pillow's basic conversion otherwise -- same rules as
    ``export_pdf``. On the profile path the .icc profile is embedded in the
    JPEG so colour-managed viewers and the press interpret the CMYK correctly
    (an un-embedded CMYK JPEG is what makes viewers show shifted/inverted
    colours). The uncalibrated fallback carries no profile to embed.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if color_mode == ColorMode.CMYK:
        to_save = _convert_to_cmyk(image, cmyk_profile_path)
    else:
        to_save = image.convert("RGB")
    to_save.save(
        output_path,
        "JPEG",
        dpi=(dpi, dpi),
        quality=quality,
        subsampling=0,
        **_icc_kwargs(to_save),
    )
    return output_path


def export_png(image: Image.Image, output_path: Path, dpi: int) -> Path:
    """Save an image as a PNG with the DPI embedded. Returns output_path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, "PNG", dpi=(dpi, dpi))
    return output_path


def export_preview_image(canvas: Image.Image, pdf_output_path: Path, dpi: int) -> Path:
    """Save the canvas as a PNG alongside the PDF, for visual quality checks. Returns its path."""
    image_path = pdf_output_path.with_suffix(".png")
    return export_png(canvas, image_path, dpi)
