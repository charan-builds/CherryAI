"""Persistence for learned behavioral patterns."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from config.settings import AppSettings
from database.models import utc_now
from database.observer_models import ObserverEventLog, StudySession
from database.proactive_models import BehavioralPattern
from database.session import create_database_engine, create_session_factory
from backend.behavioral_pattern_engine.schemas import BehavioralPatternRecord


class BehavioralPatternRepository:
    """Reads observations and safely upserts learned patterns."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "BehavioralPatternRepository":
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

    def recent_study_sessions(self, since: datetime) -> list[StudySession]:
        """Return recent study sessions."""
        statement = (
            select(StudySession)
            .where(StudySession.started_at >= since)
            .order_by(StudySession.started_at.desc())
        )
        with self.session_factory() as session:
            return list(session.scalars(statement).all())

    def recent_events(self, since: datetime) -> list[ObserverEventLog]:
        """Return recent observer events."""
        statement = (
            select(ObserverEventLog)
            .where(ObserverEventLog.created_at >= since)
            .order_by(ObserverEventLog.created_at.desc())
        )
        with self.session_factory() as session:
            return list(session.scalars(statement).all())

    def upsert_pattern(
        self,
        pattern_type: str,
        pattern_key: str,
        description: str,
        confidence: float,
        sample_size: int,
        metadata: dict[str, object],
    ) -> BehavioralPatternRecord:
        """Create or update a learned pattern by stable type/key."""
        now = utc_now()
        with self._session_scope() as session:
            statement = select(BehavioralPattern).where(
                BehavioralPattern.pattern_type == pattern_type,
                BehavioralPattern.pattern_key == pattern_key,
            )
            pattern = session.scalars(statement).first()
            if pattern is None:
                pattern = BehavioralPattern(
                    pattern_type=pattern_type,
                    pattern_key=pattern_key,
                    first_seen_at=now,
                )
                session.add(pattern)

            pattern.description = description
            pattern.confidence = round(max(min(confidence, 1.0), 0.0), 3)
            pattern.sample_size = max(sample_size, 0)
            pattern.metadata_json = json.dumps(metadata, default=str)
            pattern.last_seen_at = now
            session.flush()
            return self._to_record(pattern)

    def list_patterns(
        self,
        pattern_type: str | None = None,
        limit: int = 20,
    ) -> list[BehavioralPatternRecord]:
        """List learned patterns ordered by confidence."""
        statement = select(BehavioralPattern).order_by(
            BehavioralPattern.confidence.desc(),
            BehavioralPattern.updated_at.desc(),
        )
        if pattern_type is not None:
            statement = statement.where(BehavioralPattern.pattern_type == pattern_type)
        statement = statement.limit(limit)
        with self.session_factory() as session:
            return [self._to_record(pattern) for pattern in session.scalars(statement).all()]

    def _to_record(self, pattern: BehavioralPattern) -> BehavioralPatternRecord:
        try:
            metadata = json.loads(pattern.metadata_json or "{}")
        except json.JSONDecodeError:
            metadata = {}
        return BehavioralPatternRecord(
            id=pattern.id,
            pattern_type=pattern.pattern_type,
            pattern_key=pattern.pattern_key,
            description=pattern.description,
            confidence=pattern.confidence,
            sample_size=pattern.sample_size,
            metadata=metadata,
            last_seen_at=pattern.last_seen_at,
        )


def lookback_start(days: int) -> datetime:
    """Return the datetime boundary for pattern learning."""
    return utc_now() - timedelta(days=max(days, 1))
