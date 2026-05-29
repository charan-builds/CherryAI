"""Repository for daily timeline entries."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import date, datetime
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from config.settings import AppSettings
from database.companion_models import DailyTimelineEntry
from database.session import create_database_engine, create_session_factory
from backend.daily_timeline_manager.schemas import TimelineItem


class DailyTimelineRepository:
    """Database access for persisted daily timeline items."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "DailyTimelineRepository":
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

    def create(self, item: TimelineItem) -> TimelineItem:
        """Persist one timeline item."""
        with self._session_scope() as session:
            row = DailyTimelineEntry(
                entry_date=item.started_at.date(),
                entry_type=item.entry_type,
                title=item.title,
                description=item.description,
                source_id=item.source_id,
                metadata_json=json.dumps(item.metadata, default=str),
                started_at=item.started_at,
                ended_at=item.ended_at,
            )
            session.add(row)
            session.flush()
            return self._to_item(row)

    def list_for_day(self, day: date) -> list[TimelineItem]:
        """Return timeline items for a day in chronological order."""
        statement = (
            select(DailyTimelineEntry)
            .where(DailyTimelineEntry.entry_date == day)
            .order_by(DailyTimelineEntry.started_at.asc())
        )
        with self.session_factory() as session:
            return [self._to_item(row) for row in session.scalars(statement)]

    def count(self) -> int:
        """Count timeline entries."""
        with self.session_factory() as session:
            return len(session.scalars(select(DailyTimelineEntry)).all())

    def _to_item(self, row: DailyTimelineEntry) -> TimelineItem:
        try:
            metadata = json.loads(row.metadata_json or "{}")
        except json.JSONDecodeError:
            metadata = {}
        return TimelineItem(
            id=row.id,
            entry_type=row.entry_type,
            title=row.title,
            description=row.description,
            source_id=row.source_id,
            metadata=metadata,
            started_at=row.started_at,
            ended_at=row.ended_at,
        )
