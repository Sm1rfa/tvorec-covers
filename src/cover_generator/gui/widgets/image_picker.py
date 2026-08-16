"""A drag-and-drop / file-dialog image slot with a thumbnail preview."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

_IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp)"


class ImagePicker(QFrame):
    """One labeled drop target for a front/back/spine cover image."""

    path_changed = Signal(object)  # Path | None

    def __init__(self, title: str, *, optional: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("imagePicker")
        self._path: Path | None = None
        self._optional = optional

        self._title_label = QLabel(title)
        self._title_label.setObjectName("imagePickerTitle")

        self._thumbnail = QLabel()
        self._thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumbnail.setMinimumSize(140, 180)
        self._thumbnail.setObjectName("imagePickerThumbnail")
        self._set_placeholder_text()

        self._browse_button = QPushButton(self.tr("Browse..."))
        self._browse_button.clicked.connect(self._browse)

        self._clear_button = QPushButton(self.tr("Clear"))
        self._clear_button.clicked.connect(self.clear)
        self._clear_button.setEnabled(False)

        buttons_row = QHBoxLayout()
        buttons_row.addWidget(self._browse_button)
        buttons_row.addWidget(self._clear_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._title_label)
        layout.addWidget(self._thumbnail)
        layout.addLayout(buttons_row)

    def _set_placeholder_text(self) -> None:
        if self._optional:
            hint = self.tr("Drop image here\nor optional")
        else:
            hint = self.tr("Drop image here")
        self._thumbnail.setText(hint)

    @property
    def path(self) -> Path | None:
        return self._path

    def set_path(self, path: Path | None) -> None:
        self._path = path
        if path is None:
            self._thumbnail.setPixmap(QPixmap())
            self._set_placeholder_text()
            self._clear_button.setEnabled(False)
        else:
            pixmap = QPixmap(str(path)).scaled(
                self._thumbnail.width(),
                self._thumbnail.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._thumbnail.setPixmap(pixmap)
            self._clear_button.setEnabled(True)
        self.path_changed.emit(path)

    def clear(self) -> None:
        self.set_path(None)

    def _browse(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(self, self.tr("Select image"), "", _IMAGE_FILTER)
        if file_name:
            self.set_path(Path(file_name))

    def dragEnterEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802 (Qt override)
        urls = event.mimeData().urls()
        if urls:
            self.set_path(Path(urls[0].toLocalFile()))
