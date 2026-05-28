"""Recommendation log repository."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from config.settings import AppSettings
from database.models import utc_now
from database.proactive_models import RecommendationLog
from database.session import create_database_engine, create_session_factory
from backend.recommendation_engine.schemas import Recommendation


class RecommendationLogRepository:
    """Persists recommendation generation and delivery decisions."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "RecommendationLogRepository":
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

    def create_log(
        self,
        recommendation: Recommendation,
        status: str = "generated",
        suppression_reason: str = "",
    ) -> Recommendation:
        """Persist a recommendation log row and return a copy with id."""
        now = recommendation.created_at or utc_now()
        with self._session_scope() as session:
            log = RecommendationLog(
                recommendation_type=recommendation.recommendation_type,
                cooldown_key=recommendation.cooldown_key,
                title=recommendation.title,
                message=recommendation.message,
                priority=recommendation.priority,
                context_json=json.dumps(recommendation.context, default=str),
                status=status,
                suppression_reason=suppression_reason,
                created_at=now,
            )
            session.add(log)
            session.flush()
            return Recommendation(
                id=log.id,
                created_at=log.created_at,
                recommendation_type=recommendation.recommendation_type,
                title=recommendation.title,
                message=recommendation.message,
                priority=recommendation.priority,
                cooldown_key=recommendation.cooldown_key,
                context=recommendation.context,
            )

    def mark_status(
        self,
        recommendation_id: str,
        status: str,
        suppression_reason: str = "",
        delivered_at: datetime | None = None,
    ) -> None:
        """Update recommendation delivery status."""
        with self._session_scope() as session:
            log = session.get(RecommendationLog, recommendation_id)
            if log is None:
                return
            log.status = status
            log.suppression_reason = suppression_reason
            if delivered_at is not None:
                log.delivered_at = delivered_at

    def has_recent(
        self,
        cooldown_key: str,
        now: datetime,
        seconds: float,
        statuses: tuple[str, ...] | None = None,
    ) -> bool:
        """Return whether a matching log exists inside a cooldown window."""
        since = now - timedelta(seconds=max(seconds, 0.0))
        statement = select(RecommendationLog).where(
            RecommendationLog.cooldown_key == cooldown_key,
            RecommendationLog.created_at >= since,
        )
        if statuses is not None:
            statement = statement.where(RecommendationLog.status.in_(statuses))
        with self.session_factory() as session:
            return session.scalars(statement.limit(1)).first() is not None

    def has_any_recent_delivery(self, now: datetime, seconds: float) -> bool:
        """Return whether any notification was recently delivered."""
        since = now - timedelta(seconds=max(seconds, 0.0))
        statement = select(RecommendationLog).where(
            RecommendationLog.status == "delivered",
            RecommendationLog.delivered_at >= since,
        )
        with self.session_factory() as session:
            return session.scalars(statement.limit(1)).first() is not None

    def count_logs(self, status: str | None = None) -> int:
        """Count recommendation logs for tests and diagnostics."""
        statement = select(RecommendationLog)
        if status is not None:
            statement = statement.where(RecommendationLog.status == status)
        with self.session_factory() as session:
            return len(session.scalars(statement).all())
