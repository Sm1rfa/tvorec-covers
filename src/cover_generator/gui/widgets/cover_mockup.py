"""Cover mockup tool: renders a blank, actual-size template PNG (no source
images) for use as a real-size guide layer in an external editor such as
Krita or Inkscape while designing actual cover art."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
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

from cover_generator.core.geometry import (
    MM_PER_UNIT,
    compute_canvas_layout_from_params,
    compute_spine_width_mm,
)
from cover_generator.core.models import TRIM_SIZE_PRESETS, MockupSpec, PaperType, TrimSize
from cover_generator.gui.widgets.preview import SchematicPreview
from cover_generator.gui.workers import MockupWorker

_CUSTOM_LABEL = "Custom..."


class CoverMockupWidget(QWidget):
    """Renders a blank, actual-size cover template PNG to use as a design guide."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._worker: MockupWorker | None = None

        self.result_preview = QLabel()
        self.result_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_preview.setMinimumSize(220, 280)
        self.result_preview.setObjectName("imagePickerThumbnail")
        self.result_preview.setText(self.tr("Result preview appears here"))

        self.schematic_preview = SchematicPreview()

        # -- trim size --------------------------------------------------
        self.trim_size_combo = QComboBox()
        for preset in TRIM_SIZE_PRESETS:
            self.trim_size_combo.addItem(preset.label, preset)
        self.trim_size_combo.addItem(self.tr(_CUSTOM_LABEL), None)
        self.trim_size_combo.setCurrentIndex(2)  # A5

        self.size_unit_combo = QComboBox()
        for unit in MM_PER_UNIT:
            self.size_unit_combo.addItem(self.tr(unit), unit)
        self._previous_size_mm_per_unit = MM_PER_UNIT[self.size_unit_combo.currentData()]

        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(50.0, 500.0)
        self.width_spin.setSuffix(" mm")

        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(50.0, 500.0)
        self.height_spin.setSuffix(" mm")

        # -- paper stock / page count -------------------------------------
        self.paper_combo = QComboBox()
        self.paper_combo.addItem(self.tr("Cream"), PaperType.CREAM)
        self.paper_combo.addItem(self.tr("White"), PaperType.WHITE)
        self.paper_combo.addItem(self.tr("Offset"), PaperType.OFFSET)

        self.pages_spin = QSpinBox()
        self.pages_spin.setRange(1, 2000)
        self.pages_spin.setValue(220)
        self.pages_spin.setSuffix(self.tr(" pages"))

        # -- bleed / danger zone, sharing one unit dropdown -----------------
        self.margin_unit_combo = QComboBox()
        for unit in MM_PER_UNIT:
            self.margin_unit_combo.addItem(self.tr(unit), unit)
        self._previous_margin_mm_per_unit = MM_PER_UNIT[self.margin_unit_combo.currentData()]

        self.bleed_spin = QDoubleSpinBox()
        self.bleed_spin.setRange(0.0, 20.0)
        self.bleed_spin.setSingleStep(0.5)
        self.bleed_spin.setValue(3.0)
        self.bleed_spin.setSuffix(" mm")

        self.danger_zone_spin = QDoubleSpinBox()
        self.danger_zone_spin.setRange(0.0, 30.0)
        self.danger_zone_spin.setSingleStep(0.5)
        self.danger_zone_spin.setValue(5.0)
        self.danger_zone_spin.setSuffix(" mm")

        # -- spine width override --------------------------------------------
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

        # -- resolution -------------------------------------------------------
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)
        self.dpi_spin.setValue(300)
        self.dpi_spin.setSuffix(" dpi")

        # -- output -------------------------------------------------------------
        self.output_edit = QLineEdit()
        self.output_browse_button = QPushButton(self.tr("Browse..."))
        self.output_browse_button.clicked.connect(self._browse_output)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_edit)
        output_row.addWidget(self.output_browse_button)

        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form_layout.addRow(self.tr("Trim size:"), self.trim_size_combo)
        form_layout.addRow(self.tr("Size unit:"), self.size_unit_combo)
        form_layout.addRow(self.tr("Width:"), self.width_spin)
        form_layout.addRow(self.tr("Height:"), self.height_spin)
        form_layout.addRow(self.tr("Paper type:"), self.paper_combo)
        form_layout.addRow(self.tr("Page count:"), self.pages_spin)
        form_layout.addRow(self.tr("Margin unit:"), self.margin_unit_combo)
        form_layout.addRow(self.tr("Bleed:"), self.bleed_spin)
        form_layout.addRow(self.tr("Danger zone:"), self.danger_zone_spin)
        form_layout.addRow("", self.spine_override_checkbox)
        self.spine_width_row_label = QLabel(self.tr("Spine width:"))
        form_layout.addRow(self.spine_width_row_label, self.spine_width_spin)
        form_layout.addRow(self.tr("Resolution:"), self.dpi_spin)
        form_layout.addRow(self.tr("Output PNG:"), output_row)

        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setObjectName("outputCanvasLabel")

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

        # -- layout: preview column | parameters column ------------------
        left_column = QVBoxLayout()
        left_column.addWidget(self.result_preview)
        left_column.addWidget(self.schematic_preview)
        left_column.addStretch()

        right_column = QVBoxLayout()
        right_column.addLayout(form_layout)
        right_column.addWidget(self.info_label)
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
        self.size_unit_combo.currentIndexChanged.connect(self._on_size_unit_changed)
        self.margin_unit_combo.currentIndexChanged.connect(self._on_margin_unit_changed)
        self.spine_override_checkbox.stateChanged.connect(self._on_spine_override_changed)
        for spin in (
            self.width_spin,
            self.height_spin,
            self.pages_spin,
            self.bleed_spin,
            self.danger_zone_spin,
            self.spine_width_spin,
            self.dpi_spin,
        ):
            spin.valueChanged.connect(self._update_info)
        self.paper_combo.currentIndexChanged.connect(self._update_info)
        self.preview_button.clicked.connect(self._on_preview_clicked)
        self.generate_button.clicked.connect(self._on_generate_clicked)

        self._on_trim_size_changed(self.trim_size_combo.currentIndex())
        self._on_spine_override_changed(self.spine_override_checkbox.checkState())
        self._update_info()

    # -- parameters ------------------------------------------------------

    @property
    def trim_size(self) -> TrimSize:
        mm_per_unit = MM_PER_UNIT[self.size_unit_combo.currentData()]
        return TrimSize(
            self.width_spin.value() * mm_per_unit, self.height_spin.value() * mm_per_unit
        )

    @property
    def bleed_mm(self) -> float:
        mm_per_unit = MM_PER_UNIT[self.margin_unit_combo.currentData()]
        return self.bleed_spin.value() * mm_per_unit

    @property
    def danger_zone_mm(self) -> float:
        mm_per_unit = MM_PER_UNIT[self.margin_unit_combo.currentData()]
        return self.danger_zone_spin.value() * mm_per_unit

    @property
    def spine_width_override(self) -> float | None:
        """The exact spine width in mm when overriding, else None (auto)."""
        if self.spine_override_checkbox.isChecked():
            return self.spine_width_spin.value()
        return None

    @property
    def paper_type(self) -> PaperType:
        # Qt's QVariant round-trip through QComboBox.itemData() silently
        # downgrades StrEnum members to plain str, which breaks core code
        # (generate_mockup) that relies on the real enum (e.g. its .value
        # attribute) -- coerce back at this GUI/core boundary.
        return PaperType(self.paper_combo.currentData())

    def _on_trim_size_changed(self, index: int) -> None:
        preset: TrimSize | None = self.trim_size_combo.itemData(index)
        is_custom = preset is None
        self.width_spin.setEnabled(is_custom)
        self.height_spin.setEnabled(is_custom)
        if preset is not None:
            mm_per_unit = MM_PER_UNIT[self.size_unit_combo.currentData()]
            self.width_spin.setValue(preset.width_mm / mm_per_unit)
            self.height_spin.setValue(preset.height_mm / mm_per_unit)
        self._update_info()

    def _on_size_unit_changed(self, index: int) -> None:
        unit = self.size_unit_combo.itemData(index)
        mm_per_unit = MM_PER_UNIT[unit]
        old_width_mm = self.width_spin.value() * self._previous_size_mm_per_unit
        old_height_mm = self.height_spin.value() * self._previous_size_mm_per_unit
        for spin in (self.width_spin, self.height_spin):
            spin.setSuffix(f" {unit}")
            spin.setRange(50.0 / mm_per_unit, 500.0 / mm_per_unit)
            spin.setSingleStep(1.0 if mm_per_unit == 1.0 else 0.1)
        self.width_spin.setValue(old_width_mm / mm_per_unit)
        self.height_spin.setValue(old_height_mm / mm_per_unit)
        self._previous_size_mm_per_unit = mm_per_unit
        self._update_info()

    def _on_margin_unit_changed(self, index: int) -> None:
        unit = self.margin_unit_combo.itemData(index)
        mm_per_unit = MM_PER_UNIT[unit]
        old_bleed_mm = self.bleed_spin.value() * self._previous_margin_mm_per_unit
        old_danger_zone_mm = self.danger_zone_spin.value() * self._previous_margin_mm_per_unit
        self.bleed_spin.setSuffix(f" {unit}")
        self.bleed_spin.setRange(0.0, 20.0 / mm_per_unit)
        self.bleed_spin.setSingleStep(0.5 if mm_per_unit == 1.0 else 0.1)
        self.danger_zone_spin.setSuffix(f" {unit}")
        self.danger_zone_spin.setRange(0.0, 30.0 / mm_per_unit)
        self.danger_zone_spin.setSingleStep(0.5 if mm_per_unit == 1.0 else 0.1)
        self.bleed_spin.setValue(old_bleed_mm / mm_per_unit)
        self.danger_zone_spin.setValue(old_danger_zone_mm / mm_per_unit)
        self._previous_margin_mm_per_unit = mm_per_unit
        self._update_info()

    def _on_spine_override_changed(self, _state: int) -> None:
        override = self.spine_override_checkbox.isChecked()
        self.spine_width_spin.setEnabled(override)
        self.spine_width_row_label.setVisible(override)
        self.spine_width_spin.setVisible(override)
        # When overriding, spine width no longer comes from pages x paper.
        self.pages_spin.setEnabled(not override)
        self.paper_combo.setEnabled(not override)
        self._update_info()

    def _browse_output(self) -> None:
        file_name, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save mockup as"), "", "PNG (*.png)"
        )
        if file_name:
            self.output_edit.setText(file_name)

    # -- live info / preview ----------------------------------------------

    def _update_info(self, *_args) -> None:
        trim_size = self.trim_size
        layout_info = compute_canvas_layout_from_params(
            trim_size,
            self.bleed_mm,
            self.dpi_spin.value(),
            self.pages_spin.value(),
            self.paper_type,
            spine_width_mm=self.spine_width_override,
        )
        self.schematic_preview.set_layout(layout_info)

        spine_mm = (
            self.spine_width_override
            if self.spine_width_override is not None
            else compute_spine_width_mm(self.pages_spin.value(), self.paper_type)
        )
        total_w_mm = trim_size.width_mm * 2 + spine_mm + self.bleed_mm * 2
        total_h_mm = trim_size.height_mm + self.bleed_mm * 2
        self.info_label.setText(
            self.tr(
                "Canvas: {w_mm:.1f} x {h_mm:.1f} mm / {w_px} x {h_px} px @ {dpi} dpi "
                "-- spine {spine:.1f} mm"
            ).format(
                w_mm=total_w_mm,
                h_mm=total_h_mm,
                w_px=layout_info.total_w_px,
                h_px=layout_info.total_h_px,
                dpi=self.dpi_spin.value(),
                spine=spine_mm,
            )
        )

    # -- spec / actions -----------------------------------------------------

    def _labels(self) -> dict[str, str]:
        # Baked into the PNG itself (core has no i18n of its own), so this is
        # what makes the rendered template text follow the app's language.
        return {
            "back": self.tr("BACK COVER"),
            "front": self.tr("FRONT COVER"),
            "trim": self.tr("Trim"),
            "bleed": self.tr("Bleed"),
            "danger_zone": self.tr("Danger zone"),
            "spine": self.tr("Spine"),
            "pages": self.tr("pages"),
            "canvas": self.tr("Canvas"),
            "dpi": self.tr("DPI"),
        }

    def _build_spec(self, output_path: Path, *, dpi: int | None = None) -> MockupSpec:
        return MockupSpec(
            output_path=output_path,
            trim_size=self.trim_size,
            pages=self.pages_spin.value(),
            paper_type=self.paper_type,
            bleed_mm=self.bleed_mm,
            danger_zone_mm=self.danger_zone_mm,
            dpi=dpi if dpi is not None else self.dpi_spin.value(),
            spine_width_mm=self.spine_width_override,
            labels=self._labels(),
        )

    def _on_preview_clicked(self) -> None:
        temp_path = Path(tempfile.gettempdir()) / "cover_mockup_preview.png"
        spec = self._build_spec(temp_path, dpi=96)
        self._run_worker(spec, is_preview=True)

    def _on_generate_clicked(self) -> None:
        text = self.output_edit.text().strip()
        if text:
            output_path = Path(text)
        else:
            file_name, _ = QFileDialog.getSaveFileName(
                self, self.tr("Save mockup as"), "", "PNG (*.png)"
            )
            if not file_name:
                return
            output_path = Path(file_name)
            self.output_edit.setText(file_name)

        spec = self._build_spec(output_path)
        self._run_worker(spec, is_preview=False)

    def _run_worker(self, spec: MockupSpec, *, is_preview: bool) -> None:
        self.generate_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self._worker = MockupWorker(spec)
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
        self.status_label.setText(self.tr("Mockup saved: {}").format(path))
        QMessageBox.information(
            self, self.tr("Done"), self.tr("Mockup saved to:\n{}").format(path)
        )

    def _on_failed(self, message: str) -> None:
        self.generate_button.setEnabled(True)
        self.preview_button.setEnabled(True)
        self.status_label.setText(self.tr("Failed: {}").format(message))
        QMessageBox.critical(self, self.tr("Generation failed"), message)
