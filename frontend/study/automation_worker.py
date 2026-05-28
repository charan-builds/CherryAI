"""Background worker for Study Mode automation actions."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QThread, pyqtSignal

from backend.automation_engine.schemas import AutomationResult
from backend.automation_engine.service import AutomationEngine

logger = logging.getLogger(__name__)


class AutomationWorker(QThread):
    """Runs automation tools away from the UI thread."""

    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        automation_engine: AutomationEngine,
        tool_name: str,
        parameters: dict[str, object],
        confirmed: bool = False,
    ) -> None:
        super().__init__()
        self.automation_engine = automation_engine
        self.tool_name = tool_name
        self.parameters = parameters
        self.confirmed = confirmed

    def run(self) -> None:
        """Execute the automation tool."""
        try:
            result: AutomationResult = self.automation_engine.execute_tool(
                self.tool_name,
                self.parameters,
                confirmed=self.confirmed,
            )
            self.completed.emit(result)
        except Exception as exc:
            logger.exception("Automation worker failed")
            self.failed.emit(str(exc))
