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
from backend.centralized_event_bus.schemas import (
    EVENT_CATEGORY_AUTOMATION,
    PRIORITY_NORMAL,
    PlatformEvent,
)
from backend.centralized_event_bus.service import CentralizedEventBus
from backend.execution_sandbox.service import ExecutionSandbox

logger = logging.getLogger(__name__)


@dataclass
class AutomationManager:
    """Coordinates permission checks, tool execution, and action history."""

    settings: AppSettings
    tool_registry: ToolRegistry
    permission_manager: PermissionManager
    action_history: ActionHistoryManager
    event_bus: CentralizedEventBus | None = None
    execution_sandbox: ExecutionSandbox | None = None

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

        sandbox_decision = None
        if self.execution_sandbox is not None:
            sandbox_decision = self.execution_sandbox.begin_execution(
                subject="automation",
                action_name=tool.name,
                parameters=parameters,
            )
            if not sandbox_decision.allowed:
                self._publish_event(
                    "automation_blocked",
                    tool.name,
                    success=False,
                    message=sandbox_decision.reason,
                    parameters=parameters,
                )
                return AutomationResult(
                    tool_name=tool.name,
                    success=False,
                    message=sandbox_decision.reason,
                    error_message=sandbox_decision.reason,
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
            if self.execution_sandbox is not None:
                self.execution_sandbox.end_execution("automation", tool.name)
            return AutomationResult(
                tool_name=tool.name,
                success=False,
                message=decision.reason,
                error_message=decision.reason,
                permission_status=decision.status,
                confirmation_required=decision.requires_confirmation,
                action_id=action_id,
            )

        try:
            result = self.tool_registry.execute(tool.name, parameters)
            self.action_history.record_tool_execution(action_id, tool.name, result)
            self.action_history.complete_action(action_id, result)
            logger.info("Automation tool %s completed: %s", tool.name, result.success)
        finally:
            if self.execution_sandbox is not None:
                self.execution_sandbox.end_execution("automation", tool.name)

        automation_result = AutomationResult(
            tool_name=tool.name,
            success=result.success,
            message=result.message,
            data=result.data,
            error_message=result.error_message,
            permission_status=decision.status,
            action_id=action_id,
        )
        self._publish_event(
            "automation_completed",
            tool.name,
            success=automation_result.success,
            message=automation_result.message,
            parameters=parameters,
            action_id=action_id,
        )
        return automation_result

    def _publish_event(
        self,
        event_type: str,
        tool_name: str,
        success: bool,
        message: str,
        parameters: dict[str, object],
        action_id: str = "",
    ) -> None:
        if self.event_bus is None:
            return
        self.event_bus.publish(
            PlatformEvent(
                event_type=event_type,
                source="automation_engine",
                category=EVENT_CATEGORY_AUTOMATION,
                priority=PRIORITY_NORMAL,
                correlation_id=action_id,
                payload={
                    "tool_name": tool_name,
                    "success": success,
                    "message": message,
                    "parameters": parameters,
                    "action_id": action_id,
                },
            )
        )
