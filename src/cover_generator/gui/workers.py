"""Runs the core pipeline on a background thread so the UI never blocks."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from cover_generator.core.mockup import generate_mockup
from cover_generator.core.models import CoverSpec, MockupSpec, SingleImageSpec
from cover_generator.core.pipeline import generate_cover
from cover_generator.core.single import process_single_image


class GenerateWorker(QThread):
    """Runs generate_cover() off the UI thread, reporting progress and result."""

    progress = Signal(str, float)
    succeeded = Signal(Path)
    failed = Signal(str)

    def __init__(self, spec: CoverSpec, parent=None) -> None:
        super().__init__(parent)
        self._spec = spec

    def run(self) -> None:
        try:
            result = generate_cover(self._spec, on_progress=self.progress.emit)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the GUI
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(result)


class SingleImageWorker(QThread):
    """Runs process_single_image() off the UI thread, reporting progress and result."""

    progress = Signal(str, float)
    succeeded = Signal(Path)
    failed = Signal(str)

    def __init__(self, spec: SingleImageSpec, parent=None) -> None:
        super().__init__(parent)
        self._spec = spec

    def run(self) -> None:
        try:
            result = process_single_image(self._spec, on_progress=self.progress.emit)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the GUI
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(result)


class MockupWorker(QThread):
    """Runs generate_mockup() off the UI thread, reporting progress and result."""

    progress = Signal(str, float)
    succeeded = Signal(Path)
    failed = Signal(str)

    def __init__(self, spec: MockupSpec, parent=None) -> None:
        super().__init__(parent)
        self._spec = spec

    def run(self) -> None:
        try:
            result = generate_mockup(self._spec, on_progress=self.progress.emit)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the GUI
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(result)
