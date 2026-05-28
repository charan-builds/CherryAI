"""Task engine service layer."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config.settings import AppSettings
from database.models import utc_now
from backend.task_engine.constants import (
    OPEN_TASK_STATUSES,
    TASK_PRIORITIES,
    TASK_PRIORITY_HIGH,
    TASK_PRIORITY_NORMAL,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_PENDING,
)
from backend.task_engine.repository import TaskRepository
from backend.task_engine.schemas import DailyTaskSummary, TaskRecord, TaskStatistics

logger = logging.getLogger(__name__)


@dataclass
class TaskEngine:
    """Coordinates task validation, persistence, and reporting."""

    settings: AppSettings
    repository: TaskRepository | None = None
    analytics_engine: object | None = None

    def __post_init__(self) -> None:
        if self.repository is None:
            self.repository = TaskRepository.from_settings(self.settings)

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = TASK_PRIORITY_NORMAL,
    ) -> TaskRecord:
        """Create and persist a task."""
        title = self._clean_title(title)
        description = description.strip()
        priority = self._validate_priority(priority)

        task = self.repository.create(title, description, priority)
        logger.info("Created task: %s", task.id)
        self._record_event("task_created", priority=task.priority)
        return task

    def get_task(self, task_id: str) -> TaskRecord:
        """Return one task by id."""
        return self.repository.get(task_id)

    def list_tasks(
        self,
        status_filter: str = "open",
        priority_filter: str = "all",
    ) -> list[TaskRecord]:
        """List tasks for the UI with friendly filters."""
        statuses = self._map_status_filter(status_filter)
        priority = None if priority_filter == "all" else self._validate_priority(
            priority_filter
        )
        return self.repository.list_tasks(statuses=statuses, priority=priority)

    def update_task(
        self,
        task_id: str,
        title: str,
        description: str = "",
        priority: str = TASK_PRIORITY_NORMAL,
    ) -> TaskRecord:
        """Update a task's editable fields."""
        task = self.repository.update(
            task_id=task_id,
            title=self._clean_title(title),
            description=description.strip(),
            priority=self._validate_priority(priority),
        )
        logger.info("Updated task: %s", task.id)
        self._record_event("task_updated", priority=task.priority)
        return task

    def complete_task(self, task_id: str) -> TaskRecord:
        """Mark a task complete."""
        task = self.repository.set_completed(task_id, completed_at=utc_now())
        logger.info("Completed task: %s", task.id)
        self._record_event("task_completed", priority=task.priority)
        return task

    def reopen_task(self, task_id: str) -> TaskRecord:
        """Move a completed task back to open."""
        task = self.repository.set_open(task_id)
        logger.info("Reopened task: %s", task.id)
        self._record_event("task_reopened", priority=task.priority)
        return task

    def delete_task(self, task_id: str) -> None:
        """Delete a task permanently."""
        self.repository.delete(task_id)
        logger.info("Deleted task: %s", task_id)
        self._record_event("task_deleted")

    def get_statistics(self) -> TaskStatistics:
        """Return task completion statistics."""
        all_tasks = self.repository.list_tasks()
        completed = [
            task for task in all_tasks if task.status == TASK_STATUS_COMPLETED
        ]
        today = utc_now().date()
        completed_today = [
            task
            for task in completed
            if task.completed_at is not None and task.completed_at.date() == today
        ]
        total = len(all_tasks)
        completion_rate = round((len(completed) / total) * 100, 1) if total else 0.0

        return TaskStatistics(
            total=total,
            open_count=total - len(completed),
            completed_count=len(completed),
            completed_today=len(completed_today),
            completion_rate=completion_rate,
        )

    def generate_daily_summary(self) -> DailyTaskSummary:
        """Generate a concise daily task summary."""
        today = utc_now().date()
        created_today = self.repository.list_created_on(today)
        completed_today = self.repository.list_completed_on(today)
        high_priority_open = [
            task
            for task in self.repository.list_tasks(
                statuses=OPEN_TASK_STATUSES,
                priority=TASK_PRIORITY_HIGH,
            )
        ]

        summary_text = (
            f"Today: {len(created_today)} created, "
            f"{len(completed_today)} completed, "
            f"{len(high_priority_open)} high-priority open."
        )

        return DailyTaskSummary(
            created_today=len(created_today),
            completed_today=len(completed_today),
            open_high_priority=len(high_priority_open),
            summary_text=summary_text,
        )

    def _clean_title(self, title: str) -> str:
        cleaned = title.strip()
        if not cleaned:
            raise ValueError("Task title is required.")
        if len(cleaned) > 240:
            raise ValueError("Task title must be 240 characters or fewer.")
        return cleaned

    def _validate_priority(self, priority: str) -> str:
        normalized = priority.strip().lower()
        if normalized not in TASK_PRIORITIES:
            allowed = ", ".join(TASK_PRIORITIES)
            raise ValueError(f"Task priority must be one of: {allowed}.")
        return normalized

    def _map_status_filter(self, status_filter: str) -> tuple[str, ...] | None:
        normalized = status_filter.strip().lower()
        if normalized == "all":
            return None
        if normalized == "open":
            return OPEN_TASK_STATUSES
        if normalized in {TASK_STATUS_PENDING, TASK_STATUS_COMPLETED}:
            return (normalized,)
        raise ValueError("Task status filter must be all, open, pending, or completed.")

    def _record_event(self, name: str, **properties: str) -> None:
        """Send placeholder analytics events when the analytics engine is present."""
        if self.analytics_engine is not None and hasattr(
            self.analytics_engine,
            "record",
        ):
            self.analytics_engine.record(name, **properties)
