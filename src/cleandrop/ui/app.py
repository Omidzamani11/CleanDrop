from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QLocale, QSettings
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from cleandrop.ui.main_window import MainWindow
from cleandrop.ui.styles import STYLESHEET


def _resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[3]


def run() -> int:
    existing = QApplication.instance()
    application = existing if isinstance(existing, QApplication) else QApplication(sys.argv)
    application.setApplicationName("CleanDrop")
    application.setOrganizationName("CleanDrop")
    application.setStyle("Fusion")
    application.setStyleSheet(STYLESHEET)
    settings = QSettings()
    saved_language = str(settings.value("language", ""))
    system_language = QLocale.system().language()
    language = saved_language or ("fa" if system_language is QLocale.Language.Persian else "en")
    window = MainWindow(language)
    window.drop_page.language_changed.connect(
        lambda selected: settings.setValue("language", selected)
    )
    icon_path = _resource_root() / "src" / "cleandrop" / "resources" / "cleandrop-icon.ico"
    if icon_path.exists():
        application.setWindowIcon(QIcon(str(icon_path)))
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    return application.exec()
