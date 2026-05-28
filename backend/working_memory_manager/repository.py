"""Persistence for working memory state."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from config.settings import AppSettings
from database.memory_models import WorkingMemoryState
from database.models import utc_now
from database.session import create_database_engine, create_session_factory
from backend.working_memory_manager.schemas import WorkingMemoryRecord


class WorkingMemoryRepository:
    """Database access for temporary working memory."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "WorkingMemoryRepository":
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

    def upsert(
        self,
        state_key: str,
        state_type: str,
        content: str,
        metadata: dict[str, object],
        expires_at: datetime | None,
    ) -> WorkingMemoryRecord:
        """Insert or update one working memory state."""
        with self._session_scope() as session:
            row = session.scalars(
                select(WorkingMemoryState).where(
                    WorkingMemoryState.state_key == state_key
                )
            ).first()
            if row is None:
                row = WorkingMemoryState(state_key=state_key, state_type=state_type)
                session.add(row)

            row.state_type = state_type
            row.content = content
            row.metadata_json = json.dumps(metadata, default=str)
            row.expires_at = expires_at
            session.flush()
            return self._to_record(row)

    def list_active(self, state_type: str | None = None) -> list[WorkingMemoryRecord]:
        """Return unexpired working memory states."""
        now = utc_now()
        statement = select(WorkingMemoryState).where(
            or_(
                WorkingMemoryState.expires_at.is_(None),
                WorkingMemoryState.expires_at > now,
            )
        )
        if state_type is not None:
            statement = statement.where(WorkingMemoryState.state_type == state_type)
        statement = statement.order_by(WorkingMemoryState.updated_at.desc())
        with self.session_factory() as session:
            return [self._to_record(row) for row in session.scalars(statement).all()]

    def clear_expired(self) -> int:
        """Delete expired working memory states."""
        now = utc_now()
        with self._session_scope() as session:
            rows = session.scalars(
                select(WorkingMemoryState).where(
                    WorkingMemoryState.expires_at.is_not(None),
                    WorkingMemoryState.expires_at <= now,
                )
            ).all()
            for row in rows:
                session.delete(row)
            return len(rows)

    def _to_record(self, row: WorkingMemoryState) -> WorkingMemoryRecord:
        try:
            metadata = json.loads(row.metadata_json or "{}")
        except json.JSONDecodeError:
            metadata = {}
        return WorkingMemoryRecord(
            id=row.id,
            state_key=row.state_key,
            state_type=row.state_type,
            content=row.content,
            metadata=metadata,
            expires_at=row.expires_at,
            updated_at=row.updated_at,
        )
