"""Workflow scheduler for delayed and recurring workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from config.settings import AppSettings
from database.models import utc_now
from backend.goal_planner_engine.service import GoalPlannerEngine
from backend.workflow_scheduler.schemas import ScheduledWorkflowRecord
from backend.workflow_state_manager.repository import WorkflowRepository
from backend.workflow_state_manager.serialization import plan_to_dict


@dataclass
class WorkflowScheduler:
    """Stores delayed, recurring, study, and reminder-triggered workflows."""

    settings: AppSettings
    repository: WorkflowRepository | None = None
    goal_planner: GoalPlannerEngine | None = None

    def __post_init__(self) -> None:
        self.repository = self.repository or WorkflowRepository.from_settings(
            self.settings
        )

    def schedule_delayed_workflow(
        self,
        goal: str,
        run_at: datetime,
    ) -> str:
        """Schedule a workflow for one future time."""
        return self.repository.create_schedule(
            goal=goal,
            plan=self._plan_payload(goal),
            trigger_type="delayed",
            run_at=run_at,
        )

    def schedule_recurring_workflow(
        self,
        goal: str,
        first_run_at: datetime,
        recurrence_seconds: int,
    ) -> str:
        """Schedule a recurring workflow."""
        if recurrence_seconds <= 0:
            raise ValueError("Recurring workflow interval must be positive.")
        return self.repository.create_schedule(
            goal=goal,
            plan=self._plan_payload(goal),
            trigger_type="recurring",
            run_at=first_run_at,
            recurrence_seconds=recurrence_seconds,
        )

    def schedule_study_session(
        self,
        topic: str,
        run_at: datetime,
        recurrence_seconds: int = 0,
    ) -> str:
        """Schedule a study-session workflow."""
        goal = f"Prepare {topic.strip() or 'Focused'} study session"
        trigger_type = "recurring_study_session" if recurrence_seconds else "study_session"
        return self.repository.create_schedule(
            goal=goal,
            plan=self._plan_payload(goal),
            trigger_type=trigger_type,
            run_at=run_at,
            recurrence_seconds=recurrence_seconds,
        )

    def schedule_reminder_workflow(
        self,
        message: str,
        delay_seconds: int,
    ) -> str:
        """Schedule a reminder-triggered workflow after a delay."""
        run_at = utc_now() + timedelta(seconds=max(delay_seconds, 0))
        return self.repository.create_schedule(
            goal=f"Reminder: {message}",
            plan={},
            trigger_type="reminder",
            run_at=run_at,
        )

    def due_workflows(
        self,
        now: datetime | None = None,
    ) -> list[ScheduledWorkflowRecord]:
        """Return schedules due to run."""
        due_rows = self.repository.list_due_schedules(now or utc_now())
        return [self._record_from_row(row) for row in due_rows]

    def mark_dispatched(
        self,
        schedule_id: str,
        dispatched_at: datetime | None = None,
    ) -> None:
        """Mark a schedule dispatched or advance its recurrence."""
        self.repository.mark_schedule_dispatched(schedule_id, dispatched_at or utc_now())

    def _plan_payload(self, goal: str) -> dict[str, object]:
        if self.goal_planner is None:
            return {}
        return plan_to_dict(self.goal_planner.create_plan(goal))

    def _record_from_row(self, row: dict[str, object]) -> ScheduledWorkflowRecord:
        return ScheduledWorkflowRecord(
            id=str(row["id"]),
            goal=str(row["goal"]),
            plan=dict(row.get("plan", {}) or {}),
            status=str(row["status"]),
            trigger_type=str(row["trigger_type"]),
            run_at=row["run_at"],  # type: ignore[arg-type]
            recurrence_seconds=int(row["recurrence_seconds"]),
            last_run_at=row.get("last_run_at"),  # type: ignore[arg-type]
            next_run_at=row.get("next_run_at"),  # type: ignore[arg-type]
        )
