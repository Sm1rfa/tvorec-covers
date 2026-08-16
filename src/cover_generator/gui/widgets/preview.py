"""A schematic preview of the front/spine/back panel proportions."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from cover_generator.core.geometry import CanvasLayout


class SchematicPreview(QWidget):
    """Draws proportioned back/spine/front rectangles for the current layout."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(160)
        self._layout_info: CanvasLayout | None = None

    def set_layout(self, layout_info: CanvasLayout | None) -> None:
        self._layout_info = layout_info
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(4, 4, -4, -4)
        painter.fillRect(rect, QColor("#f0f0f0"))

        if self._layout_info is None:
            painter.setPen(QPen(QColor("#888888")))
            painter.drawText(
                rect, Qt.AlignmentFlag.AlignCenter, self.tr("Set parameters to see the layout")
            )
            return

        layout_info = self._layout_info
        scale = rect.width() / layout_info.total_w_px

        def scaled_rect(x_px: int, width_px: int):
            x = rect.left() + int(x_px * scale)
            w = max(int(width_px * scale), 1)
            return x, rect.top(), w, rect.height()

        back_x, back_y, back_w, h = scaled_rect(layout_info.back_x, layout_info.panel_w_px)
        spine_x, spine_y, spine_w, _ = scaled_rect(layout_info.spine_x, layout_info.spine_w_px)
        front_x, front_y, front_w, _ = scaled_rect(layout_info.front_x, layout_info.panel_w_px)

        painter.fillRect(back_x, back_y, back_w, h, QColor("#90caf9"))
        painter.fillRect(spine_x, spine_y, spine_w, h, QColor("#616161"))
        painter.fillRect(front_x, front_y, front_w, h, QColor("#a5d6a7"))

        painter.setPen(QPen(QColor("#212121")))
        painter.drawText(back_x, back_y, back_w, h, Qt.AlignmentFlag.AlignCenter, self.tr("Back"))
        painter.drawText(
            front_x, front_y, front_w, h, Qt.AlignmentFlag.AlignCenter, self.tr("Front")
        )
