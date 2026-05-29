"""Persistence for knowledge memory records."""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from config.settings import AppSettings
from database.knowledge_models import KnowledgeMemory
from database.session import create_database_engine, create_session_factory
from backend.knowledge_memory_manager.schemas import (
    KnowledgeMemoryCreate,
    KnowledgeMemoryRecord,
)


class KnowledgeMemoryRepository:
    """Database access for knowledge summaries and notes."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "KnowledgeMemoryRepository":
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

    def upsert(self, item: KnowledgeMemoryCreate) -> KnowledgeMemoryRecord:
        """Create or refresh a knowledge memory by content hash."""
        content_hash = self.content_hash(item)
        with self._session_scope() as session:
            row = session.scalars(
                select(KnowledgeMemory).where(
                    KnowledgeMemory.content_hash == content_hash
                )
            ).first()
            if row is None:
                row = KnowledgeMemory(
                    source_type=item.source_type,
                    source_name=item.source_name,
                    title=item.title,
                    summary=item.summary,
                    content_hash=content_hash,
                )
                session.add(row)

            row.source_type = item.source_type
            row.source_name = item.source_name
            row.title = item.title
            row.summary = item.summary
            row.notes_json = json.dumps(item.notes, default=str)
            row.concepts_json = json.dumps(item.concepts, default=str)
            row.tags_json = json.dumps(item.tags, default=str)
            row.metadata_json = json.dumps(item.metadata, default=str)
            session.flush()
            return self._to_record(row)

    def update_semantic_link(
        self,
        record_id: str,
        semantic_memory_id: str,
    ) -> KnowledgeMemoryRecord | None:
        """Persist the semantic-memory link for a knowledge memory."""
        with self._session_scope() as session:
            row = session.get(KnowledgeMemory, record_id)
            if row is None:
                return None
            row.semantic_memory_id = semantic_memory_id
            session.flush()
            return self._to_record(row)

    def list_recent(self, limit: int = 20) -> list[KnowledgeMemoryRecord]:
        """Return recent knowledge memories."""
        statement = (
            select(KnowledgeMemory)
            .order_by(KnowledgeMemory.updated_at.desc())
            .limit(max(limit, 1))
        )
        with self.session_factory() as session:
            return [self._to_record(row) for row in session.scalars(statement)]

    def count(self) -> int:
        """Count knowledge memory records."""
        with self.session_factory() as session:
            return len(session.scalars(select(KnowledgeMemory)).all())

    def content_hash(self, item: KnowledgeMemoryCreate) -> str:
        """Return a stable hash for deduplication."""
        digest = hashlib.sha256()
        digest.update(item.source_type.encode("utf-8"))
        digest.update(item.source_name.encode("utf-8"))
        digest.update(item.summary.encode("utf-8"))
        return digest.hexdigest()

    def _to_record(self, row: KnowledgeMemory) -> KnowledgeMemoryRecord:
        return KnowledgeMemoryRecord(
            id=row.id,
            source_type=row.source_type,
            source_name=row.source_name,
            title=row.title,
            summary=row.summary,
            notes=tuple(self._loads(row.notes_json, [])),
            concepts=tuple(self._loads(row.concepts_json, [])),
            tags=tuple(self._loads(row.tags_json, [])),
            content_hash=row.content_hash,
            semantic_memory_id=row.semantic_memory_id,
            metadata=self._loads(row.metadata_json, {}),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _loads(self, raw_value: str, fallback):
        try:
            return json.loads(raw_value or "")
        except json.JSONDecodeError:
            return fallback
