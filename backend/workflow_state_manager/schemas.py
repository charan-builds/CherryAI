"""Shared workflow data transfer objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from database.models import utc_now

WORKFLOW_STATUS_PLANNED = "planned"
WORKFLOW_STATUS_RUNNING = "running"
WORKFLOW_STATUS_PAUSED = "paused"
WORKFLOW_STATUS_COMPLETED = "completed"
WORKFLOW_STATUS_FAILED = "failed"
WORKFLOW_STATUS_CANCELLED = "cancelled"
WORKFLOW_STATUS_SCHEDULED = "scheduled"

STEP_STATUS_PENDING = "pending"
STEP_STATUS_RUNNING = "running"
STEP_STATUS_COMPLETED = "completed"
STEP_STATUS_FAILED = "failed"
STEP_STATUS_SKIPPED = "skipped"
STEP_STATUS_CANCELLED = "cancelled"

ACTION_TYPE_AUTOMATION = "automation_tool"
ACTION_TYPE_STUDY_SESSION = "study_session"
ACTION_TYPE_NOTIFICATION = "notification"
ACTION_TYPE_NOOP = "noop"

CONDITION_ALWAYS = "always"
CONDITION_PREVIOUS_SUCCESS = "previous_success"
CONDITION_PREVIOUS_FAILURE = "previous_failure"
CONDITION_CONTEXT_EQUALS = "context_equals"

TERMINAL_WORKFLOW_STATUSES = {
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_FAILED,
    WORKFLOW_STATUS_CANCELLED,
}


@dataclass(frozen=True)
class WorkflowStepPlan:
    """One deterministic step in a workflow plan."""

    key: str
    name: str
    action_type: str
    action_name: str = ""
    parameters: dict[str, object] = field(default_factory=dict)
    depends_on: tuple[str, ...] = field(default_factory=tuple)
    condition_kind: str = CONDITION_ALWAYS
    condition_data: dict[str, object] = field(default_factory=dict)
    retries: int = 0
    timeout_seconds: float | None = None
    continue_on_failure: bool = False
    position: int = 0
    agent_id: str = "local"


@dataclass(frozen=True)
class WorkflowPlan:
    """Structured workflow plan produced before execution."""

    goal: str
    name: str
    steps: tuple[WorkflowStepPlan, ...]
    id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    source: str = "heuristic"
    metadata: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)

    @property
    def step_count(self) -> int:
        """Return the number of steps in the plan."""
        return len(self.steps)


@dataclass(frozen=True)
class WorkflowStepRecord:
    """Persisted step state returned to services and UI."""

    workflow_id: str
    key: str
    name: str
    action_type: str
    action_name: str
    parameters: dict[str, object]
    depends_on: tuple[str, ...]
    condition_kind: str
    condition_data: dict[str, object]
    status: str
    position: int
    attempts: int
    max_retries: int
    timeout_seconds: float
    continue_on_failure: bool
    error_message: str
    started_at: datetime | None
    completed_at: datetime | None


@dataclass(frozen=True)
class WorkflowRecord:
    """Persisted workflow state returned to services and UI."""

    id: str
    name: str
    goal: str
    status: str
    source: str
    metadata: dict[str, object]
    current_step_key: str
    progress_percent: float
    failure_reason: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


@dataclass(frozen=True)
class WorkflowSnapshot:
    """Workflow state plus ordered steps for display."""

    workflow: WorkflowRecord
    steps: tuple[WorkflowStepRecord, ...]


@dataclass(frozen=True)
class StepExecutionResult:
    """Runtime result for one workflow step."""

    step_key: str
    success: bool
    status: str
    message: str
    attempts: int = 1
    data: dict[str, object] = field(default_factory=dict)
    error_message: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True)
class WorkflowExecutionResult:
    """Runtime result for a full workflow execution."""

    workflow_id: str
    success: bool
    status: str
    message: str
    step_results: tuple[StepExecutionResult, ...]
    reflection_summary: str = ""


@dataclass(frozen=True)
class WorkflowEvent:
    """Event published whenever workflow state changes."""

    workflow_id: str
    event_type: str
    message: str
    step_key: str = ""
    payload: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
