"""Optional AI upscaling backend (OpenCV FSRCNN), with a Lanczos fallback.

OpenCV is an optional dependency (`pip install cover-generator[upscale]`).
Code in this module must not be imported at module load time by anything in
`core/` that needs to run without OpenCV installed -- callers should go
through `ensure_min_size`, which degrades gracefully.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

from .models import FitMode

logger = logging.getLogger(__name__)


def needs_upscale(image: Image.Image, target_w: int, target_h: int) -> bool:
    """Whether an image is smaller than the target size in either dimension."""
    return image.width < target_w or image.height < target_h


def _upscale_with_fsrcnn(
    image: Image.Image, model_path: Path, scale: int = 4
) -> Image.Image | None:
    """Try AI upscaling via OpenCV's FSRCNN super-resolution model.

    Returns None (rather than raising) if OpenCV or the model file are
    unavailable, so callers can fall back to a plain resize.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        logger.warning("OpenCV not installed; skipping AI upscale, falling back to Lanczos resize.")
        return None

    if not model_path.exists():
        logger.warning("Upscale model not found at %s; falling back to Lanczos resize.", model_path)
        return None

    sr = cv2.dnn_superres.DnnSuperResImpl_create()
    sr.readModel(str(model_path))
    sr.setModel("fsrcnn", scale)

    img = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)

    upscaled = sr.upsample(img)
    upscaled_rgb = cv2.cvtColor(upscaled, cv2.COLOR_BGR2RGB)
    return Image.fromarray(upscaled_rgb)


def crop_to_visible_content(image: Image.Image) -> Image.Image:
    """Crop away fully-transparent padding so the visible artwork fills the frame.

    Source exports (especially AI-generated cover art) often carry a
    transparent margin around the actual design. Left uncropped, that margin
    gets stretched along with the content and shows up as solid black bars
    once the alpha channel is flattened during compositing.
    """
    if image.mode not in ("RGBA", "LA"):
        return image
    bbox = image.split()[-1].getbbox()
    if bbox is None:
        return image
    return image.crop(bbox)


def ensure_min_size(
    image_path: Path,
    target_w: int,
    target_h: int,
    *,
    allow_ai_upscale: bool = True,
    model_path: Path | None = None,
) -> Image.Image:
    """Load an image and guarantee it is at least target_w x target_h.

    Tries AI upscaling first (if allowed and available), then falls back to
    a plain Lanczos resize so the pipeline always produces a usable image.
    """
    with Image.open(image_path) as opened:
        image = opened.copy()

    image = crop_to_visible_content(image)

    if not needs_upscale(image, target_w, target_h):
        return image

    if allow_ai_upscale and model_path is not None:
        upscaled = _upscale_with_fsrcnn(image, model_path)
        if upscaled is not None and not needs_upscale(upscaled, target_w, target_h):
            return upscaled
        if upscaled is not None:
            image = upscaled

    return image.resize((target_w, target_h), Image.Resampling.LANCZOS)


def _resize_and_center_crop(image: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Scale (preserving aspect) so the image covers the target, then center-crop to it."""
    scale = max(target_w / image.width, target_h / image.height)
    scaled_w = max(round(image.width * scale), target_w)
    scaled_h = max(round(image.height * scale), target_h)
    resized = image.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)

    left = (scaled_w - target_w) // 2
    top = (scaled_h - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def fit_to_cover(
    image_path: Path,
    target_w: int,
    target_h: int,
    *,
    allow_ai_upscale: bool = True,
    model_path: Path | None = None,
) -> Image.Image:
    """Load an image and return it sized to exactly target_w x target_h, no distortion.

    Scales the image to *cover* the target box (preserving aspect ratio) and
    center-crops the overflow. When covering the box requires enlarging the
    source, tries AI upscaling first (if allowed and available) so the result
    stays sharp, then falls back to a plain Lanczos scale-and-crop.
    """
    with Image.open(image_path) as opened:
        image = opened.copy()

    image = crop_to_visible_content(image)

    needs_enlarging = image.width < target_w or image.height < target_h
    if needs_enlarging and allow_ai_upscale and model_path is not None:
        upscaled = _upscale_with_fsrcnn(image, model_path)
        if upscaled is not None:
            image = upscaled

    return _resize_and_center_crop(image, target_w, target_h)


def _flatten_onto(image: Image.Image, target_w: int, target_h: int, fill_color: str) -> Image.Image:
    """Return an RGB image of exactly target size with ``image`` centered on ``fill_color``.

    Alpha (a spine strip's transparent margin, say) is composited onto the fill
    colour rather than dropped, so padded and transparent areas share one solid
    background instead of leaking raw RGB.
    """
    canvas = Image.new("RGB", (target_w, target_h), fill_color)
    offset = ((target_w - image.width) // 2, (target_h - image.height) // 2)
    mask = image.convert("RGBA").split()[-1] if image.mode in ("RGBA", "LA", "P") else None
    canvas.paste(image.convert("RGB"), offset, mask)
    return canvas


def fit_image(
    image_path: Path,
    target_w: int,
    target_h: int,
    *,
    mode: FitMode = FitMode.CONTAIN,
    fill_color: str = "white",
    allow_ai_upscale: bool = True,
    model_path: Path | None = None,
) -> Image.Image:
    """Load an image and size it to exactly target_w x target_h using ``mode``.

    - ``CONTAIN`` scales the whole image to fit inside the panel and pads the
      shorter sides with ``fill_color`` -- nothing is cropped.
    - ``COVER`` scales to fill the panel and center-crops the overflow.
    - ``STRETCH`` scales each axis to the exact panel size (distorts).

    Enlarging (when the source is smaller than the panel in the direction that
    binds for the chosen mode) tries AI upscaling first, if allowed and
    available, then falls back to a plain Lanczos scale. The result is always
    RGB at exactly the target size, with any alpha flattened onto ``fill_color``.
    """
    with Image.open(image_path) as opened:
        image = opened.copy()

    image = crop_to_visible_content(image)

    if mode == FitMode.COVER:
        needs_enlarging = image.width < target_w or image.height < target_h
    elif mode == FitMode.CONTAIN:
        needs_enlarging = image.width < target_w and image.height < target_h
    else:  # STRETCH
        needs_enlarging = image.width < target_w or image.height < target_h

    if needs_enlarging and allow_ai_upscale and model_path is not None:
        upscaled = _upscale_with_fsrcnn(image, model_path)
        if upscaled is not None:
            image = upscaled

    if mode == FitMode.COVER:
        cropped = _resize_and_center_crop(image, target_w, target_h)
        return _flatten_onto(cropped, target_w, target_h, fill_color)
    if mode == FitMode.STRETCH:
        return _flatten_onto(
            image.resize((target_w, target_h), Image.Resampling.LANCZOS),
            target_w,
            target_h,
            fill_color,
        )

    # CONTAIN: scale to fit inside the panel, then pad to the exact size.
    scale = min(target_w / image.width, target_h / image.height)
    fitted_w = max(round(image.width * scale), 1)
    fitted_h = max(round(image.height * scale), 1)
    fitted = image.resize((fitted_w, fitted_h), Image.Resampling.LANCZOS)
    return _flatten_onto(fitted, target_w, target_h, fill_color)
