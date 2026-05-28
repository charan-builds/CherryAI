from datetime import date

from backend.behavioral_pattern_engine.repository import BehavioralPatternRepository
from backend.chat_session_manager.service import ChatSessionManager
from backend.context_retriever.service import ContextRetriever
from backend.daily_summary_engine.repository import DailySummaryRepository
from backend.daily_summary_engine.schemas import DailyProductivitySummary
from backend.memory_classifier.service import MemoryClassifier
from backend.memory_scoring_engine.service import MemoryScoringEngine
from backend.observer_engine.observer_state_manager.repository import (
    ObserverStateRepository,
)
from backend.semantic_memory_manager.service import SemanticMemoryManager
from backend.task_engine.service import TaskEngine
from database.init_db import initialize_database
from database.models import utc_now
from tests.helpers import make_test_settings


def test_context_retriever_collects_and_scores_relevant_context(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    task_engine = TaskEngine(settings=settings)
    task_engine.create_task("Study machine learning", priority="high")

    observer_repository = ObserverStateRepository.from_settings(settings)
    observer_repository.create_study_session("Machine learning", {}, utc_now())

    DailySummaryRepository.from_settings(settings).upsert(
        DailyProductivitySummary(
            summary_date=date.today(),
            productivity_score=60,
            consistency_score=40,
            focus_score=70,
            completed_tasks=1,
            open_tasks=1,
            study_duration_seconds=1800,
            focus_duration_seconds=1500,
            distraction_count=1,
            interruption_count=1,
            summary_text="Studied machine learning today.",
            focus_report="Focus was steady.",
            task_report="One task completed.",
            study_statistics={},
        )
    )

    BehavioralPatternRepository.from_settings(settings).upsert_pattern(
        pattern_type="preferred_study_time",
        pattern_key="hour_21",
        description="The user often studies ML at night.",
        confidence=0.8,
        sample_size=3,
        metadata={"hour": 21},
    )
    SemanticMemoryManager(
        settings=settings,
        classifier=MemoryClassifier(),
    ).remember("The user prefers studying machine learning at night.")

    chat_sessions = ChatSessionManager(settings=settings)
    session_id = chat_sessions.create_session()
    chat_sessions.record_interaction(
        session_id=session_id,
        user_prompt="Help me focus on ML.",
        ai_response="Start with one small topic.",
        detected_intent="general_chat",
    )

    retriever = ContextRetriever(
        settings=settings,
        scoring_engine=MemoryScoringEngine(),
    )
    context = retriever.retrieve("machine learning focus at night", session_id=session_id)
    sources = {scored.item.source for scored in context.items}

    assert "task" in sources
    assert "active_study_session" in sources
    assert "productivity_summary" in sources
    assert "behavioral_pattern" in sources
    assert "semantic_memory" in sources
    assert "ai_interaction" in sources
    assert context.items[0].score >= context.items[-1].score
