from datetime import timedelta

from backend.daily_summary_engine.repository import DailySummaryRepository
from backend.daily_summary_engine.service import DailySummaryEngine
from backend.focus_scoring_engine.service import FocusScoringEngine
from backend.observer_engine.observer_state_manager.repository import (
    ObserverStateRepository,
)
from backend.productivity_analyzer.service import ProductivityAnalyzer
from backend.task_engine.service import TaskEngine
from database.init_db import initialize_database
from database.models import utc_now
from tests.helpers import make_test_settings


def test_daily_summary_engine_persists_task_focus_and_study_report(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    task_engine = TaskEngine(settings=settings)
    task = task_engine.create_task("Finish chapter")
    task_engine.complete_task(task.id)

    observer_repository = ObserverStateRepository.from_settings(settings)
    started_at = utc_now() - timedelta(minutes=25)
    session = observer_repository.create_study_session("Chapter 4", {}, started_at)
    observer_repository.complete_study_session(
        session_id=session.id,
        ended_at=started_at + timedelta(minutes=25),
        focus_seconds=1200,
        idle_seconds=60,
        interruption_count=1,
    )

    analyzer = ProductivityAnalyzer(
        settings=settings,
        focus_scoring_engine=FocusScoringEngine(settings=settings),
    )
    repository = DailySummaryRepository.from_settings(settings)
    engine = DailySummaryEngine(
        settings=settings,
        productivity_analyzer=analyzer,
        repository=repository,
    )

    summary = engine.generate_today()

    assert summary.completed_tasks == 1
    assert "Productivity score" in summary.summary_text
    assert "Focus score" in summary.focus_report
    assert repository.count_summaries() == 1
