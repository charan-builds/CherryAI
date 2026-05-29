"""Workflow scheduler schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ScheduledWorkflowRecord:
    """Scheduled workflow trigger returned by the scheduler."""

    id: str
    goal: str
    plan: dict[str, object]
    status: str
    trigger_type: str
    run_at: datetime
    recurrence_seconds: int
    last_run_at: datetime | None
    next_run_at: datetime | None
    metadata: dict[str, object] = field(default_factory=dict)
