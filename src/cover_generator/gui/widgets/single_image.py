"""Single-image tool: make one image print-ready for services that take
front and back as separate uploads (e.g. photopis) and compute the spine."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from cover_generator.core.geometry import compute_single_panel_size, compute_spine_panel_size
from cover_generator.core.models import (
    TRIM_SIZE_PRESETS,
    ColorMode,
    FitMode,
    PaperType,
    SingleImageSpec,
    TrimSize,
)
from cover_generator.gui.widgets.cmyk_selector import CmykSelector
from cover_generator.gui.widgets.image_picker import ImagePicker
from cover_generator.gui.workers import SingleImageWorker

_CUSTOM_LABEL = "Custom..."


class SingleImageWidget(QWidget):
    """Sizes one image to trim (+ bleed) at a target DPI, upscaling if needed, and exports a JPG."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._worker: SingleImageWorker | None = None

        self.picker = ImagePicker(self.tr("Image"))
        self.source_info_label = QLabel("")
        self.source_info_label.setWordWrap(True)
        self.source_info_label.setObjectName("imagePropertiesLabel")

        self.result_preview = QLabel()
        self.result_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_preview.setMinimumSize(220, 280)
        self.result_preview.setObjectName("imagePickerThumbnail")
        self.result_preview.setText(self.tr("Result preview appears here"))

        # -- parameters (compact; mm only, no title/author) --------------
        self.trim_size_combo = QComboBox()
        for preset in TRIM_SIZE_PRESETS:
            self.trim_size_combo.addItem(preset.label, preset)
        self.trim_size_combo.addItem(self.tr(_CUSTOM_LABEL), None)
        self.trim_size_combo.setCurrentIndex(2)  # A5

        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(50.0, 500.0)
        self.width_spin.setSuffix(" mm")

        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(50.0, 500.0)
        self.height_spin.setSuffix(" mm")

        self.bleed_spin = QDoubleSpinBox()
        self.bleed_spin.setRange(0.0, 20.0)
        self.bleed_spin.setSingleStep(0.5)
        self.bleed_spin.setValue(3.0)
        self.bleed_spin.setSuffix(" mm")

        self.include_bleed_checkbox = QCheckBox(self.tr("Add bleed around the trim size"))
        self.include_bleed_checkbox.setChecked(True)
        self.include_bleed_checkbox.setToolTip(
            self.tr("Adds the bleed margin on all four sides. Most print services require it.")
        )

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)
        self.dpi_spin.setValue(300)
        self.dpi_spin.setSuffix(" dpi")

        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(70, 100)
        self.quality_spin.setValue(95)
        self.quality_spin.setSuffix(" %")

        # -- how the image is fitted when its shape != the panel's -----------
        self.fit_mode_combo = QComboBox()
        self.fit_mode_combo.addItem(self.tr("Fit whole image (pad)"), FitMode.CONTAIN)
        self.fit_mode_combo.addItem(self.tr("Fill & crop"), FitMode.COVER)
        self.fit_mode_combo.addItem(self.tr("Stretch"), FitMode.STRETCH)
        self.fit_mode_combo.setCurrentIndex(0)  # Contain: never crops the design
        self.fit_mode_combo.setToolTip(
            self.tr(
                "Fit whole image: nothing is cropped; the shorter sides are padded "
                "with the fill colour.\nFill & crop: fills the panel and trims the "
                "overflow.\nStretch: distorts the image to the exact panel size."
            )
        )

        self._fill_color = "#ffffff"
        self.fill_color_button = QPushButton()
        self.fill_color_button.setToolTip(
            self.tr("Colour used to pad the empty sides when fitting the whole image.")
        )
        self.fill_color_button.clicked.connect(self._pick_fill_color)
        self._apply_fill_color_swatch()

        # -- spine mode: size the panel from the page count ------------------
        self.spine_mode_checkbox = QCheckBox(self.tr("Spine mode (size from page count)"))
        self.spine_mode_checkbox.setToolTip(
            self.tr(
                "Sizes the output to the book's spine: width is computed from the "
                "page count and paper stock, height is the trim height (+ bleed)."
            )
        )

        self.pages_spin = QSpinBox()
        self.pages_spin.setRange(1, 2000)
        self.pages_spin.setValue(220)
        self.pages_spin.setSuffix(self.tr(" pages"))

        self.paper_combo = QComboBox()
        self.paper_combo.addItem(self.tr("Cream"), PaperType.CREAM)
        self.paper_combo.addItem(self.tr("White"), PaperType.WHITE)
        self.paper_combo.addItem(self.tr("Offset"), PaperType.OFFSET)

        # Override the computed spine width to match a print service's template.
        self.spine_override_checkbox = QCheckBox(self.tr("Override spine width"))
        self.spine_override_checkbox.setToolTip(
            self.tr(
                "Use an exact spine width instead of estimating it from the page "
                "count and paper stock -- set it to match your print service's own "
                "cover template."
            )
        )
        self.spine_width_spin = QDoubleSpinBox()
        self.spine_width_spin.setRange(1.0, 200.0)
        self.spine_width_spin.setSingleStep(0.1)
        self.spine_width_spin.setDecimals(2)
        self.spine_width_spin.setValue(18.15)
        self.spine_width_spin.setSuffix(" mm")
        self.spine_width_spin.setEnabled(False)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText(self.tr("Title (optional -- drawn on the spine)"))
        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText(self.tr("Author (optional -- drawn on the spine)"))

        self.cmyk_selector = CmykSelector()

        self.output_edit = QLineEdit()
        self.output_browse_button = QPushButton(self.tr("Browse..."))
        self.output_browse_button.clicked.connect(self._browse_output)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_edit)
        output_row.addWidget(self.output_browse_button)

        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form_layout.addRow(self.tr("Trim size:"), self.trim_size_combo)
        form_layout.addRow(self.tr("Width:"), self.width_spin)
        form_layout.addRow(self.tr("Height:"), self.height_spin)
        form_layout.addRow(self.tr("Bleed:"), self.bleed_spin)
        form_layout.addRow("", self.include_bleed_checkbox)
        form_layout.addRow(self.tr("Resolution:"), self.dpi_spin)
        form_layout.addRow(self.tr("JPG quality:"), self.quality_spin)
        form_layout.addRow("", self.spine_mode_checkbox)
        self.pages_row_label = QLabel(self.tr("Pages:"))
        form_layout.addRow(self.pages_row_label, self.pages_spin)
        self.paper_row_label = QLabel(self.tr("Paper:"))
        form_layout.addRow(self.paper_row_label, self.paper_combo)
        form_layout.addRow("", self.spine_override_checkbox)
        self.spine_width_row_label = QLabel(self.tr("Spine width:"))
        form_layout.addRow(self.spine_width_row_label, self.spine_width_spin)
        self.title_row_label = QLabel(self.tr("Title:"))
        form_layout.addRow(self.title_row_label, self.title_edit)
        self.author_row_label = QLabel(self.tr("Author:"))
        form_layout.addRow(self.author_row_label, self.author_edit)
        form_layout.addRow(self.tr("Fit mode:"), self.fit_mode_combo)
        self.fill_color_row_label = QLabel(self.tr("Pad colour:"))
        form_layout.addRow(self.fill_color_row_label, self.fill_color_button)
        form_layout.addRow(self.tr("Output JPG:"), output_row)

        self.target_info_label = QLabel("")
        self.target_info_label.setWordWrap(True)
        self.target_info_label.setObjectName("outputCanvasLabel")

        self.preview_button = QPushButton(self.tr("Preview"))
        self.generate_button = QPushButton(self.tr("Generate"))
        self.generate_button.setObjectName("generateButton")
        actions_row = QHBoxLayout()
        actions_row.addStretch()
        actions_row.addWidget(self.preview_button)
        actions_row.addWidget(self.generate_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        self.status_label = QLabel("")

        # -- layout: image column | parameters column --------------------
        left_column = QVBoxLayout()
        left_column.addWidget(self.picker)
        left_column.addWidget(self.source_info_label)
        left_column.addWidget(self.result_preview)
        left_column.addStretch()

        right_column = QVBoxLayout()
        right_column.addLayout(form_layout)
        right_column.addWidget(self.cmyk_selector)
        right_column.addWidget(self.target_info_label)
        right_column.addLayout(actions_row)
        right_column.addWidget(self.progress_bar)
        right_column.addWidget(self.status_label)
        right_column.addStretch()

        main_layout = QHBoxLayout(self)
        left_container = QWidget()
        left_container.setLayout(left_column)
        right_container = QWidget()
        right_container.setLayout(right_column)
        main_layout.addWidget(left_container, stretch=1)
        main_layout.addWidget(right_container, stretch=1)

        # -- wiring -------------------------------------------------------
        self.trim_size_combo.currentIndexChanged.connect(self._on_trim_size_changed)
        self._on_trim_size_changed(self.trim_size_combo.currentIndex())
        for spin in (self.width_spin, self.height_spin, self.bleed_spin, self.dpi_spin):
            spin.valueChanged.connect(self._update_info)
        self.include_bleed_checkbox.stateChanged.connect(self._update_info)
        self.cmyk_selector.changed.connect(self._update_info)
        self.picker.path_changed.connect(self._update_info)
        self.fit_mode_combo.currentIndexChanged.connect(self._on_fit_mode_changed)
        self.spine_mode_checkbox.stateChanged.connect(self._on_spine_mode_changed)
        for spin in (self.pages_spin, self.spine_width_spin):
            spin.valueChanged.connect(self._update_info)
        self.paper_combo.currentIndexChanged.connect(self._update_info)
        self.spine_override_checkbox.stateChanged.connect(self._on_spine_override_changed)
        self.preview_button.clicked.connect(self._on_preview_clicked)
        self.generate_button.clicked.connect(self._on_generate_clicked)
        self._on_fit_mode_changed(self.fit_mode_combo.currentIndex())
        self._on_spine_mode_changed(self.spine_mode_checkbox.checkState())
        self._update_info()

    # -- parameters ------------------------------------------------------

    @property
    def trim_size(self) -> TrimSize:
        return TrimSize(self.width_spin.value(), self.height_spin.value())

    def _on_trim_size_changed(self, index: int) -> None:
        preset: TrimSize | None = self.trim_size_combo.itemData(index)
        is_custom = preset is None
        self.width_spin.setEnabled(is_custom)
        self.height_spin.setEnabled(is_custom)
        if preset is not None:
            self.width_spin.setValue(preset.width_mm)
            self.height_spin.setValue(preset.height_mm)
        self._update_info()

    @property
    def spine_width_override(self) -> float | None:
        """The exact spine width in mm when overriding, else None (auto)."""
        if self.spine_override_checkbox.isChecked():
            return self.spine_width_spin.value()
        return None

    @property
    def fit_mode(self) -> FitMode:
        return self.fit_mode_combo.currentData()

    def _on_fit_mode_changed(self, _index: int) -> None:
        # Only "Fit whole image" pads, so the pad colour is irrelevant otherwise.
        needs_fill = self.fit_mode == FitMode.CONTAIN
        self.fill_color_row_label.setVisible(needs_fill)
        self.fill_color_button.setVisible(needs_fill)
        self._update_info()

    def _on_spine_mode_changed(self, _state: int) -> None:
        on = self.spine_mode_checkbox.isChecked()
        for widget in (
            self.pages_row_label,
            self.pages_spin,
            self.paper_row_label,
            self.paper_combo,
            self.spine_override_checkbox,
            self.title_row_label,
            self.title_edit,
            self.author_row_label,
            self.author_edit,
        ):
            widget.setVisible(on)
        # The spine-width row is a sub-option of spine mode; let its own handler
        # decide visibility so it stays hidden unless the override is enabled.
        self._on_spine_override_changed(self.spine_override_checkbox.checkState())

    def _on_spine_override_changed(self, _state: int) -> None:
        override = self.spine_override_checkbox.isChecked()
        spine_mode = self.spine_mode_checkbox.isChecked()
        self.spine_width_spin.setEnabled(override)
        self.spine_width_row_label.setVisible(spine_mode and override)
        self.spine_width_spin.setVisible(spine_mode and override)
        # When overriding, spine width no longer comes from pages x paper.
        for widget in (self.pages_spin, self.paper_combo):
            widget.setEnabled(not override)
        self._update_info()

    def _apply_fill_color_swatch(self) -> None:
        color = QColor(self._fill_color)
        text_color = "#000000" if color.lightnessF() > 0.5 else "#ffffff"
        self.fill_color_button.setText(self._fill_color)
        self.fill_color_button.setStyleSheet(
            f"background-color: {self._fill_color}; color: {text_color};"
        )

    def _pick_fill_color(self) -> None:
        chosen = QColorDialog.getColor(QColor(self._fill_color), self, self.tr("Pad colour"))
        if chosen.isValid():
            self._fill_color = chosen.name()
            self._apply_fill_color_swatch()

    def _browse_output(self) -> None:
        file_name, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save image as"), "", "JPEG (*.jpg *.jpeg)"
        )
        if file_name:
            self.output_edit.setText(file_name)

    # -- live info -------------------------------------------------------

    def _update_info(self, *_args) -> None:
        if self.spine_mode_checkbox.isChecked():
            target_w, target_h = compute_spine_panel_size(
                self.trim_size,
                self.bleed_spin.value(),
                self.dpi_spin.value(),
                self.pages_spin.value(),
                self.paper_combo.currentData(),
                include_bleed=self.include_bleed_checkbox.isChecked(),
                spine_width_mm=self.spine_width_override,
            )
        else:
            target_w, target_h = compute_single_panel_size(
                self.trim_size,
                self.bleed_spin.value(),
                self.dpi_spin.value(),
                include_bleed=self.include_bleed_checkbox.isChecked(),
            )
        color_label = (
            self.tr("CMYK") if self.cmyk_selector.color_mode == ColorMode.CMYK else self.tr("RGB")
        )
        self.target_info_label.setText(
            self.tr("Output: {w} x {h} px @ {dpi} dpi, JPG ({color})").format(
                w=target_w, h=target_h, dpi=self.dpi_spin.value(), color=color_label
            )
        )
        self._update_source_info(target_w, target_h)

    def _update_source_info(self, target_w: int, target_h: int) -> None:
        path = self.picker.path
        if path is None:
            self.source_info_label.setText(self.tr("No image selected."))
            return
        try:
            with Image.open(path) as img:
                width, height = img.size
                mode = img.mode
        except OSError:
            self.source_info_label.setText(self.tr("Could not read image file."))
            return

        lines = [self.tr("{w} x {h} px, {mode}").format(w=width, h=height, mode=mode)]
        if width < target_w or height < target_h:
            lines.append(
                self.tr("Smaller than {w} x {h} px -- will be upscaled.").format(
                    w=target_w, h=target_h
                )
            )
        else:
            lines.append(
                self.tr("Large enough for {w} x {h} px.").format(w=target_w, h=target_h)
            )
        self.source_info_label.setText("\n".join(lines))

    # -- spec / actions --------------------------------------------------

    def _build_spec(self, output_path: Path) -> SingleImageSpec | None:
        if self.picker.path is None:
            QMessageBox.warning(
                self,
                self.tr("Missing image"),
                self.tr("Please select an image to process."),
            )
            return None
        return SingleImageSpec(
            input_path=self.picker.path,
            output_path=output_path,
            trim_size=self.trim_size,
            bleed_mm=self.bleed_spin.value(),
            include_bleed=self.include_bleed_checkbox.isChecked(),
            dpi=self.dpi_spin.value(),
            spine_mode=self.spine_mode_checkbox.isChecked(),
            pages=self.pages_spin.value(),
            paper_type=self.paper_combo.currentData(),
            spine_width_mm=self.spine_width_override,
            title=self.title_edit.text().strip(),
            author=self.author_edit.text().strip(),
            fit_mode=self.fit_mode,
            fill_color=self._fill_color,
            jpg_quality=self.quality_spin.value(),
            color_mode=self.cmyk_selector.color_mode,
            cmyk_profile_path=self.cmyk_selector.cmyk_profile_path,
        )

    def _on_preview_clicked(self) -> None:
        if self.picker.path is None:
            QMessageBox.warning(
                self,
                self.tr("Missing image"),
                self.tr("Please select an image to process."),
            )
            return
        temp_path = Path(tempfile.gettempdir()) / "single_image_preview.jpg"
        spec = self._build_spec(temp_path)
        if spec is None:
            return
        spec.dpi = 96  # low-res, just to verify the crop
        # Preview in RGB regardless of the chosen mode: the crop is all we're
        # checking here, and Qt renders CMYK JPEGs with shifted colours.
        spec.color_mode = ColorMode.RGB
        self._run_worker(spec, is_preview=True)

    def _on_generate_clicked(self) -> None:
        text = self.output_edit.text().strip()
        if text:
            output_path = Path(text)
        else:
            file_name, _ = QFileDialog.getSaveFileName(
                self, self.tr("Save image as"), "", "JPEG (*.jpg *.jpeg)"
            )
            if not file_name:
                return
            output_path = Path(file_name)
            self.output_edit.setText(file_name)

        spec = self._build_spec(output_path)
        if spec is not None:
            self._run_worker(spec, is_preview=False)

    def _run_worker(self, spec: SingleImageSpec, *, is_preview: bool) -> None:
        self.generate_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self._worker = SingleImageWorker(spec)
        self._worker.progress.connect(self._on_progress)
        self._worker.succeeded.connect(
            lambda path: self._on_finished(path, is_preview=is_preview)
        )
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_progress(self, message: str, fraction: float) -> None:
        self.status_label.setText(message)
        self.progress_bar.setValue(int(fraction * 100))

    def _on_finished(self, path: Path, *, is_preview: bool) -> None:
        self.generate_button.setEnabled(True)
        self.preview_button.setEnabled(True)
        pixmap = QPixmap(str(path)).scaled(
            self.result_preview.width(),
            self.result_preview.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.result_preview.setPixmap(pixmap)
        if is_preview:
            self.status_label.setText(self.tr("Preview generated."))
            return
        self.status_label.setText(self.tr("Image saved: {}").format(path))
        QMessageBox.information(
            self, self.tr("Done"), self.tr("Image saved to:\n{}").format(path)
        )

    def _on_failed(self, message: str) -> None:
        self.generate_button.setEnabled(True)
        self.preview_button.setEnabled(True)
        self.status_label.setText(self.tr("Failed: {}").format(message))
        QMessageBox.critical(self, self.tr("Processing failed"), message)
