"""Reusable colour-mode + CMYK ICC profile picker.

Encapsulates the RGB/CMYK combo, the known-profile preset combo (plus a
"Custom..." file picker), and the status label that reports whether the
selected profile file was found on disk. Emits ``changed`` whenever the
effective colour mode or profile selection changes.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from cover_generator.core.icc_profiles import (
    KNOWN_CMYK_PROFILES,
    expected_profile_path,
    known_profile_path,
)
from cover_generator.core.models import ColorMode

_CUSTOM_LABEL = "Custom..."
_CUSTOM_PROFILE = "__custom__"


class CmykSelector(QWidget):
    """Colour mode + CMYK profile controls, sharing the cover builder's UX."""

    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._custom_cmyk_profile_path: Path | None = None

        self.color_mode_combo = QComboBox()
        # Long item text would otherwise force the label column too wide; cap
        # the closed-box width while the popup still shows full text.
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
                "Without an ICC profile, CMYK is a basic, uncalibrated conversion. "
                "Check with your print house which color mode they require, and "
                "verify colors before final submission."
            )
        )

        self.cmyk_profile_combo = QComboBox()
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

        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form_layout.addRow(self.tr("Color mode:"), self.color_mode_combo)
        form_layout.addRow(self.tr("CMYK profile:"), self.cmyk_profile_combo)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(form_layout)
        layout.addWidget(self.cmyk_profile_status_label)

        self.color_mode_combo.currentIndexChanged.connect(self._on_color_mode_changed)
        self.cmyk_profile_combo.currentIndexChanged.connect(self._on_cmyk_profile_changed)
        self.color_mode_combo.currentIndexChanged.connect(lambda *_a: self.changed.emit())
        self.cmyk_profile_combo.currentIndexChanged.connect(lambda *_a: self.changed.emit())
        self._on_color_mode_changed(self.color_mode_combo.currentIndex())

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
        # label (and column) wider than available. Show just the filename
        # inline and put the full path in a tooltip.
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
