from datetime import timedelta

from backend.focus_scoring_engine.schemas import FocusScoreInput
from backend.focus_scoring_engine.service import FocusScoringEngine
from backend.observer_engine.observer_event_bus.events import DISTRACTION_DETECTED
from backend.observer_engine.observer_state_manager.repository import (
    ObserverStateRepository,
)
from backend.productivity_analyzer.service import ProductivityAnalyzer
from backend.task_engine.service import TaskEngine
from database.init_db import initialize_database
from database.models import utc_now
from tests.helpers import make_test_settings


def test_focus_scoring_calculates_quality_metrics(tmp_path):
    settings = make_test_settings(tmp_path)
    engine = FocusScoringEngine(settings=settings)

    result = engine.score(
        FocusScoreInput(
            session_duration_seconds=3600,
            focus_duration_seconds=2700,
            idle_seconds=120,
            interruption_count=2,
            distraction_count=1,
        )
    )

    assert result.focus_duration_seconds == 2700
    assert result.interruption_rate == 2.0
    assert 0 < result.distraction_severity < 100
    assert 0 < result.session_quality <= 100
    assert 0 < result.focus_score <= 100


def test_productivity_analyzer_combines_tasks_study_and_distractions(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    task_engine = TaskEngine(settings=settings)
    task = task_engine.create_task("Study NumPy")
    task_engine.complete_task(task.id)

    repository = ObserverStateRepository.from_settings(settings)
    started_at = utc_now() - timedelta(minutes=40)
    session = repository.create_study_session("NumPy", {}, started_at)
    repository.complete_study_session(
        session_id=session.id,
        ended_at=started_at + timedelta(minutes=40),
        focus_seconds=1800,
        idle_seconds=120,
        interruption_count=2,
    )
    repository.record_event(
        DISTRACTION_DETECTED,
        {"application_name": "YouTube.exe"},
        utc_now(),
    )

    analyzer = ProductivityAnalyzer(
        settings=settings,
        focus_scoring_engine=FocusScoringEngine(settings=settings),
    )
    analysis = analyzer.analyze_today()

    assert analysis.completed_tasks == 1
    assert analysis.study_duration_seconds == 2400
    assert analysis.focus_duration_seconds == 1800
    assert analysis.distraction_count == 1
    assert analysis.productivity_score > 0
