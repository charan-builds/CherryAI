from datetime import timedelta

from database.models import utc_now
from backend.memory_scoring_engine.schemas import MemoryScoreInput
from backend.memory_scoring_engine.service import MemoryScoringEngine


def test_memory_scoring_prefers_relevant_recent_important_memory():
    engine = MemoryScoringEngine()
    now = utc_now()

    strong = engine.score(
        MemoryScoreInput(
            content="The user studies machine learning at night with strong focus.",
            query="machine learning focus",
            created_at=now,
            importance=0.9,
            repetition_count=4,
            behavioral_significance=0.7,
        )
    )
    weak = engine.score(
        MemoryScoreInput(
            content="The user once opened a music app.",
            query="machine learning focus",
            created_at=now - timedelta(days=90),
            importance=0.2,
            repetition_count=1,
            behavioral_significance=0.0,
        )
    )

    assert strong.score > weak.score
    assert strong.relevance_score > weak.relevance_score
