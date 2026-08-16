"""QApplication bootstrap: theming, translations, and the main window."""

from __future__ import annotations

import sys
from importlib import resources

from PySide6.QtCore import QLocale, QSettings, QTranslator
from PySide6.QtWidgets import QApplication

from cover_generator.gui.main_window import MainWindow

ORG_NAME = "CoverGenerator"
APP_NAME = "CoverGenerator"
SETTINGS_LANGUAGE_KEY = "language"
SUPPORTED_LANGUAGES = ("en", "bg")


def _settings() -> QSettings:
    return QSettings(ORG_NAME, APP_NAME)


def preferred_language() -> str:
    """Return the saved language, or fall back to the system locale, or 'en'."""
    saved = _settings().value(SETTINGS_LANGUAGE_KEY, type=str)
    if saved in SUPPORTED_LANGUAGES:
        return saved
    system_lang = QLocale.system().name().split("_")[0]
    return system_lang if system_lang in SUPPORTED_LANGUAGES else "en"


def save_preferred_language(language: str) -> None:
    _settings().setValue(SETTINGS_LANGUAGE_KEY, language)


def load_translator(app: QApplication, language: str) -> QTranslator | None:
    """Load and install the .qm translation file for the given language code."""
    translator = QTranslator(app)
    try:
        qm_path = resources.files("cover_generator.i18n") / f"cover_generator_{language}.qm"
        loaded = translator.load(str(qm_path))
    except (FileNotFoundError, ModuleNotFoundError):
        loaded = False

    if loaded:
        app.installTranslator(translator)
        return translator
    return None


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    try:
        qss_path = resources.files("cover_generator.gui") / "theme.qss"
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ModuleNotFoundError):
        pass


def main() -> None:
    app = QApplication(sys.argv)
    apply_theme(app)
    load_translator(app, preferred_language())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
