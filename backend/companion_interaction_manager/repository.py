"""Repository for companion interactions."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from config.settings import AppSettings
from database.companion_models import CompanionInteractionLog
from database.session import create_database_engine, create_session_factory
from backend.companion_interaction_manager.schemas import CompanionMessage


class CompanionInteractionRepository:
    """Persists companion messages and cooldown history."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "CompanionInteractionRepository":
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

    def create(self, message: CompanionMessage) -> CompanionMessage:
        """Persist a companion message."""
        with self._session_scope() as session:
            row = CompanionInteractionLog(
                interaction_type=message.interaction_type,
                cooldown_key=message.cooldown_key,
                title=message.title,
                message=message.message,
                priority=message.priority,
                context_json=json.dumps(message.context, default=str),
                created_at=message.created_at,
            )
            session.add(row)
            session.flush()
            return self._to_message(row)

    def has_recent(self, cooldown_key: str, now: datetime, seconds: float) -> bool:
        """Return whether a cooldown key was recently emitted."""
        since = now - timedelta(seconds=max(seconds, 0.0))
        statement = select(CompanionInteractionLog).where(
            CompanionInteractionLog.cooldown_key == cooldown_key,
            CompanionInteractionLog.created_at >= since,
        )
        with self.session_factory() as session:
            return session.scalars(statement.limit(1)).first() is not None

    def recent(self, limit: int = 10) -> list[CompanionMessage]:
        """Return recent companion messages newest-first."""
        statement = (
            select(CompanionInteractionLog)
            .order_by(CompanionInteractionLog.created_at.desc())
            .limit(limit)
        )
        with self.session_factory() as session:
            return [self._to_message(row) for row in session.scalars(statement)]

    def count(self) -> int:
        """Count companion messages."""
        with self.session_factory() as session:
            return len(session.scalars(select(CompanionInteractionLog)).all())

    def _to_message(self, row: CompanionInteractionLog) -> CompanionMessage:
        try:
            context = json.loads(row.context_json or "{}")
        except json.JSONDecodeError:
            context = {}
        return CompanionMessage(
            id=row.id,
            interaction_type=row.interaction_type,
            cooldown_key=row.cooldown_key,
            title=row.title,
            message=row.message,
            priority=row.priority,
            context=context,
            created_at=row.created_at,
        )
