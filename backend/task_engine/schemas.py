"""Task service data transfer objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from database.task_models import Task


@dataclass(frozen=True)
class TaskRecord:
    """Task data returned by the task service."""

    id: str
    title: str
    description: str
    status: str
    priority: str
    created_at: datetime
    completed_at: datetime | None

    @classmethod
    def from_model(cls, task: Task) -> "TaskRecord":
        """Convert an ORM model to an immutable service record."""
        return cls(
            id=task.id,
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            created_at=task.created_at,
            completed_at=task.completed_at,
        )


@dataclass(frozen=True)
class TaskStatistics:
    """Aggregate task completion statistics."""

    total: int
    open_count: int
    completed_count: int
    completed_today: int
    completion_rate: float


@dataclass(frozen=True)
class DailyTaskSummary:
    """Human-readable task summary for the current day."""

    created_today: int
    completed_today: int
    open_high_priority: int
    summary_text: str
