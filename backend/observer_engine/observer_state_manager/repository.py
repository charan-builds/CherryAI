"""Repository for observer persistence."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from config.settings import AppSettings
from database.observer_models import ActivityLog, ObserverEventLog, StudySession
from database.session import create_database_engine, create_session_factory
from backend.observer_engine.schemas import StudySessionRecord


class ObserverStateRepository:
    """Database access object for observer records."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "ObserverStateRepository":
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

    def start_activity(
        self,
        application_name: str,
        window_title: str,
        started_at: datetime,
    ) -> str:
        """Create an activity interval and return its id."""
        with self._session_scope() as session:
            log = ActivityLog(
                application_name=application_name,
                window_title=window_title,
                started_at=started_at,
            )
            session.add(log)
            session.flush()
            return log.id

    def end_activity(self, activity_id: str, ended_at: datetime) -> None:
        """Close an activity interval."""
        with self._session_scope() as session:
            log = session.get(ActivityLog, activity_id)
            if log is None or log.ended_at is not None:
                return
            log.ended_at = ended_at
            log.duration_seconds = self._duration_seconds(log.started_at, ended_at)

    def record_event(
        self,
        event_type: str,
        payload: dict[str, object],
        created_at: datetime,
    ) -> str:
        """Persist an observer event."""
        with self._session_scope() as session:
            event = ObserverEventLog(
                event_type=event_type,
                payload_json=json.dumps(payload, default=str),
                created_at=created_at,
            )
            session.add(event)
            session.flush()
            return event.id

    def create_study_session(
        self,
        topic: str,
        metadata: dict[str, object],
        started_at: datetime,
    ) -> StudySessionRecord:
        """Create an active study session."""
        with self._session_scope() as session:
            study_session = StudySession(
                topic=topic,
                metadata_json=json.dumps(metadata, default=str),
                status="active",
                started_at=started_at,
            )
            session.add(study_session)
            session.flush()
            return self._to_study_record(study_session)

    def complete_study_session(
        self,
        session_id: str,
        ended_at: datetime,
        focus_seconds: float,
        idle_seconds: float,
        interruption_count: int,
    ) -> StudySessionRecord | None:
        """Complete an active study session."""
        with self._session_scope() as session:
            study_session = session.get(StudySession, session_id)
            if study_session is None:
                return None

            study_session.status = "completed"
            study_session.ended_at = ended_at
            study_session.duration_seconds = self._duration_seconds(
                study_session.started_at,
                ended_at,
            )
            study_session.focus_seconds = focus_seconds
            study_session.idle_seconds = idle_seconds
            study_session.interruption_count = interruption_count
            session.flush()
            return self._to_study_record(study_session)

    def get_active_study_session(self) -> StudySessionRecord | None:
        """Return the latest active study session."""
        statement = (
            select(StudySession)
            .where(StudySession.status == "active")
            .order_by(StudySession.started_at.desc())
            .limit(1)
        )
        with self.session_factory() as session:
            study_session = session.scalars(statement).first()
            if study_session is None:
                return None
            return self._to_study_record(study_session)

    def count_events(self, event_type: str | None = None) -> int:
        """Count persisted observer events."""
        statement = select(ObserverEventLog)
        if event_type:
            statement = statement.where(ObserverEventLog.event_type == event_type)
        with self.session_factory() as session:
            return len(session.scalars(statement).all())

    def count_activity_logs(self) -> int:
        """Count persisted activity logs."""
        with self.session_factory() as session:
            return len(session.scalars(select(ActivityLog)).all())

    def _to_study_record(self, study_session: StudySession) -> StudySessionRecord:
        return StudySessionRecord(
            id=study_session.id,
            topic=study_session.topic,
            status=study_session.status,
            started_at=study_session.started_at,
            ended_at=study_session.ended_at,
            duration_seconds=study_session.duration_seconds,
            focus_seconds=study_session.focus_seconds,
            idle_seconds=study_session.idle_seconds,
            interruption_count=study_session.interruption_count,
        )

    def _duration_seconds(self, started_at: datetime, ended_at: datetime) -> float:
        if started_at.tzinfo is None and ended_at.tzinfo is not None:
            ended_at = ended_at.replace(tzinfo=None)
        if started_at.tzinfo is not None and ended_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=None)
        return max((ended_at - started_at).total_seconds(), 0.0)
