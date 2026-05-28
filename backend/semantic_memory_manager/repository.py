"""Persistence for semantic memories."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from config.settings import AppSettings
from database.memory_models import SemanticMemory
from database.models import utc_now
from database.session import create_database_engine, create_session_factory
from backend.semantic_memory_manager.schemas import (
    SemanticMemoryCreate,
    SemanticMemoryRecord,
)


class SemanticMemoryRepository:
    """Database access for durable memories."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "SemanticMemoryRepository":
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

    def remember(self, memory: SemanticMemoryCreate) -> SemanticMemoryRecord:
        """Create a memory or reinforce an existing source-linked memory."""
        with self._session_scope() as session:
            row = self._find_existing(session, memory)
            if row is None:
                row = SemanticMemory(
                    category=memory.category,
                    title=memory.title,
                    content=memory.content,
                    source_type=memory.source_type,
                    source_id=memory.source_id,
                )
                session.add(row)
            else:
                row.repetition_count += 1
                row.last_reinforced_at = utc_now()

            row.category = memory.category
            row.title = memory.title
            row.content = memory.content
            row.importance = self._blend(row.importance, memory.importance)
            row.confidence = self._blend(row.confidence, memory.confidence)
            row.behavioral_significance = self._blend(
                row.behavioral_significance,
                memory.behavioral_significance,
            )
            row.metadata_json = json.dumps(memory.metadata, default=str)
            session.flush()
            return self._to_record(row)

    def list_memories(
        self,
        categories: tuple[str, ...] | None = None,
        limit: int = 50,
    ) -> list[SemanticMemoryRecord]:
        """List durable memories ordered by reinforcement and update time."""
        statement = select(SemanticMemory).order_by(
            SemanticMemory.last_reinforced_at.desc(),
            SemanticMemory.updated_at.desc(),
        )
        if categories:
            statement = statement.where(SemanticMemory.category.in_(categories))
        statement = statement.limit(limit)
        with self.session_factory() as session:
            return [self._to_record(row) for row in session.scalars(statement).all()]

    def prune_older_than(self, retention_days: int, limit: int = 100) -> int:
        """Delete stale low-confidence memories in small batches."""
        cutoff = utc_now() - timedelta(days=max(retention_days, 1))
        statement = (
            select(SemanticMemory)
            .where(
                SemanticMemory.last_reinforced_at < cutoff,
                SemanticMemory.importance < 0.7,
                SemanticMemory.confidence < 0.7,
            )
            .limit(max(limit, 1))
        )
        with self._session_scope() as session:
            rows = session.scalars(statement).all()
            for row in rows:
                session.delete(row)
            return len(rows)

    def count(self) -> int:
        """Count durable memories for tests and diagnostics."""
        with self.session_factory() as session:
            return len(session.scalars(select(SemanticMemory)).all())

    def _find_existing(
        self,
        session: Session,
        memory: SemanticMemoryCreate,
    ) -> SemanticMemory | None:
        if memory.source_id:
            statement = select(SemanticMemory).where(
                SemanticMemory.source_type == memory.source_type,
                SemanticMemory.source_id == memory.source_id,
            )
            existing = session.scalars(statement).first()
            if existing is not None:
                return existing

        statement = select(SemanticMemory).where(
            SemanticMemory.category == memory.category,
            SemanticMemory.title == memory.title,
        )
        return session.scalars(statement).first()

    def _to_record(self, row: SemanticMemory) -> SemanticMemoryRecord:
        try:
            metadata = json.loads(row.metadata_json or "{}")
        except json.JSONDecodeError:
            metadata = {}
        return SemanticMemoryRecord(
            id=row.id,
            category=row.category,
            title=row.title,
            content=row.content,
            source_type=row.source_type,
            source_id=row.source_id,
            importance=row.importance,
            confidence=row.confidence,
            repetition_count=row.repetition_count,
            behavioral_significance=row.behavioral_significance,
            metadata=metadata,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _blend(self, old_value: float | None, new_value: float) -> float:
        if old_value is None:
            old_value = new_value
        return round(max(min((old_value * 0.6) + (new_value * 0.4), 1.0), 0.0), 3)
