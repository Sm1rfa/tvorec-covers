"""The full wrap-around cover builder: image pickers, parameters, preview, generate."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from cover_generator.core.geometry import compute_canvas_layout
from cover_generator.core.models import CoverSpec
from cover_generator.gui.widgets.image_info_panel import ImagePropertiesLabel, OutputCanvasLabel
from cover_generator.gui.widgets.image_picker import ImagePicker
from cover_generator.gui.widgets.parameters_form import ParametersForm
from cover_generator.gui.widgets.preview import SchematicPreview
from cover_generator.gui.workers import GenerateWorker


class CoverBuilderWidget(QWidget):
    """Builds one print-ready wrap-around cover (back + spine + front) as a PDF."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._worker: GenerateWorker | None = None

        self.front_picker = ImagePicker(self.tr("Front cover"))
        self.back_picker = ImagePicker(self.tr("Back cover"))
        self.spine_picker = ImagePicker(self.tr("Spine"), optional=True)

        self.front_info_label = ImagePropertiesLabel()
        self.back_info_label = ImagePropertiesLabel()
        self.spine_info_label = ImagePropertiesLabel(is_spine=True)

        pickers_row = QHBoxLayout()
        for picker, info_label in (
            (self.back_picker, self.back_info_label),
            (self.spine_picker, self.spine_info_label),
            (self.front_picker, self.front_info_label),
        ):
            column = QVBoxLayout()
            column.addWidget(picker)
            column.addWidget(info_label)
            pickers_row.addLayout(column)

        self.parameters_form = ParametersForm()
        self.output_canvas_label = OutputCanvasLabel()
        self.preview = SchematicPreview()

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

        right_column = QVBoxLayout()
        right_column.addWidget(self.parameters_form)
        right_column.addWidget(self.output_canvas_label)
        right_column.addWidget(self.preview)
        right_column.addLayout(actions_row)
        right_column.addWidget(self.progress_bar)
        right_column.addWidget(self.status_label)

        main_layout = QHBoxLayout(self)
        pickers_container = QWidget()
        pickers_container.setLayout(pickers_row)
        main_layout.addWidget(pickers_container, stretch=2)

        right_container = QWidget()
        right_container.setLayout(right_column)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        right_scroll.setWidget(right_container)
        main_layout.addWidget(right_scroll, stretch=2)

        self.parameters_form.changed.connect(self._update_preview)
        self.parameters_form.changed.connect(self._update_image_info)
        self.front_picker.path_changed.connect(self._update_image_info)
        self.back_picker.path_changed.connect(self._update_image_info)
        self.spine_picker.path_changed.connect(self._update_image_info)
        self.preview_button.clicked.connect(self._on_preview_clicked)
        self.generate_button.clicked.connect(self._on_generate_clicked)
        self._update_preview()
        self._update_image_info()

    # -- spec building -------------------------------------------------

    def _build_spec(self, output_path: Path, dpi: int | None = None) -> CoverSpec | None:
        if self.front_picker.path is None or self.back_picker.path is None:
            QMessageBox.warning(
                self,
                self.tr("Missing images"),
                self.tr("Please select both a front and a back cover image."),
            )
            return None

        form = self.parameters_form
        return CoverSpec(
            front_path=self.front_picker.path,
            back_path=self.back_picker.path,
            spine_path=self.spine_picker.path,
            output_path=output_path,
            pages=form.pages_spin.value(),
            paper_type=form.paper_type,
            trim_size=form.trim_size,
            bleed_mm=form.bleed_spin.value(),
            dpi=dpi if dpi is not None else form.dpi_spin.value(),
            title=form.title_edit.text(),
            author=form.author_edit.text(),
            export_png=form.export_png,
            color_mode=form.color_mode,
            cmyk_profile_path=form.cmyk_profile_path,
        )

    def _update_preview(self) -> None:
        form = self.parameters_form
        spec = CoverSpec(
            front_path=Path("front"),
            back_path=Path("back"),
            output_path=Path("out.pdf"),
            pages=form.pages_spin.value(),
            paper_type=form.paper_type,
            trim_size=form.trim_size,
            bleed_mm=form.bleed_spin.value(),
            dpi=form.dpi_spin.value(),
        )
        self.preview.set_layout(compute_canvas_layout(spec))

    def _update_image_info(self) -> None:
        form = self.parameters_form
        spec = CoverSpec(
            front_path=Path("front"),
            back_path=Path("back"),
            output_path=Path("out.pdf"),
            pages=form.pages_spin.value(),
            paper_type=form.paper_type,
            trim_size=form.trim_size,
            bleed_mm=form.bleed_spin.value(),
            dpi=form.dpi_spin.value(),
        )
        layout_info = compute_canvas_layout(spec)

        self.front_info_label.update_info(
            self.front_picker.path, (layout_info.panel_w_px, layout_info.panel_h_px)
        )
        self.back_info_label.update_info(
            self.back_picker.path, (layout_info.panel_w_px, layout_info.panel_h_px)
        )
        self.spine_info_label.update_info(
            self.spine_picker.path, (layout_info.spine_w_px, layout_info.total_h_px)
        )
        self.output_canvas_label.update_info(layout_info, form.color_mode, form.dpi_spin.value())

    # -- actions ---------------------------------------------------------

    def _on_preview_clicked(self) -> None:
        temp_path = Path(tempfile.gettempdir()) / "cover_generator_preview.pdf"
        spec = self._build_spec(temp_path, dpi=96)
        if spec is not None:
            self._run_worker(spec, is_preview=True)

    def _on_generate_clicked(self) -> None:
        output_path = self.parameters_form.output_path
        if output_path is None:
            file_name, _ = QFileDialog.getSaveFileName(
                self, self.tr("Save cover as"), "", "PDF (*.pdf)"
            )
            if not file_name:
                return
            output_path = Path(file_name)
            self.parameters_form.output_edit.setText(file_name)

        spec = self._build_spec(output_path)
        if spec is not None:
            self._run_worker(spec, is_preview=False)

    def _run_worker(self, spec: CoverSpec, *, is_preview: bool) -> None:
        self.generate_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self._worker = GenerateWorker(spec)
        self._worker.progress.connect(self._on_progress)
        self._worker.succeeded.connect(
            lambda path: self._on_finished(path, is_preview=is_preview, export_png=spec.export_png)
        )
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_progress(self, message: str, fraction: float) -> None:
        self.status_label.setText(message)
        self.progress_bar.setValue(int(fraction * 100))

    def _on_finished(self, path: Path, *, is_preview: bool, export_png: bool = False) -> None:
        self.generate_button.setEnabled(True)
        self.preview_button.setEnabled(True)
        if is_preview:
            self.status_label.setText(self.tr("Preview generated: {}").format(path))
            return

        self.status_label.setText(self.tr("Cover generated: {}").format(path))
        if export_png:
            png_path = path.with_suffix(".png")
            QMessageBox.information(
                self,
                self.tr("Done"),
                self.tr("Cover saved to:\n{}\n\nPNG copy saved to:\n{}").format(path, png_path),
            )
        else:
            QMessageBox.information(
                self,
                self.tr("Done"),
                self.tr("Cover saved to:\n{}").format(path),
            )

    def _on_failed(self, message: str) -> None:
        self.generate_button.setEnabled(True)
        self.preview_button.setEnabled(True)
        self.status_label.setText(self.tr("Failed: {}").format(message))
        QMessageBox.critical(self, self.tr("Generation failed"), message)
