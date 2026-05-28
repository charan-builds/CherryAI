"""Background worker for dashboard chat requests."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QThread, pyqtSignal

from backend.ai_engine.service import AIEngine
from backend.ai_response_handler.schemas import AIWorkflowResult

logger = logging.getLogger(__name__)


class ChatWorker(QThread):
    """Runs the AI workflow away from the UI thread."""

    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        ai_engine: AIEngine,
        user_message: str,
        session_id: str,
    ) -> None:
        super().__init__()
        self.ai_engine = ai_engine
        self.user_message = user_message
        self.session_id = session_id

    def run(self) -> None:
        """Execute the AI workflow."""
        try:
            result: AIWorkflowResult = self.ai_engine.handle_message(
                user_message=self.user_message,
                session_id=self.session_id,
            )
            self.completed.emit(result)
        except Exception as exc:
            logger.exception("Chat worker failed")
            self.failed.emit(str(exc))
