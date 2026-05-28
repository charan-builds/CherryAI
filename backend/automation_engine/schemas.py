"""Automation engine schemas."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime


SAFETY_SAFE = "safe"
SAFETY_MEDIUM = "medium"
SAFETY_HIGH = "high"

PERMISSION_ALLOWED = "allowed"
PERMISSION_CONFIRMATION_REQUIRED = "confirmation_required"
PERMISSION_BLOCKED = "blocked"


@dataclass(frozen=True)
class PermissionDecision:
    """Decision returned by the permission manager."""

    status: str
    reason: str

    @property
    def allowed(self) -> bool:
        return self.status == PERMISSION_ALLOWED

    @property
    def requires_confirmation(self) -> bool:
        return self.status == PERMISSION_CONFIRMATION_REQUIRED


@dataclass(frozen=True)
class ToolExecutionResult:
    """Result returned by one automation tool handler."""

    success: bool
    message: str
    data: dict[str, object] = field(default_factory=dict)
    error_message: str = ""


AutomationToolHandler = Callable[[dict[str, object]], ToolExecutionResult]


@dataclass(frozen=True)
class AutomationTool:
    """Registered automation tool definition."""

    name: str
    description: str
    input_schema: dict[str, object]
    safety_level: str
    handler: AutomationToolHandler


@dataclass(frozen=True)
class AutomationResult:
    """Final result of an automation request."""

    tool_name: str
    success: bool
    message: str
    data: dict[str, object] = field(default_factory=dict)
    error_message: str = ""
    permission_status: str = PERMISSION_ALLOWED
    confirmation_required: bool = False
    action_id: str = ""


@dataclass(frozen=True)
class AutomationActionRecord:
    """Persisted automation action DTO."""

    id: str
    tool_name: str
    parameters: dict[str, object]
    safety_level: str
    permission_status: str
    success: bool
    message: str
    error_message: str
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: float
