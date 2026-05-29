"""Repository helpers for productivity analysis."""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from typing import Iterator

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import Session, sessionmaker

from config.settings import AppSettings
from database.observer_models import ActivityLog, ObserverEventLog, StudySession
from database.session import create_database_engine, create_session_factory
from database.task_models import Task


class ProductivityDataRepository:
    """Reads task and observer records needed for productivity metrics."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "ProductivityDataRepository":
        engine = create_database_engine(settings)
        return cls(create_session_factory(engine))

    @contextmanager
    def _session_scope(self) -> Iterator[Session]:
        with self.session_factory() as session:
            yield session

    def count_created_tasks(self, start: datetime, end: datetime) -> int:
        """Count tasks created inside a datetime window."""
        statement = self._between(select(Task), Task.created_at, start, end)
        with self._session_scope() as session:
            return len(session.scalars(statement).all())

    def count_completed_tasks(self, start: datetime, end: datetime) -> int:
        """Count tasks completed inside a datetime window."""
        statement = self._between(
            select(Task).where(Task.status == "completed", Task.completed_at.is_not(None)),
            Task.completed_at,
            start,
            end,
        )
        with self._session_scope() as session:
            return len(session.scalars(statement).all())

    def count_open_tasks(self) -> int:
        """Count tasks that are still open."""
        statement = select(Task).where(Task.status != "completed")
        with self._session_scope() as session:
            return len(session.scalars(statement).all())

    def study_totals(self, start: datetime, end: datetime) -> dict[str, float | int]:
        """Return aggregate study duration, focus, idle, and interruptions."""
        statement = select(StudySession).where(
            or_(
                and_(StudySession.started_at >= start, StudySession.started_at < end),
                and_(StudySession.ended_at >= start, StudySession.ended_at < end),
                and_(StudySession.started_at < start, StudySession.ended_at >= end),
            )
        )
        with self._session_scope() as session:
            sessions = session.scalars(statement).all()

        return {
            "duration_seconds": sum(session.duration_seconds for session in sessions),
            "focus_seconds": sum(session.focus_seconds for session in sessions),
            "idle_seconds": sum(session.idle_seconds for session in sessions),
            "interruption_count": sum(session.interruption_count for session in sessions),
            "session_count": len(sessions),
        }

    def app_usage_totals(self, start: datetime, end: datetime) -> dict[str, float]:
        """Return app usage seconds grouped by application name."""
        statement = self._between(select(ActivityLog), ActivityLog.started_at, start, end)
        usage: dict[str, float] = defaultdict(float)
        with self._session_scope() as session:
            for activity in session.scalars(statement).all():
                usage[activity.application_name] += max(activity.duration_seconds, 0.0)
        return dict(sorted(usage.items(), key=lambda item: item[1], reverse=True))

    def count_events(self, event_type: str, start: datetime, end: datetime) -> int:
        """Count observer events by type in a datetime window."""
        statement = self._between(
            select(ObserverEventLog).where(ObserverEventLog.event_type == event_type),
            ObserverEventLog.created_at,
            start,
            end,
        )
        with self._session_scope() as session:
            return len(session.scalars(statement).all())

    def active_days(self, end_day: date, days: int) -> int:
        """Count recent days with at least one task completion or study session."""
        active = 0
        first_day = end_day - timedelta(days=max(days - 1, 0))
        current = first_day
        while current <= end_day:
            start, end = day_bounds(current)
            if self.count_completed_tasks(start, end) > 0:
                active += 1
            elif self.study_totals(start, end)["duration_seconds"] > 0:
                active += 1
            current += timedelta(days=1)
        return active

    def _between(
        self,
        statement: Select,
        column,
        start: datetime,
        end: datetime,
    ) -> Select:
        return statement.where(column >= start, column < end)


def day_bounds(day: date) -> tuple[datetime, datetime]:
    """Return naive UTC-compatible day bounds for SQLite comparisons."""
    start = datetime.combine(day, time.min)
    end = start + timedelta(days=1)
    return start, end
