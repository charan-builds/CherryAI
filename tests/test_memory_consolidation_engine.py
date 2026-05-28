from datetime import timedelta

from backend.memory_classifier.service import MemoryClassifier
from backend.memory_consolidation_engine.service import MemoryConsolidationEngine
from backend.observer_engine.observer_event_bus.events import DISTRACTION_DETECTED
from backend.observer_engine.observer_state_manager.repository import (
    ObserverStateRepository,
)
from backend.semantic_memory_manager.service import SemanticMemoryManager
from database.init_db import initialize_database
from database.models import utc_now
from tests.helpers import make_test_settings


def test_memory_consolidation_creates_patterns_and_semantic_memories(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    observer_repository = ObserverStateRepository.from_settings(settings)
    started_at = utc_now() - timedelta(hours=2)
    session = observer_repository.create_study_session("ML", {}, started_at)
    observer_repository.complete_study_session(
        session_id=session.id,
        ended_at=started_at + timedelta(minutes=45),
        focus_seconds=2100,
        idle_seconds=0,
        interruption_count=1,
    )
    observer_repository.record_event(
        DISTRACTION_DETECTED,
        {"keyword": "youtube"},
        started_at + timedelta(minutes=10),
    )

    semantic_manager = SemanticMemoryManager(
        settings=settings,
        classifier=MemoryClassifier(),
    )
    engine = MemoryConsolidationEngine(
        settings=settings,
        semantic_memory_manager=semantic_manager,
    )

    result = engine.consolidate(days=7)

    assert result.patterns
    assert result.semantic_memories_created > 0
    assert semantic_manager.repository.count() > 0
