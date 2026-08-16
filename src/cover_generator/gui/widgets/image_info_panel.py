"""Compact widgets reporting native image properties and output canvas info."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtWidgets import QLabel

from cover_generator.core.geometry import CanvasLayout
from cover_generator.core.models import ColorMode


class ImagePropertiesLabel(QLabel):
    """Compact, read-only report of one image's resolution/DPI/mode and
    whether it meets the pixel size the current layout requires. Meant to sit
    directly under that image's picker widget, so no title duplication."""

    def __init__(self, *, is_spine: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._is_spine = is_spine
        self.setWordWrap(True)
        self.setObjectName("imagePropertiesLabel")
        self.update_info(None, None)

    def update_info(self, path: Path | None, required: tuple[int, int] | None) -> None:
        if path is None:
            if self._is_spine:
                self.setText(
                    self.tr("No image -- a plain black spine with title text will be used.")
                )
            else:
                self.setText(self.tr("No image selected."))
            return

        try:
            with Image.open(path) as img:
                width, height = img.size
                mode = img.mode
                dpi_info = img.info.get("dpi")
        except OSError:
            self.setText(self.tr("Could not read image file."))
            return

        dpi_text = (
            self.tr("{x:.0f} x {y:.0f}").format(x=dpi_info[0], y=dpi_info[1])
            if dpi_info
            else self.tr("not embedded")
        )

        lines = [
            self.tr("{w} x {h} px, {mode}, DPI: {dpi}").format(
                w=width, h=height, mode=mode, dpi=dpi_text
            )
        ]

        if required is not None:
            req_w, req_h = required
            if width >= req_w and height >= req_h:
                lines.append(self.tr("Meets required {w} x {h} px.").format(w=req_w, h=req_h))
            else:
                lines.append(
                    self.tr("Below required {w} x {h} px -- will be upscaled.").format(
                        w=req_w, h=req_h
                    )
                )

        self.setText("\n".join(lines))


class OutputCanvasLabel(QLabel):
    """Compact summary of the final canvas size/DPI/color mode for the current settings."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWordWrap(True)
        self.setObjectName("outputCanvasLabel")

    def update_info(self, layout_info: CanvasLayout, color_mode: ColorMode, dpi: int) -> None:
        mode_label = (
            self.tr("CMYK (offset / commercial print)")
            if color_mode == ColorMode.CMYK
            else self.tr("RGB (screen / most print-on-demand)")
        )
        self.setText(
            self.tr(
                "Canvas: {w} x {h} px @ {dpi} dpi, {mode}\n"
                "Note: verify final colors with your print house before submitting."
            ).format(w=layout_info.total_w_px, h=layout_info.total_h_px, dpi=dpi, mode=mode_label)
        )
