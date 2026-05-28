from datetime import timedelta

from backend.observer_engine.schemas import ObserverStatus
from backend.productivity_analyzer.schemas import ProductivityAnalysis
from backend.recommendation_engine.repository import RecommendationLogRepository
from backend.recommendation_engine.schemas import RECOMMENDATION_START_STUDY
from backend.recommendation_engine.service import RecommendationEngine
from database.init_db import initialize_database
from database.models import utc_now
from tests.helpers import make_test_settings


def test_recommendation_engine_generates_contextual_cooldown_aware_suggestions(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    repository = RecommendationLogRepository.from_settings(settings)
    engine = RecommendationEngine(settings=settings, repository=repository)
    now = utc_now()

    status = ObserverStatus(
        active_app="Code.exe",
        window_title="Cherry AI",
        idle_seconds=0,
        is_idle=False,
        app_switch_count=0,
        distraction_count=0,
        focus_seconds=0,
        current_focus_seconds=0,
        active_study_session=None,
    )
    analysis = ProductivityAnalysis(
        analysis_date=now.date(),
        created_tasks=0,
        completed_tasks=0,
        open_tasks=2,
        study_duration_seconds=0,
        focus_duration_seconds=0,
        idle_seconds=0,
        productivity_score=20,
        consistency_score=0,
        focus_score=0,
    )

    first = engine.generate(status=status, analysis=analysis, now=now)
    second = engine.generate(status=status, analysis=analysis, now=now + timedelta(minutes=1))

    assert any(item.recommendation_type == RECOMMENDATION_START_STUDY for item in first)
    assert second == []
    assert repository.count_logs("generated") == len(first)
