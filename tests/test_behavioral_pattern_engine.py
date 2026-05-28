from datetime import timedelta

from backend.behavioral_pattern_engine.service import BehavioralPatternEngine
from backend.observer_engine.observer_event_bus.events import DISTRACTION_DETECTED
from backend.observer_engine.observer_state_manager.repository import (
    ObserverStateRepository,
)
from database.init_db import initialize_database
from database.models import utc_now
from tests.helpers import make_test_settings


def test_behavioral_pattern_engine_learns_study_times_and_distraction_windows(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    observer_repository = ObserverStateRepository.from_settings(settings)
    started_at = utc_now().replace(hour=9, minute=0, second=0, microsecond=0)
    session = observer_repository.create_study_session("Calculus", {}, started_at)
    observer_repository.complete_study_session(
        session_id=session.id,
        ended_at=started_at + timedelta(minutes=45),
        focus_seconds=2100,
        idle_seconds=60,
        interruption_count=1,
    )
    observer_repository.record_event(
        DISTRACTION_DETECTED,
        {"keyword": "youtube"},
        started_at + timedelta(hours=3),
    )

    engine = BehavioralPatternEngine(settings=settings)
    insights = engine.learn_patterns(days=7)

    assert insights.preferred_study_times
    assert insights.productive_periods
    assert insights.distraction_windows
    assert insights.common_interruptions
