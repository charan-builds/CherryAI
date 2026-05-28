"""Safe automation manager."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config.settings import AppSettings
from backend.automation_engine.action_history_manager.service import (
    ActionHistoryManager,
)
from backend.automation_engine.permission_manager.service import PermissionManager
from backend.automation_engine.schemas import (
    PERMISSION_BLOCKED,
    AutomationResult,
    ToolExecutionResult,
)
from backend.automation_engine.tool_registry.service import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class AutomationManager:
    """Coordinates permission checks, tool execution, and action history."""

    settings: AppSettings
    tool_registry: ToolRegistry
    permission_manager: PermissionManager
    action_history: ActionHistoryManager

    def execute_tool(
        self,
        tool_name: str,
        parameters: dict[str, object] | None = None,
        confirmed: bool = False,
    ) -> AutomationResult:
        """Run a tool through the safety and history pipeline."""
        parameters = parameters or {}
        if not self.settings.automation_enabled:
            return AutomationResult(
                tool_name=tool_name,
                success=False,
                message="Automation is disabled in settings.",
                permission_status=PERMISSION_BLOCKED,
            )

        tool = self.tool_registry.get(tool_name)
        if tool is None:
            return AutomationResult(
                tool_name=tool_name,
                success=False,
                message=f"Unknown automation tool: {tool_name}.",
                error_message="Unknown tool.",
                permission_status=PERMISSION_BLOCKED,
            )

        decision = self.permission_manager.evaluate(
            tool=tool,
            parameters=parameters,
            confirmed=confirmed,
        )
        self.action_history.record_permission_decision(
            tool_name=tool.name,
            safety_level=tool.safety_level,
            decision=decision.status,
            reason=decision.reason,
        )
        action_id = self.action_history.start_action(
            tool_name=tool.name,
            parameters=parameters,
            safety_level=tool.safety_level,
            permission_status=decision.status,
        )

        if not decision.allowed:
            result = ToolExecutionResult(
                success=False,
                message=decision.reason,
                error_message=decision.reason,
            )
            self.action_history.complete_action(action_id, result)
            return AutomationResult(
                tool_name=tool.name,
                success=False,
                message=decision.reason,
                error_message=decision.reason,
                permission_status=decision.status,
                confirmation_required=decision.requires_confirmation,
                action_id=action_id,
            )

        result = self.tool_registry.execute(tool.name, parameters)
        self.action_history.record_tool_execution(action_id, tool.name, result)
        self.action_history.complete_action(action_id, result)
        logger.info("Automation tool %s completed: %s", tool.name, result.success)

        return AutomationResult(
            tool_name=tool.name,
            success=result.success,
            message=result.message,
            data=result.data,
            error_message=result.error_message,
            permission_status=decision.status,
            action_id=action_id,
        )
