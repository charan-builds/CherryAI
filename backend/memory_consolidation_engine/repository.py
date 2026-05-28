"""Persistence and source reads for memory consolidation."""

from __future__ import annotations

import json
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from config.settings import AppSettings
from database.memory_models import ConsolidatedMemoryPattern
from database.models import utc_now
from database.observer_models import ObserverEventLog, StudySession
from database.proactive_models import ProductivitySummary
from database.session import create_database_engine, create_session_factory
from backend.memory_consolidation_engine.schemas import ConsolidatedPatternRecord


class MemoryConsolidationRepository:
    """Reads raw activity and upserts consolidated patterns."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "MemoryConsolidationRepository":
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
        statement = select(StudySession).where(StudySession.started_at >= since)
        with self.session_factory() as session:
            return list(session.scalars(statement).all())

    def recent_events(self, since: datetime) -> list[ObserverEventLog]:
        """Return recent observer events."""
        statement = select(ObserverEventLog).where(ObserverEventLog.created_at >= since)
        with self.session_factory() as session:
            return list(session.scalars(statement).all())

    def recent_summaries(self, since: datetime) -> list[ProductivitySummary]:
        """Return recent productivity summaries."""
        statement = select(ProductivitySummary).where(ProductivitySummary.updated_at >= since)
        with self.session_factory() as session:
            return list(session.scalars(statement).all())

    def upsert_pattern(
        self,
        pattern_type: str,
        pattern_key: str,
        title: str,
        insight: str,
        confidence: float,
        evidence_count: int,
        metadata: dict[str, object],
    ) -> ConsolidatedPatternRecord:
        """Create or update one consolidated pattern."""
        with self._session_scope() as session:
            row = session.scalars(
                select(ConsolidatedMemoryPattern).where(
                    ConsolidatedMemoryPattern.pattern_type == pattern_type,
                    ConsolidatedMemoryPattern.pattern_key == pattern_key,
                )
            ).first()
            if row is None:
                row = ConsolidatedMemoryPattern(
                    pattern_type=pattern_type,
                    pattern_key=pattern_key,
                    title=title,
                    insight=insight,
                )
                session.add(row)

            row.title = title
            row.insight = insight
            row.confidence = round(max(min(confidence, 1.0), 0.0), 3)
            row.evidence_count = max(evidence_count, 0)
            row.metadata_json = json.dumps(metadata, default=str)
            session.flush()
            return self._to_record(row)

    def list_patterns(self, limit: int = 20) -> list[ConsolidatedPatternRecord]:
        """List consolidated memory patterns."""
        statement = (
            select(ConsolidatedMemoryPattern)
            .order_by(
                ConsolidatedMemoryPattern.confidence.desc(),
                ConsolidatedMemoryPattern.updated_at.desc(),
            )
            .limit(limit)
        )
        with self.session_factory() as session:
            return [self._to_record(row) for row in session.scalars(statement).all()]

    def count_patterns(self) -> int:
        """Count consolidated patterns for tests."""
        with self.session_factory() as session:
            return len(session.scalars(select(ConsolidatedMemoryPattern)).all())

    def _to_record(self, row: ConsolidatedMemoryPattern) -> ConsolidatedPatternRecord:
        try:
            metadata = json.loads(row.metadata_json or "{}")
        except json.JSONDecodeError:
            metadata = {}
        return ConsolidatedPatternRecord(
            id=row.id,
            pattern_type=row.pattern_type,
            pattern_key=row.pattern_key,
            title=row.title,
            insight=row.insight,
            confidence=row.confidence,
            evidence_count=row.evidence_count,
            metadata=metadata,
        )


def consolidation_since(days: int) -> datetime:
    """Return lookback start for consolidation."""
    return utc_now() - timedelta(days=max(days, 1))
