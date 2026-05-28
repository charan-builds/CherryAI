"""Structured automation tool registry."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from backend.automation_engine.app_launcher.service import AppLauncher
from backend.automation_engine.browser_automation.service import BrowserAutomation
from backend.automation_engine.screenshot_service.service import ScreenshotService
from backend.automation_engine.schemas import (
    SAFETY_MEDIUM,
    SAFETY_SAFE,
    AutomationTool,
    ToolExecutionResult,
)

logger = logging.getLogger(__name__)


@dataclass
class ToolRegistry:
    """Registry of structured automation tools."""

    app_launcher: AppLauncher
    browser: BrowserAutomation
    screenshot_service: ScreenshotService
    tools: dict[str, AutomationTool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._register_defaults()

    def register(self, tool: AutomationTool) -> None:
        """Register a tool definition."""
        self.tools[tool.name] = tool

    def get(self, tool_name: str) -> AutomationTool | None:
        """Return a tool by name."""
        return self.tools.get(tool_name)

    def list_tools(self) -> list[AutomationTool]:
        """Return registered tools."""
        return list(self.tools.values())

    def execute(self, tool_name: str, parameters: dict[str, object]) -> ToolExecutionResult:
        """Execute a registered tool handler."""
        tool = self.get(tool_name)
        if tool is None:
            return ToolExecutionResult(
                success=False,
                message=f"Unknown automation tool: {tool_name}.",
                error_message="Unknown tool.",
            )

        logger.info("Executing automation tool: %s", tool_name)
        return tool.handler(parameters)

    def _register_defaults(self) -> None:
        self.register(
            AutomationTool(
                name="open_app",
                description="Open a configured local application.",
                input_schema={
                    "type": "object",
                    "required": ["app_name"],
                    "properties": {"app_name": {"type": "string"}},
                },
                safety_level=SAFETY_SAFE,
                handler=self._open_app,
            )
        )
        self.register(
            AutomationTool(
                name="open_website",
                description="Open a website in the default browser.",
                input_schema={
                    "type": "object",
                    "required": ["url"],
                    "properties": {"url": {"type": "string"}},
                },
                safety_level=SAFETY_SAFE,
                handler=self._open_website,
            )
        )
        self.register(
            AutomationTool(
                name="play_music",
                description="Open a YouTube music search or playlist.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "playlist_url": {"type": "string"},
                    },
                },
                safety_level=SAFETY_SAFE,
                handler=self._play_music,
            )
        )
        self.register(
            AutomationTool(
                name="take_screenshot",
                description="Capture the full screen and save it locally.",
                input_schema={"type": "object", "properties": {}},
                safety_level=SAFETY_MEDIUM,
                handler=self._take_screenshot,
            )
        )
        self.register(
            AutomationTool(
                name="open_study_workspace",
                description="Open a study workspace with tools and resources.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "app_name": {"type": "string"},
                    },
                },
                safety_level=SAFETY_MEDIUM,
                handler=self._open_study_workspace,
            )
        )

    def _open_app(self, parameters: dict[str, object]) -> ToolExecutionResult:
        return self.app_launcher.launch(str(parameters.get("app_name", "")))

    def _open_website(self, parameters: dict[str, object]) -> ToolExecutionResult:
        return self.browser.open_url(str(parameters.get("url", "")))

    def _play_music(self, parameters: dict[str, object]) -> ToolExecutionResult:
        playlist_url = str(parameters.get("playlist_url", "")).strip()
        query = str(parameters.get("query", "")).strip()
        if playlist_url:
            return self.browser.open_playlist(playlist_url)
        return self.browser.open_youtube_search(query or "focus music")

    def _take_screenshot(self, parameters: dict[str, object]) -> ToolExecutionResult:
        return self.screenshot_service.capture_full_screen()

    def _open_study_workspace(self, parameters: dict[str, object]) -> ToolExecutionResult:
        topic = str(parameters.get("topic", "study")).strip() or "study"
        app_name = str(parameters.get("app_name", "vscode")).strip() or "vscode"
        app_result = self.app_launcher.launch(app_name)
        resource_result = self.browser.open_study_resources(topic)
        success = app_result.success and resource_result.success
        errors = " ".join(
            item.error_message
            for item in (app_result, resource_result)
            if item.error_message
        )
        return ToolExecutionResult(
            success=success,
            message=f"Study workspace opened for {topic}."
            if success
            else "I could not open the full study workspace.",
            data={
                "topic": topic,
                "app": app_result.data,
                "resources": resource_result.data,
            },
            error_message=errors,
        )
