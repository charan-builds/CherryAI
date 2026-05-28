"""Screenshot capture service."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from config.settings import AppSettings
from database.models import utc_now
from backend.automation_engine.schemas import ToolExecutionResult

logger = logging.getLogger(__name__)
ScreenshotCaptureFn = Callable[[], object]


@dataclass
class ScreenshotService:
    """Captures and saves full-screen screenshots."""

    settings: AppSettings
    capture_fn: ScreenshotCaptureFn | None = None

    def capture_full_screen(self) -> ToolExecutionResult:
        """Capture a timestamped screenshot."""
        self.settings.screenshot_dir.mkdir(parents=True, exist_ok=True)
        timestamp = utc_now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = self.settings.screenshot_dir / f"screenshot_{timestamp}.png"

        try:
            image = self._capture()
            image.save(screenshot_path)
            logger.info("Screenshot saved: %s", screenshot_path)
            return ToolExecutionResult(
                success=True,
                message=f"Screenshot saved to {screenshot_path}.",
                data={"path": str(screenshot_path)},
            )
        except Exception as exc:
            logger.exception("Screenshot capture failed")
            return ToolExecutionResult(
                success=False,
                message="I could not take a screenshot.",
                error_message=str(exc),
            )

    def _capture(self) -> object:
        if self.capture_fn is not None:
            return self.capture_fn()

        import pyautogui

        return pyautogui.screenshot()
