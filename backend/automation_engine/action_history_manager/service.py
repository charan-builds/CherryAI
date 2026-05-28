"""Action history manager."""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import AppSettings
from database.models import utc_now
from backend.automation_engine.action_history_manager.repository import (
    ActionHistoryRepository,
)
from backend.automation_engine.schemas import AutomationActionRecord, ToolExecutionResult


@dataclass
class ActionHistoryManager:
    """Records automation actions and permission decisions."""

    settings: AppSettings
    repository: ActionHistoryRepository | None = None

    def __post_init__(self) -> None:
        if self.repository is None:
            self.repository = ActionHistoryRepository.from_settings(self.settings)

    def start_action(
        self,
        tool_name: str,
        parameters: dict[str, object],
        safety_level: str,
        permission_status: str,
    ) -> str:
        """Create an action history row."""
        return self.repository.start_action(
            tool_name=tool_name,
            parameters=parameters,
            safety_level=safety_level,
            permission_status=permission_status,
            started_at=utc_now(),
        )

    def complete_action(self, action_id: str, result: ToolExecutionResult) -> None:
        """Complete an action history row."""
        self.repository.complete_action(
            action_id=action_id,
            success=result.success,
            message=result.message,
            error_message=result.error_message,
            completed_at=utc_now(),
        )

    def record_tool_execution(
        self,
        action_id: str,
        tool_name: str,
        result: ToolExecutionResult,
    ) -> None:
        """Persist tool result details."""
        self.repository.record_tool_execution(
            action_id=action_id,
            tool_name=tool_name,
            result={
                "success": result.success,
                "message": result.message,
                "data": result.data,
                "error_message": result.error_message,
            },
            created_at=utc_now(),
        )

    def record_permission_decision(
        self,
        tool_name: str,
        safety_level: str,
        decision: str,
        reason: str,
    ) -> None:
        """Persist a permission decision."""
        self.repository.record_permission_decision(
            tool_name=tool_name,
            safety_level=safety_level,
            decision=decision,
            reason=reason,
            created_at=utc_now(),
        )

    def recent_actions(self, limit: int = 20) -> list[AutomationActionRecord]:
        """Return recent actions."""
        return self.repository.list_recent(limit=limit)
