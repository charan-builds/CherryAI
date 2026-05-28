"""Context retrieval service."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config.settings import AppSettings
from backend.context_retriever.repository import ContextRetrieverRepository
from backend.context_retriever.schemas import ContextItem, RetrievedContext, ScoredContextItem
from backend.memory_scoring_engine.schemas import MemoryScoreInput
from backend.memory_scoring_engine.service import MemoryScoringEngine

logger = logging.getLogger(__name__)


@dataclass
class ContextRetriever:
    """Retrieves relevant tasks, study state, summaries, patterns, and interactions."""

    settings: AppSettings
    scoring_engine: MemoryScoringEngine
    repository: ContextRetrieverRepository | None = None

    def __post_init__(self) -> None:
        if self.repository is None:
            self.repository = ContextRetrieverRepository.from_settings(self.settings)

    def retrieve(
        self,
        query: str,
        session_id: str | None = None,
        limit: int | None = None,
    ) -> RetrievedContext:
        """Retrieve and rank relevant context for a prompt."""
        if not self.settings.memory_enabled:
            return RetrievedContext(query=query, items=[])

        candidates = self._collect_candidates(session_id)
        scored = [self._score_candidate(query, item) for item in candidates]
        scored.sort(key=lambda item: item.score, reverse=True)
        max_items = limit or (
            self.settings.memory_recent_task_limit
            + self.settings.memory_behavioral_pattern_limit
        )
        result = RetrievedContext(query=query, items=scored[:max(max_items, 1)])
        logger.debug("Retrieved %s context items", len(result.items))
        return result

    def _collect_candidates(self, session_id: str | None) -> list[ContextItem]:
        return [
            *self.repository.working_memory(self.settings.memory_recent_task_limit),
            *self.repository.active_study_context(),
            *self.repository.recent_tasks(self.settings.memory_recent_task_limit),
            *self.repository.productivity_summaries(
                self.settings.memory_productivity_summary_limit
            ),
            *self.repository.behavioral_patterns(
                self.settings.memory_behavioral_pattern_limit
            ),
            *self.repository.semantic_memories(
                self.settings.memory_behavioral_pattern_limit
            ),
            *self.repository.recent_ai_interactions(
                session_id=session_id,
                limit=self.settings.memory_recent_interaction_limit,
            ),
        ]

    def _score_candidate(self, query: str, item: ContextItem) -> ScoredContextItem:
        score = self.scoring_engine.score(
            MemoryScoreInput(
                content=f"{item.title} {item.content}",
                query=query,
                created_at=item.created_at,
                updated_at=item.updated_at,
                importance=item.importance,
                repetition_count=item.repetition_count,
                behavioral_significance=item.behavioral_significance,
                interaction_relevance=0.6 if item.source == "ai_interaction" else 0.0,
            )
        )
        return ScoredContextItem(item=item, score=score.score)
