"""Persistence for daily productivity summaries."""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from config.settings import AppSettings
from database.proactive_models import ProductivitySummary
from database.session import create_database_engine, create_session_factory
from backend.daily_summary_engine.schemas import DailyProductivitySummary


class DailySummaryRepository:
    """Upserts daily summary records by date."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "DailySummaryRepository":
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

    def upsert(self, summary: DailyProductivitySummary) -> DailyProductivitySummary:
        """Insert or update a daily productivity summary."""
        with self._session_scope() as session:
            statement = select(ProductivitySummary).where(
                ProductivitySummary.summary_date == summary.summary_date
            )
            row = session.scalars(statement).first()
            if row is None:
                row = ProductivitySummary(summary_date=summary.summary_date)
                session.add(row)

            row.productivity_score = summary.productivity_score
            row.consistency_score = summary.consistency_score
            row.focus_score = summary.focus_score
            row.completed_tasks = summary.completed_tasks
            row.open_tasks = summary.open_tasks
            row.study_duration_seconds = summary.study_duration_seconds
            row.focus_duration_seconds = summary.focus_duration_seconds
            row.distraction_count = summary.distraction_count
            row.interruption_count = summary.interruption_count
            row.summary_text = summary.summary_text
            row.focus_report = summary.focus_report
            row.task_report = summary.task_report
            row.study_statistics_json = json.dumps(summary.study_statistics, default=str)
            row.ai_insight = summary.ai_insight
            session.flush()
            return self._to_summary(row)

    def get_latest(self) -> DailyProductivitySummary | None:
        """Return the most recent summary."""
        statement = (
            select(ProductivitySummary)
            .order_by(ProductivitySummary.summary_date.desc())
            .limit(1)
        )
        with self.session_factory() as session:
            row = session.scalars(statement).first()
            if row is None:
                return None
            return self._to_summary(row)

    def count_summaries(self) -> int:
        """Count summaries for tests and diagnostics."""
        with self.session_factory() as session:
            return len(session.scalars(select(ProductivitySummary)).all())

    def _to_summary(self, row: ProductivitySummary) -> DailyProductivitySummary:
        try:
            statistics = json.loads(row.study_statistics_json or "{}")
        except json.JSONDecodeError:
            statistics = {}
        return DailyProductivitySummary(
            summary_date=row.summary_date,
            productivity_score=row.productivity_score,
            consistency_score=row.consistency_score,
            focus_score=row.focus_score,
            completed_tasks=row.completed_tasks,
            open_tasks=row.open_tasks,
            study_duration_seconds=row.study_duration_seconds,
            focus_duration_seconds=row.focus_duration_seconds,
            distraction_count=row.distraction_count,
            interruption_count=row.interruption_count,
            summary_text=row.summary_text,
            focus_report=row.focus_report,
            task_report=row.task_report,
            study_statistics=statistics,
            ai_insight=row.ai_insight,
        )
