from PIL import Image

from cover_generator.gui.main_window import MainWindow
from cover_generator.gui.widgets import cover_builder as cover_builder_module
from cover_generator.gui.widgets import cover_mockup as cover_mockup_module
from cover_generator.gui.widgets import single_image as single_image_module


def test_main_window_opens(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.windowTitle() == "Tvorec Cover"


def test_generate_produces_pdf(qtbot, tmp_path, monkeypatch):
    # Generation success pops a modal QMessageBox; stub it out so the
    # headless test doesn't block waiting for a user to click OK.
    monkeypatch.setattr(cover_builder_module.QMessageBox, "information", lambda *a, **k: None)

    window = MainWindow()
    qtbot.addWidget(window)
    tab = window.cover_tab

    front_path = tmp_path / "front.png"
    back_path = tmp_path / "back.png"
    Image.new("RGB", (400, 600), "red").save(front_path)
    Image.new("RGB", (400, 600), "blue").save(back_path)

    tab.front_picker.set_path(front_path)
    tab.back_picker.set_path(back_path)
    tab.parameters_form.dpi_spin.setValue(96)

    output_path = tmp_path / "cover.pdf"
    tab.parameters_form.output_edit.setText(str(output_path))

    tab._on_generate_clicked()
    qtbot.waitUntil(lambda: output_path.exists(), timeout=15000)
    # The success signal is delivered asynchronously (cross-thread queued
    # connection); wait for the slot to actually run (it re-enables the
    # button) so the monkeypatched QMessageBox is still in place when it
    # fires, instead of leaking into -- and crashing -- a later test.
    qtbot.waitUntil(lambda: tab.generate_button.isEnabled(), timeout=15000)


def test_single_image_tab_produces_jpg(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(single_image_module.QMessageBox, "information", lambda *a, **k: None)

    window = MainWindow()
    qtbot.addWidget(window)
    tab = window.single_image_tab

    input_path = tmp_path / "art.png"
    Image.new("RGB", (400, 600), "green").save(input_path)

    tab.picker.set_path(input_path)
    tab.dpi_spin.setValue(96)

    output_path = tmp_path / "front.jpg"
    tab.output_edit.setText(str(output_path))

    tab._on_generate_clicked()
    qtbot.waitUntil(lambda: output_path.exists(), timeout=15000)
    qtbot.waitUntil(lambda: tab.generate_button.isEnabled(), timeout=15000)


def test_single_image_tab_spine_mode_produces_spine_sized_jpg(qtbot, tmp_path, monkeypatch):
    from cover_generator.core.geometry import compute_spine_panel_size
    from cover_generator.core.models import PaperType

    monkeypatch.setattr(single_image_module.QMessageBox, "information", lambda *a, **k: None)

    window = MainWindow()
    qtbot.addWidget(window)
    tab = window.single_image_tab

    input_path = tmp_path / "spine_art.png"
    Image.new("RGB", (300, 1800), "gray").save(input_path)
    tab.picker.set_path(input_path)
    tab.dpi_spin.setValue(96)
    tab.spine_mode_checkbox.setChecked(True)
    tab.pages_spin.setValue(220)

    output_path = tmp_path / "spine.jpg"
    tab.output_edit.setText(str(output_path))

    tab._on_generate_clicked()
    qtbot.waitUntil(lambda: output_path.exists(), timeout=15000)
    qtbot.waitUntil(lambda: tab.generate_button.isEnabled(), timeout=15000)

    with Image.open(output_path) as out:
        assert out.size == compute_spine_panel_size(tab.trim_size, 3.0, 96, 220, PaperType.CREAM)


def test_mockup_tab_produces_png(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(cover_mockup_module.QMessageBox, "information", lambda *a, **k: None)

    window = MainWindow()
    qtbot.addWidget(window)
    tab = window.mockup_tab

    tab.dpi_spin.setValue(96)

    output_path = tmp_path / "mockup.png"
    tab.output_edit.setText(str(output_path))

    tab._on_generate_clicked()
    qtbot.waitUntil(lambda: output_path.exists(), timeout=15000)
    qtbot.waitUntil(lambda: tab.generate_button.isEnabled(), timeout=15000)
