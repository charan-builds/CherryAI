"""Automation engine for safe local desktop actions."""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import AppSettings
from backend.automation_engine.action_history_manager.service import (
    ActionHistoryManager,
)
from backend.automation_engine.app_launcher.service import AppLauncher
from backend.automation_engine.automation_manager.service import AutomationManager
from backend.automation_engine.browser_automation.service import BrowserAutomation
from backend.automation_engine.permission_manager.service import PermissionManager
from backend.automation_engine.screenshot_service.service import ScreenshotService
from backend.automation_engine.schemas import AutomationActionRecord, AutomationResult
from backend.automation_engine.tool_registry.service import ToolRegistry


@dataclass
class AutomationEngine:
    """Public facade for structured automation tools."""

    settings: AppSettings
    app_launcher: AppLauncher | None = None
    browser: BrowserAutomation | None = None
    screenshot_service: ScreenshotService | None = None
    action_history: ActionHistoryManager | None = None
    permission_manager: PermissionManager | None = None
    tool_registry: ToolRegistry | None = None
    manager: AutomationManager | None = None

    def __post_init__(self) -> None:
        self.app_launcher = self.app_launcher or AppLauncher(self.settings)
        self.browser = self.browser or BrowserAutomation()
        self.screenshot_service = self.screenshot_service or ScreenshotService(
            self.settings
        )
        self.action_history = self.action_history or ActionHistoryManager(self.settings)
        self.permission_manager = self.permission_manager or PermissionManager()
        self.tool_registry = self.tool_registry or ToolRegistry(
            app_launcher=self.app_launcher,
            browser=self.browser,
            screenshot_service=self.screenshot_service,
        )
        self.manager = self.manager or AutomationManager(
            settings=self.settings,
            tool_registry=self.tool_registry,
            permission_manager=self.permission_manager,
            action_history=self.action_history,
        )

    def configure_pyautogui(self) -> None:
        """Apply project-level PyAutoGUI safety settings."""
        import pyautogui

        pyautogui.FAILSAFE = self.settings.pyautogui_failsafe
        pyautogui.PAUSE = self.settings.pyautogui_pause_seconds

    def execute_tool(
        self,
        tool_name: str,
        parameters: dict[str, object] | None = None,
        confirmed: bool = False,
    ) -> AutomationResult:
        """Execute a structured automation tool safely."""
        return self.manager.execute_tool(tool_name, parameters, confirmed)

    def recent_actions(self, limit: int = 20) -> list[AutomationActionRecord]:
        """Return recent automation actions."""
        return self.action_history.recent_actions(limit=limit)

    def list_tools(self):
        """Return registered automation tools."""
        return self.tool_registry.list_tools()
