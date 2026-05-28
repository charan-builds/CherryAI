"""Repository layer for persisted tasks."""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import contextmanager
from datetime import date, datetime
from typing import Iterator

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, sessionmaker

from config.settings import AppSettings
from database.session import create_database_engine, create_session_factory
from database.task_models import Task
from backend.task_engine.schemas import TaskRecord


class TaskNotFoundError(ValueError):
    """Raised when a task id does not exist."""


class TaskRepository:
    """Database access object for tasks.

    All ORM sessions are opened and closed inside repository methods. The rest
    of the app works with immutable TaskRecord objects instead of live ORM rows.
    """

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "TaskRepository":
        """Create a repository from application settings."""
        engine = create_database_engine(settings)
        return cls(create_session_factory(engine))

    @contextmanager
    def _session_scope(self) -> Iterator[Session]:
        """Provide a transactional session boundary."""
        with self.session_factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def create(self, title: str, description: str, priority: str) -> TaskRecord:
        """Persist a new task."""
        with self._session_scope() as session:
            task = Task(
                title=title,
                description=description,
                priority=priority,
            )
            session.add(task)
            session.flush()
            return TaskRecord.from_model(task)

    def get(self, task_id: str) -> TaskRecord:
        """Fetch a task by id."""
        with self.session_factory() as session:
            task = self._get_model(session, task_id)
            return TaskRecord.from_model(task)

    def list_tasks(
        self,
        statuses: Iterable[str] | None = None,
        priority: str | None = None,
    ) -> list[TaskRecord]:
        """List tasks with optional status and priority filters."""
        statement: Select[tuple[Task]] = select(Task).order_by(
            Task.created_at.desc()
        )

        if statuses:
            statement = statement.where(Task.status.in_(tuple(statuses)))

        if priority:
            statement = statement.where(Task.priority == priority)

        with self.session_factory() as session:
            tasks = session.scalars(statement).all()
            return [TaskRecord.from_model(task) for task in tasks]

    def update(
        self,
        task_id: str,
        title: str,
        description: str,
        priority: str,
    ) -> TaskRecord:
        """Update editable task fields."""
        with self._session_scope() as session:
            task = self._get_model(session, task_id)
            task.title = title
            task.description = description
            task.priority = priority
            session.flush()
            return TaskRecord.from_model(task)

    def set_completed(self, task_id: str, completed_at: datetime) -> TaskRecord:
        """Mark a task complete."""
        with self._session_scope() as session:
            task = self._get_model(session, task_id)
            task.status = "completed"
            task.completed_at = completed_at
            session.flush()
            return TaskRecord.from_model(task)

    def set_open(self, task_id: str) -> TaskRecord:
        """Reopen a completed task."""
        with self._session_scope() as session:
            task = self._get_model(session, task_id)
            task.status = "pending"
            task.completed_at = None
            session.flush()
            return TaskRecord.from_model(task)

    def delete(self, task_id: str) -> None:
        """Delete a task."""
        with self._session_scope() as session:
            task = self._get_model(session, task_id)
            session.delete(task)

    def list_created_on(self, day: date) -> list[TaskRecord]:
        """Return tasks created on a UTC date."""
        return [
            task
            for task in self.list_tasks()
            if task.created_at.date() == day
        ]

    def list_completed_on(self, day: date) -> list[TaskRecord]:
        """Return tasks completed on a UTC date."""
        return [
            task
            for task in self.list_tasks(statuses=("completed",))
            if task.completed_at is not None and task.completed_at.date() == day
        ]

    def _get_model(self, session: Session, task_id: str) -> Task:
        task = session.get(Task, task_id)
        if task is None:
            raise TaskNotFoundError(f"Task not found: {task_id}")
        return task
