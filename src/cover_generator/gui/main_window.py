"""The application's main window: a tabbed shell around the cover tools."""

from __future__ import annotations

from importlib import resources
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from cover_generator.core.icc_profiles import KNOWN_CMYK_PROFILES
from cover_generator.gui.widgets.cover_builder import CoverBuilderWidget
from cover_generator.gui.widgets.cover_mockup import CoverMockupWidget
from cover_generator.gui.widgets.single_image import SingleImageWidget


def _app_version() -> str:
    try:
        return version("tvorec-cover")
    except PackageNotFoundError:
        return "1.0.0"


def _asset_path(filename: str) -> Path:
    """Path to a bundled file under ``cover_generator/resources/assets``."""
    return Path(str(resources.files("cover_generator") / "resources" / "assets" / filename))


def _manual_path(language: str) -> Path:
    """Path to the bundled usage manual for ``language``, falling back to English."""
    docs_dir = resources.files("cover_generator") / "resources" / "docs"
    candidate = Path(str(docs_dir / language / "usage-manual.md"))
    if candidate.exists():
        return candidate
    return Path(str(docs_dir / "en" / "usage-manual.md"))


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Tvorec Cover"))
        self.setMinimumSize(960, 640)

        self._build_menu()

        self.cover_tab = CoverBuilderWidget()
        self.single_image_tab = SingleImageWidget()
        self.mockup_tab = CoverMockupWidget()

        tabs = QTabWidget()
        tabs.addTab(self.cover_tab, self.tr("Cover builder"))
        tabs.addTab(self.single_image_tab, self.tr("Single image"))
        tabs.addTab(self.mockup_tab, self.tr("Cover mockup"))
        self.setCentralWidget(tabs)

    # -- menu -------------------------------------------------------------

    def _build_menu(self) -> None:
        from cover_generator.app import SUPPORTED_LANGUAGES

        language_menu = self.menuBar().addMenu(self.tr("Language"))
        language_labels = {"en": self.tr("English"), "bg": self.tr("Bulgarian")}
        for code in SUPPORTED_LANGUAGES:
            action = language_menu.addAction(language_labels[code])
            action.triggered.connect(lambda _checked=False, c=code: self._on_language_selected(c))

        help_menu = self.menuBar().addMenu(self.tr("Help"))
        manual_action = help_menu.addAction(self.tr("User manual"))
        manual_action.triggered.connect(self._show_manual)

        about_menu = self.menuBar().addMenu(self.tr("About"))
        about_action = about_menu.addAction(self.tr("About Tvorec Cover"))
        about_action.triggered.connect(self._show_about)
        icc_action = about_menu.addAction(self.tr("ICC profiles && credits"))
        icc_action.triggered.connect(self._show_icc_credits)

    # -- Help / manual -----------------------------------------------------

    def _show_manual(self) -> None:
        from cover_generator.app import preferred_language

        manual_path = _manual_path(preferred_language())
        try:
            markdown_text = manual_path.read_text(encoding="utf-8")
        except OSError:
            markdown_text = self.tr("The user manual could not be loaded.")

        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("User manual"))
        dialog.resize(720, 640)
        browser = QTextBrowser(dialog)
        browser.setOpenExternalLinks(True)
        browser.setMarkdown(markdown_text)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, dialog)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout = QVBoxLayout(dialog)
        layout.addWidget(browser)
        layout.addWidget(buttons)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.exec()

    # -- About -----------------------------------------------------------

    def _show_about(self) -> None:
        intro = self.tr("This is Tvorec Cover v{version}").format(version=_app_version())
        explanation = self.tr(
            "Tvorec Cover builds print-ready, wrap-around book covers (back, "
            "spine and front) from your images, and prepares single cover "
            "images for print services that take the front and back as "
            "separate uploads. It handles spine-width math, bleed, DPI, image "
            "upscaling, and RGB or CMYK output."
        )
        created_by = self.tr("Created by Stoyan Bonchev")

        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("About Tvorec Cover"))
        dialog.resize(440, 380)

        logo_label = QLabel(dialog)
        logo_path = _asset_path("logo.png")
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            if not pixmap.isNull():
                logo_label.setPixmap(
                    pixmap.scaledToWidth(96, Qt.TransformationMode.SmoothTransformation)
                )
        logo_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        text_label = QLabel(dialog)
        text_label.setTextFormat(Qt.TextFormat.RichText)
        text_label.setOpenExternalLinks(True)
        text_label.setWordWrap(True)
        text_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        text_label.setText(
            f"<h3>Tvorec Cover</h3>"
            f"<p>{intro}</p>"
            f"<p>{explanation}</p>"
            f"<p>{created_by}<br>"
            f"<a href='https://tvorec.org'>https://tvorec.org</a></p>"
        )

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, dialog)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)

        layout = QVBoxLayout(dialog)
        layout.addWidget(logo_label)
        layout.addWidget(text_label)
        layout.addWidget(buttons)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.exec()

    def _show_icc_credits(self) -> None:
        intro = self.tr(
            "For CMYK output, the app converts colors using an ICC profile so "
            "they print predictably. It ships with the freely distributed ECI "
            "profile packs, so the common European offset profiles work with "
            "no download. The default, ISO Coated v2, is the FOGRA39 "
            "characterization (the target Adobe calls \"Coated FOGRA39\") and "
            "is the usual choice for book covers on coated stock."
        )
        credits = self.tr(
            "Bundled ICC profiles are provided free of charge by the European "
            "Color Initiative (ECI) -- the ECI Offset 2009 and eciCMYK v2 "
            "packs from eci.org. All rights remain with their authors; they "
            "are redistributed here unmodified for convenience."
        )
        override = self.tr(
            "You can also choose \"Custom...\" in the CMYK profile dropdown to "
            "use any .icc/.icm file (for example a US GRACoL or SWOP profile, "
            "or one your print house supplies)."
        )
        heading = self.tr("CMYK ICC profiles")
        credits_label = self.tr("Credits")
        bundled_title = self.tr("Bundled profiles:")
        profile_items = "".join(f"<li>{label}</li>" for label in KNOWN_CMYK_PROFILES)
        html = (
            f"<h3>{heading}</h3>"
            f"<p>{intro}</p>"
            f"<p><b>{credits_label}</b><br>{credits} "
            f"<a href='https://www.eci.org'>www.eci.org</a></p>"
            f"<p>{override}</p>"
            f"<p><b>{bundled_title}</b></p><ul>{profile_items}</ul>"
        )

        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("ICC profiles & credits"))
        dialog.resize(560, 460)
        browser = QTextBrowser(dialog)
        browser.setOpenExternalLinks(True)
        browser.setHtml(html)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, dialog)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout = QVBoxLayout(dialog)
        layout.addWidget(browser)
        layout.addWidget(buttons)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.exec()

    def _on_language_selected(self, language: str) -> None:
        from cover_generator.app import save_preferred_language

        save_preferred_language(language)
        QMessageBox.information(
            self,
            self.tr("Language changed"),
            self.tr("Restart the application for the new language to take effect."),
        )
