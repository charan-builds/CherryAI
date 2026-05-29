"""Workflow state manager service."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config.settings import AppSettings
from backend.centralized_event_bus.schemas import (
    EVENT_CATEGORY_WORKFLOW,
    PRIORITY_NORMAL,
    PlatformEvent,
)
from backend.centralized_event_bus.service import CentralizedEventBus
from database.models import utc_now
from backend.workflow_state_manager.event_bus import WorkflowEventBus
from backend.workflow_state_manager.repository import WorkflowRepository
from backend.workflow_state_manager.schemas import (
    STEP_STATUS_CANCELLED,
    STEP_STATUS_COMPLETED,
    STEP_STATUS_FAILED,
    STEP_STATUS_RUNNING,
    STEP_STATUS_SKIPPED,
    WORKFLOW_STATUS_CANCELLED,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_FAILED,
    WORKFLOW_STATUS_PAUSED,
    WORKFLOW_STATUS_PLANNED,
    WORKFLOW_STATUS_RUNNING,
    WorkflowEvent,
    WorkflowPlan,
    WorkflowRecord,
    WorkflowSnapshot,
    WorkflowStepRecord,
)

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStateManager:
    """Tracks and persists workflow runtime state."""

    settings: AppSettings
    repository: WorkflowRepository | None = None
    event_bus: WorkflowEventBus | None = None
    platform_event_bus: CentralizedEventBus | None = None

    def __post_init__(self) -> None:
        self.repository = self.repository or WorkflowRepository.from_settings(
            self.settings
        )
        self.event_bus = self.event_bus or WorkflowEventBus()

    def create_workflow(self, plan: WorkflowPlan) -> WorkflowRecord:
        """Persist a new planned workflow."""
        workflow = self.repository.create_workflow(plan)
        self.log_event(
            workflow.id,
            "workflow_planned",
            f"Workflow planned: {workflow.name}",
            payload={"goal": workflow.goal, "step_count": plan.step_count},
        )
        return workflow

    def start_workflow(self, workflow_id: str) -> WorkflowRecord:
        """Mark a workflow as running."""
        workflow = self.repository.update_workflow(
            workflow_id,
            status=WORKFLOW_STATUS_RUNNING,
            started_at=utc_now(),
            progress_percent=0.0,
        )
        self.log_event(workflow_id, "workflow_started", "Workflow execution started.")
        return workflow

    def pause_workflow(self, workflow_id: str) -> WorkflowRecord:
        """Mark a workflow as paused."""
        workflow = self.repository.update_workflow(
            workflow_id,
            status=WORKFLOW_STATUS_PAUSED,
        )
        self.log_event(workflow_id, "workflow_paused", "Workflow paused.")
        return workflow

    def resume_workflow(self, workflow_id: str) -> WorkflowRecord:
        """Mark a paused workflow as running."""
        workflow = self.repository.update_workflow(
            workflow_id,
            status=WORKFLOW_STATUS_RUNNING,
        )
        self.log_event(workflow_id, "workflow_resumed", "Workflow resumed.")
        return workflow

    def cancel_workflow(self, workflow_id: str, reason: str = "Cancelled.") -> None:
        """Mark a workflow and remaining active steps as cancelled."""
        self.repository.update_workflow(
            workflow_id,
            status=WORKFLOW_STATUS_CANCELLED,
            failure_reason=reason,
            completed_at=utc_now(),
        )
        self.log_event(workflow_id, "workflow_cancelled", reason)

    def complete_workflow(self, workflow_id: str) -> WorkflowRecord:
        """Mark a workflow as completed."""
        workflow = self.repository.update_workflow(
            workflow_id,
            status=WORKFLOW_STATUS_COMPLETED,
            current_step_key="",
            progress_percent=100.0,
            completed_at=utc_now(),
        )
        self.log_event(workflow_id, "workflow_completed", "Workflow completed.")
        return workflow

    def fail_workflow(self, workflow_id: str, reason: str) -> WorkflowRecord:
        """Mark a workflow as failed."""
        workflow = self.repository.update_workflow(
            workflow_id,
            status=WORKFLOW_STATUS_FAILED,
            failure_reason=reason,
            completed_at=utc_now(),
        )
        self.log_event(workflow_id, "workflow_failed", reason)
        return workflow

    def mark_step_running(
        self,
        workflow_id: str,
        step_key: str,
        progress_percent: float,
        attempts: int,
    ) -> WorkflowStepRecord:
        """Mark one step as running."""
        now = utc_now()
        self.repository.update_workflow(
            workflow_id,
            status=WORKFLOW_STATUS_RUNNING,
            current_step_key=step_key,
            progress_percent=progress_percent,
        )
        step = self.repository.update_step(
            workflow_id,
            step_key,
            status=STEP_STATUS_RUNNING,
            attempts=attempts,
            started_at=now,
        )
        self.log_event(
            workflow_id,
            "step_started",
            f"Started step: {step.name}",
            step_key=step_key,
            payload={"attempts": attempts},
        )
        return step

    def mark_step_completed(
        self,
        workflow_id: str,
        step_key: str,
        progress_percent: float,
        attempts: int,
        message: str = "",
    ) -> WorkflowStepRecord:
        """Mark one step as completed."""
        step = self.repository.update_step(
            workflow_id,
            step_key,
            status=STEP_STATUS_COMPLETED,
            attempts=attempts,
            completed_at=utc_now(),
        )
        self.repository.update_workflow(
            workflow_id,
            progress_percent=progress_percent,
        )
        self.log_event(
            workflow_id,
            "step_completed",
            message or f"Completed step: {step.name}",
            step_key=step_key,
        )
        return step

    def mark_step_failed(
        self,
        workflow_id: str,
        step_key: str,
        attempts: int,
        error_message: str,
    ) -> WorkflowStepRecord:
        """Mark one step as failed."""
        step = self.repository.update_step(
            workflow_id,
            step_key,
            status=STEP_STATUS_FAILED,
            attempts=attempts,
            error_message=error_message,
            completed_at=utc_now(),
        )
        self.log_event(
            workflow_id,
            "step_failed",
            error_message,
            step_key=step_key,
            payload={"attempts": attempts},
        )
        return step

    def mark_step_skipped(
        self,
        workflow_id: str,
        step_key: str,
        progress_percent: float,
        reason: str,
    ) -> WorkflowStepRecord:
        """Mark one step as skipped."""
        step = self.repository.update_step(
            workflow_id,
            step_key,
            status=STEP_STATUS_SKIPPED,
            error_message=reason,
            completed_at=utc_now(),
        )
        self.repository.update_workflow(workflow_id, progress_percent=progress_percent)
        self.log_event(workflow_id, "step_skipped", reason, step_key=step_key)
        return step

    def mark_step_cancelled(
        self,
        workflow_id: str,
        step_key: str,
        reason: str,
    ) -> WorkflowStepRecord:
        """Mark one step as cancelled."""
        step = self.repository.update_step(
            workflow_id,
            step_key,
            status=STEP_STATUS_CANCELLED,
            error_message=reason,
            completed_at=utc_now(),
        )
        self.log_event(workflow_id, "step_cancelled", reason, step_key=step_key)
        return step

    def snapshot(self, workflow_id: str) -> WorkflowSnapshot:
        """Return workflow state plus ordered steps."""
        return WorkflowSnapshot(
            workflow=self.repository.get_workflow(workflow_id),
            steps=self.repository.get_snapshot_steps(workflow_id),
        )

    def list_active_workflows(self, limit: int = 10) -> list[WorkflowRecord]:
        """Return workflows that are currently active or paused."""
        return self.repository.list_workflows(
            statuses=(
                WORKFLOW_STATUS_PLANNED,
                WORKFLOW_STATUS_RUNNING,
                WORKFLOW_STATUS_PAUSED,
            ),
            limit=limit,
        )

    def list_history(self, limit: int = 20) -> list[dict[str, object]]:
        """Return compact workflow history."""
        return self.repository.list_history(limit=limit)

    def log_event(
        self,
        workflow_id: str,
        event_type: str,
        message: str,
        step_key: str = "",
        payload: dict[str, object] | None = None,
    ) -> None:
        """Persist and publish one workflow event."""
        payload = payload or {}
        self.repository.record_history(
            workflow_id=workflow_id,
            event_type=event_type,
            message=message,
            step_key=step_key,
            payload=payload,
        )
        self.repository.record_execution_log(
            workflow_id=workflow_id,
            step_key=step_key,
            message=message,
            level="info",
            payload={"event_type": event_type, **payload},
        )
        event = WorkflowEvent(
            workflow_id=workflow_id,
            event_type=event_type,
            message=message,
            step_key=step_key,
            payload=payload,
        )
        self.event_bus.publish(event)
        self._publish_platform_event(event)
        logger.info(
            "Workflow event %s for %s/%s: %s",
            event_type,
            workflow_id,
            step_key,
            message,
        )

    def _publish_platform_event(self, event: WorkflowEvent) -> None:
        if self.platform_event_bus is None:
            return
        payload = dict(event.payload)
        payload.update(
            {
                "workflow_id": event.workflow_id,
                "step_key": event.step_key,
                "message": event.message,
            }
        )
        self.platform_event_bus.publish(
            PlatformEvent(
                event_type=event.event_type,
                source="workflow_state_manager",
                category=EVENT_CATEGORY_WORKFLOW,
                priority=PRIORITY_NORMAL,
                correlation_id=event.workflow_id,
                payload=payload,
                created_at=event.created_at,
            )
        )
