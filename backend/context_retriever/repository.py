"""Repository for memory context retrieval candidates."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import sessionmaker

from config.settings import AppSettings
from database.ai_models import AIInteraction
from database.memory_models import (
    ConsolidatedMemoryPattern,
    SemanticMemory,
    WorkingMemoryState,
)
from database.models import utc_now
from database.observer_models import StudySession
from database.proactive_models import BehavioralPattern, ProductivitySummary
from database.session import create_database_engine, create_session_factory
from database.task_models import Task
from backend.context_retriever.schemas import ContextItem


class ContextRetrieverRepository:
    """Reads context candidates from existing Cherry data stores."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "ContextRetrieverRepository":
        engine = create_database_engine(settings)
        return cls(create_session_factory(engine))

    def recent_tasks(self, limit: int) -> list[ContextItem]:
        """Return recent task context."""
        statement = select(Task).order_by(Task.created_at.desc()).limit(limit)
        with self.session_factory() as session:
            rows = session.scalars(statement).all()
            return [
                ContextItem(
                    source="task",
                    title=row.title,
                    content=self._task_content(row),
                    category="working" if row.status != "completed" else "episodic",
                    created_at=row.created_at,
                    updated_at=row.completed_at or row.created_at,
                    importance=0.7 if row.priority == "high" else 0.5,
                    metadata={"task_id": row.id, "status": row.status, "priority": row.priority},
                )
                for row in rows
            ]

    def active_study_context(self) -> list[ContextItem]:
        """Return active study session context."""
        statement = (
            select(StudySession)
            .where(StudySession.status == "active")
            .order_by(StudySession.started_at.desc())
            .limit(1)
        )
        with self.session_factory() as session:
            row = session.scalars(statement).first()
            if row is None:
                return []
            return [
                ContextItem(
                    source="active_study_session",
                    title=f"Studying {row.topic}",
                    content=f"Active study session on {row.topic}.",
                    category="working",
                    created_at=row.started_at,
                    updated_at=row.started_at,
                    importance=0.85,
                    metadata={"session_id": row.id, "topic": row.topic},
                )
            ]

    def productivity_summaries(self, limit: int) -> list[ContextItem]:
        """Return recent productivity summaries."""
        statement = (
            select(ProductivitySummary)
            .order_by(ProductivitySummary.summary_date.desc())
            .limit(limit)
        )
        with self.session_factory() as session:
            rows = session.scalars(statement).all()
            return [
                ContextItem(
                    source="productivity_summary",
                    title=f"Productivity summary {row.summary_date.isoformat()}",
                    content=f"{row.summary_text} {row.focus_report} {row.task_report}",
                    category="episodic",
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    importance=0.65,
                    behavioral_significance=min(row.distraction_count / 5, 1.0),
                    metadata={
                        "summary_date": row.summary_date.isoformat(),
                        "productivity_score": row.productivity_score,
                        "focus_score": row.focus_score,
                    },
                )
                for row in rows
            ]

    def behavioral_patterns(self, limit: int) -> list[ContextItem]:
        """Return learned behavioral and consolidated patterns."""
        items: list[ContextItem] = []
        with self.session_factory() as session:
            behavior_rows = session.scalars(
                select(BehavioralPattern)
                .order_by(BehavioralPattern.confidence.desc())
                .limit(limit)
            ).all()
            for row in behavior_rows:
                items.append(
                    ContextItem(
                        source="behavioral_pattern",
                        title=row.pattern_type.replace("_", " ").title(),
                        content=row.description,
                        category="behavioral",
                        created_at=row.first_seen_at,
                        updated_at=row.updated_at,
                        importance=0.65,
                        repetition_count=max(row.sample_size, 1),
                        behavioral_significance=row.confidence,
                        metadata=self._metadata(row.metadata_json),
                    )
                )

            consolidated_rows = session.scalars(
                select(ConsolidatedMemoryPattern)
                .order_by(ConsolidatedMemoryPattern.confidence.desc())
                .limit(limit)
            ).all()
            for row in consolidated_rows:
                items.append(
                    ContextItem(
                        source="consolidated_pattern",
                        title=row.title,
                        content=row.insight,
                        category="behavioral",
                        created_at=row.created_at,
                        updated_at=row.updated_at,
                        importance=0.75,
                        repetition_count=max(row.evidence_count, 1),
                        behavioral_significance=row.confidence,
                        metadata=self._metadata(row.metadata_json),
                    )
                )
        return items[:limit]

    def semantic_memories(self, limit: int) -> list[ContextItem]:
        """Return durable semantic memories."""
        statement = (
            select(SemanticMemory)
            .order_by(
                SemanticMemory.importance.desc(),
                SemanticMemory.last_reinforced_at.desc(),
            )
            .limit(limit)
        )
        with self.session_factory() as session:
            rows = session.scalars(statement).all()
            return [
                ContextItem(
                    source="semantic_memory",
                    title=row.title,
                    content=row.content,
                    category=row.category,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    importance=row.importance,
                    repetition_count=row.repetition_count,
                    behavioral_significance=row.behavioral_significance,
                    metadata=self._metadata(row.metadata_json),
                )
                for row in rows
            ]

    def working_memory(self, limit: int) -> list[ContextItem]:
        """Return active working memory states."""
        now = utc_now()
        statement = (
            select(WorkingMemoryState)
            .where(
                or_(
                    WorkingMemoryState.expires_at.is_(None),
                    WorkingMemoryState.expires_at > now,
                )
            )
            .order_by(WorkingMemoryState.updated_at.desc())
            .limit(limit)
        )
        with self.session_factory() as session:
            rows = session.scalars(statement).all()
            return [
                ContextItem(
                    source="working_memory",
                    title=row.state_type.replace("_", " ").title(),
                    content=row.content,
                    category="working",
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    importance=0.8,
                    metadata=self._metadata(row.metadata_json),
                )
                for row in rows
            ]

    def recent_ai_interactions(
        self,
        session_id: str | None,
        limit: int,
    ) -> list[ContextItem]:
        """Return recent AI interactions, scoped to a session when available."""
        statement = select(AIInteraction).order_by(AIInteraction.created_at.desc()).limit(limit)
        if session_id:
            statement = statement.where(AIInteraction.session_id == session_id)
        with self.session_factory() as session:
            rows = session.scalars(statement).all()
            return [
                ContextItem(
                    source="ai_interaction",
                    title=f"Recent {row.detected_intent}",
                    content=f"User: {row.user_prompt} Cherry AI: {row.ai_response}",
                    category="episodic",
                    created_at=row.created_at,
                    updated_at=row.created_at,
                    importance=0.45,
                    metadata={"interaction_id": row.id, "intent": row.detected_intent},
                )
                for row in rows
            ]

    def _task_content(self, row: Task) -> str:
        description = f" Description: {row.description}" if row.description else ""
        return f"Task {row.title} is {row.status} with {row.priority} priority.{description}"

    def _metadata(self, raw_json: str) -> dict[str, object]:
        try:
            value = json.loads(raw_json or "{}")
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}
