"""Reusable deterministic memory scoring."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime

from database.models import utc_now
from backend.memory_scoring_engine.schemas import MemoryScoreInput, MemoryScoreResult


@dataclass
class MemoryScoringEngine:
    """Scores memories using relevance, recency, importance, and repetition."""

    recency_half_life_days: float = 14.0

    def score(self, score_input: MemoryScoreInput) -> MemoryScoreResult:
        """Return a deterministic 0-100 score for a memory candidate."""
        relevance = self._text_relevance(score_input.content, score_input.query)
        recency = self._recency_score(score_input.updated_at or score_input.created_at)
        importance = self._clamp(score_input.importance) * 100.0
        repetition = self._repetition_score(score_input.repetition_count)
        behavioral = self._clamp(score_input.behavioral_significance) * 100.0
        interaction = self._clamp(score_input.interaction_relevance) * 100.0

        final_score = (
            relevance * 0.3
            + recency * 0.2
            + importance * 0.2
            + repetition * 0.1
            + behavioral * 0.15
            + interaction * 0.05
        )
        return MemoryScoreResult(
            score=round(final_score, 2),
            relevance_score=round(relevance, 2),
            recency_score=round(recency, 2),
            importance_score=round(importance, 2),
            repetition_score=round(repetition, 2),
            behavioral_score=round(behavioral, 2),
            interaction_score=round(interaction, 2),
        )

    def _text_relevance(self, content: str, query: str) -> float:
        content_tokens = self._tokens(content)
        query_tokens = self._tokens(query)
        if not query_tokens:
            return 35.0
        if not content_tokens:
            return 0.0
        overlap = content_tokens.intersection(query_tokens)
        return min((len(overlap) / len(query_tokens)) * 100.0, 100.0)

    def _recency_score(self, value: datetime) -> float:
        now = utc_now()
        value = self._align_datetime(value, now)
        age_days = max((now - value).total_seconds() / 86400, 0.0)
        if age_days == 0:
            return 100.0
        decay = math.pow(0.5, age_days / max(self.recency_half_life_days, 1.0))
        return min(decay * 100.0, 100.0)

    def _repetition_score(self, repetition_count: int) -> float:
        count = max(repetition_count, 0)
        return min(math.log1p(count) / math.log1p(10) * 100.0, 100.0)

    def _tokens(self, value: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9]+", value.lower())
            if len(token) > 2
        }

    def _clamp(self, value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
        return max(min(value, maximum), minimum)

    def _align_datetime(self, value: datetime, reference: datetime) -> datetime:
        if value.tzinfo is None and reference.tzinfo is not None:
            return value.replace(tzinfo=reference.tzinfo)
        if value.tzinfo is not None and reference.tzinfo is None:
            return value.replace(tzinfo=None)
        return value
