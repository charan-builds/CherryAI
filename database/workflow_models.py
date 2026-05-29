"""Workflow engine persistence models."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
from database.models import utc_now


class Workflow(Base):
    """Persisted workflow run."""

    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="planned", index=True)
    source: Mapped[str] = mapped_column(String(64), default="heuristic")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    current_step_key: Mapped[str] = mapped_column(String(120), default="")
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)
    failure_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class WorkflowStep(Base):
    """Persisted workflow step definition and runtime state."""

    __tablename__ = "workflow_steps"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    workflow_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    step_key: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    action_name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    parameters_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    depends_on_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    condition_kind: Mapped[str] = mapped_column(String(80), default="always")
    condition_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=0)
    timeout_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    continue_on_failure: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkflowHistory(Base):
    """User-facing workflow event history."""

    __tablename__ = "workflow_history"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    workflow_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    step_key: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class WorkflowExecutionLog(Base):
    """Detailed workflow execution audit log."""

    __tablename__ = "workflow_execution_logs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    workflow_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    step_key: Mapped[str] = mapped_column(String(120), default="", index=True)
    level: Mapped[str] = mapped_column(String(32), default="info")
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class WorkflowMemory(Base):
    """Aggregated memory for repeated workflow patterns."""

    __tablename__ = "workflow_memory"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    goal_signature: Mapped[str] = mapped_column(String(240), index=True, nullable=False)
    workflow_name: Mapped[str] = mapped_column(String(240), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), default="unknown")
    plan_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    preferred: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ScheduledWorkflow(Base):
    """Delayed or recurring workflow trigger."""

    __tablename__ = "scheduled_workflows"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    plan_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="scheduled", index=True)
    trigger_type: Mapped[str] = mapped_column(String(64), default="delayed")
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recurrence_seconds: Mapped[int] = mapped_column(Integer, default=0)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
