"""Background workers for Knowledge Center analysis."""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from backend.service_registry import ServiceRegistry


class KnowledgeAnalysisWorker(QThread):
    """Runs document, screenshot, or project analysis off the UI thread."""

    completed = pyqtSignal(str, object)
    failed = pyqtSignal(str)

    def __init__(self, services: ServiceRegistry, mode: str, path: str) -> None:
        super().__init__()
        self.services = services
        self.mode = mode
        self.path = path

    def run(self) -> None:
        try:
            if self.mode == "document":
                result = self.services.document_intelligence.analyze_document(self.path)
            elif self.mode == "screenshot":
                result = self.services.screen_intelligence.analyze_screenshot(self.path)
            elif self.mode == "project":
                result = self.services.code_intelligence.summarize_project(self.path)
            else:
                raise ValueError(f"Unknown knowledge analysis mode: {self.mode}")
            self.completed.emit(self.mode, result)
        except Exception as exc:
            self.failed.emit(str(exc))
