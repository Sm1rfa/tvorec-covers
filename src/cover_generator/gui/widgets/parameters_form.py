"""Form widget for all non-image CoverSpec parameters."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from cover_generator.core.icc_profiles import (
    KNOWN_CMYK_PROFILES,
    expected_profile_path,
    known_profile_path,
)
from cover_generator.core.models import TRIM_SIZE_PRESETS, ColorMode, PaperType, TrimSize

_CUSTOM_LABEL = "Custom..."
_MM_PER_UNIT = {"mm": 1.0, "cm": 10.0}
_CUSTOM_PROFILE = "__custom__"


class ParametersForm(QWidget):
    """Collects page count, paper type, trim size, bleed, DPI, title/author, output path."""

    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.pages_spin = QSpinBox()
        self.pages_spin.setRange(1, 5000)
        self.pages_spin.setValue(220)

        self.paper_type_combo = QComboBox()
        self.paper_type_combo.addItem(self.tr("Cream"), PaperType.CREAM)
        self.paper_type_combo.addItem(self.tr("White"), PaperType.WHITE)
        self.paper_type_combo.addItem(self.tr("Offset"), PaperType.OFFSET)

        self.trim_size_combo = QComboBox()
        for preset in TRIM_SIZE_PRESETS:
            self.trim_size_combo.addItem(preset.label, preset)
        self.trim_size_combo.addItem(self.tr(_CUSTOM_LABEL), None)
        self.trim_size_combo.setCurrentIndex(2)  # A5

        self.size_unit_combo = QComboBox()
        self.size_unit_combo.addItem(self.tr("mm"), "mm")
        self.size_unit_combo.addItem(self.tr("cm"), "cm")
        self._previous_mm_per_unit = _MM_PER_UNIT[self.size_unit_combo.currentData()]

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

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)
        self.dpi_spin.setValue(300)
        self.dpi_spin.setSuffix(" dpi")

        self.color_mode_combo = QComboBox()
        # See the comment on cmyk_profile_combo below -- same fix, the item
        # text is long enough to otherwise force the column too wide.
        self.color_mode_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.color_mode_combo.setMinimumContentsLength(20)
        self.color_mode_combo.addItem(
            self.tr("RGB (screen / most print-on-demand)"), ColorMode.RGB
        )
        self.color_mode_combo.addItem(
            self.tr("CMYK (offset / commercial print)"), ColorMode.CMYK
        )
        self.color_mode_combo.setToolTip(
            self.tr(
                "CMYK conversion is a basic, uncalibrated conversion with no ICC "
                "profile. Check with your print house which color mode they require, "
                "and verify colors before final submission."
            )
        )

        self._custom_cmyk_profile_path: Path | None = None
        self.cmyk_profile_combo = QComboBox()
        # Some preset labels are long (e.g. "PSO Uncoated v3 (FOGRA52, EU
        # offset)"); without this, the combo's default size-adjust policy
        # grows to fit the widest item, forcing the whole column wider than
        # the available space. Cap the closed-box width; the dropdown popup
        # still shows full item text.
        self.cmyk_profile_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.cmyk_profile_combo.setMinimumContentsLength(20)
        self.cmyk_profile_combo.addItem(
            self.tr("Generic (no profile, basic conversion)"), None
        )
        for label in KNOWN_CMYK_PROFILES:
            self.cmyk_profile_combo.addItem(label, label)
        self.cmyk_profile_combo.addItem(self.tr(_CUSTOM_LABEL), _CUSTOM_PROFILE)

        self.cmyk_profile_status_label = QLabel("")
        self.cmyk_profile_status_label.setWordWrap(True)
        self.cmyk_profile_status_label.setObjectName("cmykProfileStatusLabel")

        self.title_edit = QLineEdit()
        self.author_edit = QLineEdit()

        self.export_png_checkbox = QCheckBox(self.tr("Also save a PNG copy"))
        self.export_png_checkbox.setToolTip(
            self.tr("Saves a full-resolution PNG alongside the PDF, for quality checks.")
        )

        self.output_edit = QLineEdit()
        self.output_browse_button = QPushButton(self.tr("Browse..."))
        self.output_browse_button.clicked.connect(self._browse_output)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_edit)
        output_row.addWidget(self.output_browse_button)

        # The status label below holds variable-length wrapped text (e.g. a
        # "profile not found at ..." warning). QFormLayout doesn't size its
        # rows correctly for word-wrapped QLabels -- the row collapses to a
        # single line and the wrapped text gets clipped by the row below it.
        # So it lives in the outer QVBoxLayout instead, where wrapping works.
        # QFormLayout shares one label-column width across *all* rows, so the
        # single longest label (worse in Bulgarian, where several labels run
        # longer than their English source strings) would otherwise force
        # every row's label column wide -- even rows pairing with a narrow
        # field. WrapLongRows lets each row size independently, stacking
        # label above field only when that row actually needs to.
        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form_layout.addRow(self.tr("Page count:"), self.pages_spin)
        form_layout.addRow(self.tr("Paper type:"), self.paper_type_combo)
        form_layout.addRow(self.tr("Trim size:"), self.trim_size_combo)
        form_layout.addRow(self.tr("Size unit:"), self.size_unit_combo)
        form_layout.addRow(self.tr("Width:"), self.width_spin)
        form_layout.addRow(self.tr("Height:"), self.height_spin)
        form_layout.addRow(self.tr("Bleed:"), self.bleed_spin)
        form_layout.addRow(self.tr("Resolution:"), self.dpi_spin)
        form_layout.addRow(self.tr("Color mode:"), self.color_mode_combo)
        form_layout.addRow(self.tr("CMYK profile:"), self.cmyk_profile_combo)

        bottom_form_layout = QFormLayout()
        bottom_form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        bottom_form_layout.addRow(self.tr("Title:"), self.title_edit)
        bottom_form_layout.addRow(self.tr("Author:"), self.author_edit)
        bottom_form_layout.addRow(self.tr("Output PDF:"), output_row)
        bottom_form_layout.addRow("", self.export_png_checkbox)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addWidget(self.cmyk_profile_status_label)
        layout.addLayout(bottom_form_layout)

        self.trim_size_combo.currentIndexChanged.connect(self._on_trim_size_changed)
        self._on_trim_size_changed(self.trim_size_combo.currentIndex())
        self.size_unit_combo.currentIndexChanged.connect(self._on_size_unit_changed)
        self.color_mode_combo.currentIndexChanged.connect(self._on_color_mode_changed)
        self.cmyk_profile_combo.currentIndexChanged.connect(self._on_cmyk_profile_changed)
        self._on_color_mode_changed(self.color_mode_combo.currentIndex())

        for widget in (
            self.pages_spin,
            self.paper_type_combo,
            self.trim_size_combo,
            self.size_unit_combo,
            self.width_spin,
            self.height_spin,
            self.bleed_spin,
            self.dpi_spin,
            self.color_mode_combo,
            self.cmyk_profile_combo,
            self.title_edit,
            self.author_edit,
            self.output_edit,
            self.export_png_checkbox,
        ):
            signal = getattr(widget, "textChanged", None) or getattr(widget, "valueChanged", None)
            signal = signal or getattr(widget, "currentIndexChanged", None)
            signal = signal or getattr(widget, "stateChanged", None)
            if signal is not None:
                signal.connect(lambda *_args: self.changed.emit())

    def _on_trim_size_changed(self, index: int) -> None:
        preset: TrimSize | None = self.trim_size_combo.itemData(index)
        is_custom = preset is None
        self.width_spin.setEnabled(is_custom)
        self.height_spin.setEnabled(is_custom)
        if preset is not None:
            mm_per_unit = _MM_PER_UNIT[self.size_unit_combo.currentData()]
            self.width_spin.setValue(preset.width_mm / mm_per_unit)
            self.height_spin.setValue(preset.height_mm / mm_per_unit)

    def _on_size_unit_changed(self, index: int) -> None:
        unit = self.size_unit_combo.itemData(index)
        mm_per_unit = _MM_PER_UNIT[unit]
        old_width_mm = self.width_spin.value() * self._previous_mm_per_unit
        old_height_mm = self.height_spin.value() * self._previous_mm_per_unit
        for spin in (self.width_spin, self.height_spin):
            spin.setSuffix(f" {unit}")
            spin.setRange(50.0 / mm_per_unit, 500.0 / mm_per_unit)
            spin.setSingleStep(1.0 if mm_per_unit == 1.0 else 0.1)
        self.width_spin.setValue(old_width_mm / mm_per_unit)
        self.height_spin.setValue(old_height_mm / mm_per_unit)
        self._previous_mm_per_unit = mm_per_unit

    def _on_color_mode_changed(self, index: int) -> None:
        is_cmyk = self.color_mode_combo.itemData(index) == ColorMode.CMYK
        self.cmyk_profile_combo.setEnabled(is_cmyk)
        self.cmyk_profile_status_label.setVisible(is_cmyk)
        if is_cmyk:
            self._update_cmyk_profile_status()
        else:
            self.cmyk_profile_status_label.setText("")

    def _on_cmyk_profile_changed(self, index: int) -> None:
        data = self.cmyk_profile_combo.itemData(index)
        if data == _CUSTOM_PROFILE:
            file_name, _ = QFileDialog.getOpenFileName(
                self, self.tr("Select ICC profile"), "", "ICC Profiles (*.icc *.icm)"
            )
            if file_name:
                self._custom_cmyk_profile_path = Path(file_name)
            elif self._custom_cmyk_profile_path is None:
                self.cmyk_profile_combo.setCurrentIndex(0)
                return
        self._update_cmyk_profile_status()

    def _update_cmyk_profile_status(self) -> None:
        # Full absolute paths have no spaces to wrap on, so they force the
        # label (and the whole column) wider than the available space.
        # Show just the filename inline and put the full path in a tooltip.
        data = self.cmyk_profile_combo.currentData()
        self.cmyk_profile_status_label.setToolTip("")
        if data is None:
            self.cmyk_profile_status_label.setText("")
        elif data == _CUSTOM_PROFILE:
            if self._custom_cmyk_profile_path is not None:
                self.cmyk_profile_status_label.setText(
                    self.tr("Using: {}").format(self._custom_cmyk_profile_path.name)
                )
                self.cmyk_profile_status_label.setToolTip(str(self._custom_cmyk_profile_path))
            else:
                self.cmyk_profile_status_label.setText(self.tr("No file selected."))
        elif (resolved := known_profile_path(data)) is not None:
            self.cmyk_profile_status_label.setText(self.tr("Found: {}").format(resolved.name))
            self.cmyk_profile_status_label.setToolTip(str(resolved))
        else:
            path = expected_profile_path(data)
            self.cmyk_profile_status_label.setText(
                self.tr(
                    "Not found ({}). Get this profile from its publisher (e.g. the "
                    "European Color Initiative or IDEAlliance) and place it in the "
                    "folder shown in this tooltip. Using basic conversion until then."
                ).format(path.name)
            )
            self.cmyk_profile_status_label.setToolTip(str(path))

    def _browse_output(self) -> None:
        file_name, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save cover as"), "", "PDF (*.pdf)"
        )
        if file_name:
            self.output_edit.setText(file_name)

    @property
    def trim_size(self) -> TrimSize:
        mm_per_unit = _MM_PER_UNIT[self.size_unit_combo.currentData()]
        return TrimSize(
            self.width_spin.value() * mm_per_unit, self.height_spin.value() * mm_per_unit
        )

    @property
    def export_png(self) -> bool:
        return self.export_png_checkbox.isChecked()

    @property
    def color_mode(self) -> ColorMode:
        return self.color_mode_combo.currentData()

    @property
    def cmyk_profile_path(self) -> Path | None:
        data = self.cmyk_profile_combo.currentData()
        if data is None:
            return None
        if data == _CUSTOM_PROFILE:
            return self._custom_cmyk_profile_path
        return known_profile_path(data)

    @property
    def paper_type(self) -> PaperType:
        return self.paper_type_combo.currentData()

    @property
    def output_path(self) -> Path | None:
        text = self.output_edit.text().strip()
        return Path(text) if text else None
