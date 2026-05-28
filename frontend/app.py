"""PyQt application bootstrap."""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import QApplication

from backend.service_registry import build_services
from config.settings import AppSettings
from frontend.styles.theme import load_stylesheet
from frontend.windows.main_window import MainWindow

logger = logging.getLogger(__name__)


def run_app(settings: AppSettings) -> int:
    """Start the Cherry AI desktop application."""
    app = QApplication([])
    app.setApplicationName(settings.app_name)
    app.setOrganizationName("Cherry AI")
    app.setStyle("Fusion")
    app.setStyleSheet(load_stylesheet("dark_theme"))

    services = build_services(settings)
    window = MainWindow(settings=settings, services=services)
    window.show()

    logger.info("PyQt application window launched")
    return app.exec()
