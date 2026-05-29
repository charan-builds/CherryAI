"""Repository for workflow state persistence."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from config.settings import AppSettings
from database.models import utc_now
from database.session import create_database_engine, create_session_factory
from database.workflow_models import (
    ScheduledWorkflow,
    Workflow,
    WorkflowExecutionLog,
    WorkflowHistory,
    WorkflowMemory,
    WorkflowStep,
)
from backend.workflow_state_manager.schemas import (
    WorkflowPlan,
    WorkflowRecord,
    WorkflowStepPlan,
    WorkflowStepRecord,
)


class WorkflowNotFoundError(ValueError):
    """Raised when a workflow id does not exist."""


class WorkflowRepository:
    """Database access object for workflow state and related records."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "WorkflowRepository":
        """Create a repository from application settings."""
        engine = create_database_engine(settings)
        return cls(create_session_factory(engine))

    @contextmanager
    def _session_scope(self) -> Iterator[Session]:
        with self.session_factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def create_workflow(self, plan: WorkflowPlan) -> WorkflowRecord:
        """Persist a workflow and its ordered steps."""
        with self._session_scope() as session:
            workflow = Workflow(
                id=plan.id,
                name=plan.name,
                goal=plan.goal,
                status="planned",
                source=plan.source,
                metadata_json=_dump_json(plan.metadata),
            )
            session.add(workflow)
            for index, step in enumerate(plan.steps):
                session.add(self._step_model(plan.id, step, index))
            session.flush()
            return self._workflow_record(workflow)

    def get_workflow(self, workflow_id: str) -> WorkflowRecord:
        """Return one workflow record."""
        with self.session_factory() as session:
            return self._workflow_record(self._get_workflow_model(session, workflow_id))

    def get_snapshot_steps(self, workflow_id: str) -> tuple[WorkflowStepRecord, ...]:
        """Return ordered steps for a workflow."""
        statement = (
            select(WorkflowStep)
            .where(WorkflowStep.workflow_id == workflow_id)
            .order_by(WorkflowStep.position.asc())
        )
        with self.session_factory() as session:
            return tuple(self._step_record(step) for step in session.scalars(statement))

    def list_workflows(
        self,
        statuses: tuple[str, ...] | None = None,
        limit: int = 20,
    ) -> list[WorkflowRecord]:
        """List workflows newest-first."""
        statement = select(Workflow).order_by(Workflow.created_at.desc()).limit(limit)
        if statuses:
            statement = statement.where(Workflow.status.in_(statuses))

        with self.session_factory() as session:
            return [self._workflow_record(row) for row in session.scalars(statement)]

    def update_workflow(
        self,
        workflow_id: str,
        status: str | None = None,
        current_step_key: str | None = None,
        progress_percent: float | None = None,
        failure_reason: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> WorkflowRecord:
        """Update workflow runtime state."""
        with self._session_scope() as session:
            workflow = self._get_workflow_model(session, workflow_id)
            if status is not None:
                workflow.status = status
            if current_step_key is not None:
                workflow.current_step_key = current_step_key
            if progress_percent is not None:
                workflow.progress_percent = max(min(progress_percent, 100.0), 0.0)
            if failure_reason is not None:
                workflow.failure_reason = failure_reason
            if started_at is not None:
                workflow.started_at = started_at
            if completed_at is not None:
                workflow.completed_at = completed_at
            workflow.updated_at = utc_now()
            session.flush()
            return self._workflow_record(workflow)

    def update_step(
        self,
        workflow_id: str,
        step_key: str,
        status: str,
        attempts: int | None = None,
        error_message: str = "",
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> WorkflowStepRecord:
        """Update one persisted step."""
        with self._session_scope() as session:
            step = self._get_step_model(session, workflow_id, step_key)
            step.status = status
            if attempts is not None:
                step.attempts = attempts
            step.error_message = error_message
            if started_at is not None:
                step.started_at = started_at
            if completed_at is not None:
                step.completed_at = completed_at
            session.flush()
            return self._step_record(step)

    def record_history(
        self,
        workflow_id: str,
        event_type: str,
        message: str,
        step_key: str = "",
        payload: dict[str, object] | None = None,
    ) -> None:
        """Persist a user-facing workflow event."""
        with self._session_scope() as session:
            session.add(
                WorkflowHistory(
                    workflow_id=workflow_id,
                    event_type=event_type,
                    step_key=step_key,
                    message=message,
                    payload_json=_dump_json(payload or {}),
                )
            )

    def record_execution_log(
        self,
        workflow_id: str,
        message: str,
        step_key: str = "",
        level: str = "info",
        payload: dict[str, object] | None = None,
    ) -> None:
        """Persist a detailed execution log row."""
        with self._session_scope() as session:
            session.add(
                WorkflowExecutionLog(
                    workflow_id=workflow_id,
                    step_key=step_key,
                    level=level,
                    message=message,
                    payload_json=_dump_json(payload or {}),
                )
            )

    def list_history(self, limit: int = 20) -> list[dict[str, object]]:
        """Return recent workflow history for compact UI rendering."""
        statement = (
            select(WorkflowHistory)
            .order_by(WorkflowHistory.created_at.desc())
            .limit(limit)
        )
        with self.session_factory() as session:
            return [
                {
                    "workflow_id": row.workflow_id,
                    "event_type": row.event_type,
                    "step_key": row.step_key,
                    "message": row.message,
                    "payload": _load_json(row.payload_json, {}),
                    "created_at": row.created_at,
                }
                for row in session.scalars(statement)
            ]

    def upsert_memory(
        self,
        goal_signature: str,
        workflow_name: str,
        outcome: str,
        plan_json: dict[str, object],
        summary: str,
        preferred: bool = False,
    ) -> None:
        """Create or update a workflow memory pattern."""
        statement = select(WorkflowMemory).where(
            WorkflowMemory.goal_signature == goal_signature
        )
        with self._session_scope() as session:
            memory = session.scalars(statement).first()
            if memory is None:
                memory = WorkflowMemory(
                    goal_signature=goal_signature,
                    workflow_name=workflow_name,
                    plan_json=_dump_json(plan_json),
                    success_count=0,
                    failure_count=0,
                    preferred=0,
                )
                session.add(memory)
            memory.workflow_name = workflow_name
            memory.outcome = outcome
            memory.summary = summary
            memory.plan_json = _dump_json(plan_json)
            memory.last_used_at = utc_now()
            memory.preferred = 1 if preferred else (memory.preferred or 0)
            if outcome == "success":
                memory.success_count = (memory.success_count or 0) + 1
            else:
                memory.failure_count = (memory.failure_count or 0) + 1

    def list_memory(self, limit: int = 20) -> list[dict[str, object]]:
        """Return recent workflow memory patterns."""
        statement = (
            select(WorkflowMemory)
            .order_by(WorkflowMemory.updated_at.desc())
            .limit(limit)
        )
        with self.session_factory() as session:
            return [
                {
                    "goal_signature": row.goal_signature,
                    "workflow_name": row.workflow_name,
                    "outcome": row.outcome,
                    "summary": row.summary,
                    "success_count": row.success_count,
                    "failure_count": row.failure_count,
                    "preferred": bool(row.preferred),
                    "plan": _load_json(row.plan_json, {}),
                    "last_used_at": row.last_used_at,
                }
                for row in session.scalars(statement)
            ]

    def create_schedule(
        self,
        goal: str,
        plan: dict[str, object],
        trigger_type: str,
        run_at: datetime,
        recurrence_seconds: int = 0,
    ) -> str:
        """Persist a delayed or recurring workflow schedule."""
        with self._session_scope() as session:
            schedule = ScheduledWorkflow(
                goal=goal,
                plan_json=_dump_json(plan),
                trigger_type=trigger_type,
                run_at=run_at,
                recurrence_seconds=max(recurrence_seconds, 0),
                next_run_at=run_at,
            )
            session.add(schedule)
            session.flush()
            return schedule.id

    def list_due_schedules(self, now: datetime) -> list[dict[str, object]]:
        """Return schedules that are due to dispatch."""
        statement = select(ScheduledWorkflow).where(
            ScheduledWorkflow.status == "scheduled",
            ScheduledWorkflow.next_run_at <= now,
        )
        with self.session_factory() as session:
            return [self._schedule_record(row) for row in session.scalars(statement)]

    def mark_schedule_dispatched(self, schedule_id: str, dispatched_at: datetime) -> None:
        """Mark a schedule as dispatched or advance its recurrence."""
        with self._session_scope() as session:
            schedule = session.get(ScheduledWorkflow, schedule_id)
            if schedule is None:
                return
            schedule.last_run_at = dispatched_at
            if schedule.recurrence_seconds > 0:
                from datetime import timedelta

                schedule.next_run_at = dispatched_at + timedelta(
                    seconds=schedule.recurrence_seconds
                )
            else:
                schedule.status = "completed"

    def _step_model(
        self,
        workflow_id: str,
        step: WorkflowStepPlan,
        fallback_position: int,
    ) -> WorkflowStep:
        return WorkflowStep(
            workflow_id=workflow_id,
            step_key=step.key,
            name=step.name,
            action_type=step.action_type,
            action_name=step.action_name,
            parameters_json=_dump_json(step.parameters),
            depends_on_json=_dump_json(list(step.depends_on)),
            condition_kind=step.condition_kind,
            condition_json=_dump_json(step.condition_data),
            position=step.position or fallback_position,
            max_retries=step.retries,
            timeout_seconds=step.timeout_seconds or 0.0,
            continue_on_failure=1 if step.continue_on_failure else 0,
        )

    def _get_workflow_model(self, session: Session, workflow_id: str) -> Workflow:
        workflow = session.get(Workflow, workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(f"Workflow not found: {workflow_id}")
        return workflow

    def _get_step_model(
        self,
        session: Session,
        workflow_id: str,
        step_key: str,
    ) -> WorkflowStep:
        statement = select(WorkflowStep).where(
            WorkflowStep.workflow_id == workflow_id,
            WorkflowStep.step_key == step_key,
        )
        step = session.scalars(statement).first()
        if step is None:
            raise WorkflowNotFoundError(f"Workflow step not found: {step_key}")
        return step

    def _workflow_record(self, workflow: Workflow) -> WorkflowRecord:
        return WorkflowRecord(
            id=workflow.id,
            name=workflow.name,
            goal=workflow.goal,
            status=workflow.status,
            source=workflow.source,
            metadata=_load_json(workflow.metadata_json, {}),
            current_step_key=workflow.current_step_key,
            progress_percent=workflow.progress_percent,
            failure_reason=workflow.failure_reason,
            created_at=workflow.created_at,
            started_at=workflow.started_at,
            completed_at=workflow.completed_at,
        )

    def _step_record(self, step: WorkflowStep) -> WorkflowStepRecord:
        return WorkflowStepRecord(
            workflow_id=step.workflow_id,
            key=step.step_key,
            name=step.name,
            action_type=step.action_type,
            action_name=step.action_name,
            parameters=_load_json(step.parameters_json, {}),
            depends_on=tuple(_load_json(step.depends_on_json, [])),
            condition_kind=step.condition_kind,
            condition_data=_load_json(step.condition_json, {}),
            status=step.status,
            position=step.position,
            attempts=step.attempts,
            max_retries=step.max_retries,
            timeout_seconds=step.timeout_seconds,
            continue_on_failure=bool(step.continue_on_failure),
            error_message=step.error_message,
            started_at=step.started_at,
            completed_at=step.completed_at,
        )

    def _schedule_record(self, schedule: ScheduledWorkflow) -> dict[str, object]:
        return {
            "id": schedule.id,
            "goal": schedule.goal,
            "plan": _load_json(schedule.plan_json, {}),
            "status": schedule.status,
            "trigger_type": schedule.trigger_type,
            "run_at": schedule.run_at,
            "recurrence_seconds": schedule.recurrence_seconds,
            "last_run_at": schedule.last_run_at,
            "next_run_at": schedule.next_run_at,
        }


def _dump_json(payload: object) -> str:
    return json.dumps(payload, default=str)


def _load_json(raw_value: str, fallback):
    try:
        return json.loads(raw_value or "")
    except (TypeError, json.JSONDecodeError):
        return fallback
