"""Repository for persisted AI interactions."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from config.settings import AppSettings
from database.ai_models import AIInteraction
from database.session import create_database_engine, create_session_factory
from backend.chat_session_manager.schemas import AIInteractionRecord


class AIInteractionRepository:
    """Database access for AI interaction history."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "AIInteractionRepository":
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

    def create(
        self,
        session_id: str,
        user_prompt: str,
        ai_response: str,
        detected_intent: str,
    ) -> AIInteractionRecord:
        """Persist one AI interaction."""
        with self._session_scope() as session:
            interaction = AIInteraction(
                session_id=session_id,
                user_prompt=user_prompt,
                ai_response=ai_response,
                detected_intent=detected_intent,
            )
            session.add(interaction)
            session.flush()
            return AIInteractionRecord.from_model(interaction)

    def list_recent(
        self,
        session_id: str,
        limit: int = 10,
    ) -> list[AIInteractionRecord]:
        """Return recent interaction records oldest-first."""
        statement = (
            select(AIInteraction)
            .where(AIInteraction.session_id == session_id)
            .order_by(AIInteraction.created_at.desc())
            .limit(limit)
        )
        with self.session_factory() as session:
            rows = session.scalars(statement).all()
            records = [AIInteractionRecord.from_model(row) for row in rows]
            return list(reversed(records))
