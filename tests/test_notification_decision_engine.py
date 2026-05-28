from dataclasses import replace
from datetime import datetime

from backend.notification_decision_engine.service import NotificationDecisionEngine
from backend.recommendation_engine.repository import RecommendationLogRepository
from backend.recommendation_engine.schemas import Recommendation
from database.init_db import initialize_database
from tests.helpers import make_test_settings


def test_notification_decision_delivers_once_then_suppresses_duplicate(tmp_path):
    settings = replace(
        make_test_settings(tmp_path),
        notification_quiet_mode_enabled=False,
        notification_global_cooldown_seconds=0,
    )
    initialize_database(settings)
    repository = RecommendationLogRepository.from_settings(settings)
    engine = NotificationDecisionEngine(settings=settings, repository=repository)
    now = datetime(2026, 5, 28, 12, 0)

    recommendation = repository.create_log(
        Recommendation(
            recommendation_type="resume_focus",
            title="Resume focus",
            message="Return to the task when ready.",
            priority="normal",
            cooldown_key="resume_focus",
        )
    )
    first = engine.evaluate(recommendation, now=now)

    duplicate = repository.create_log(
        Recommendation(
            recommendation_type="resume_focus",
            title="Resume focus",
            message="Return to the task when ready.",
            priority="normal",
            cooldown_key="resume_focus",
        )
    )
    second = engine.evaluate(duplicate, now=now)

    assert first.should_notify is True
    assert second.should_notify is False
    assert second.reason == "duplicate_suppressed"


def test_notification_decision_respects_quiet_mode_for_low_priority(tmp_path):
    settings = replace(
        make_test_settings(tmp_path),
        notification_quiet_mode_enabled=True,
        notification_quiet_hours_start="00:00",
        notification_quiet_hours_end="23:59",
    )
    initialize_database(settings)
    repository = RecommendationLogRepository.from_settings(settings)
    engine = NotificationDecisionEngine(settings=settings, repository=repository)
    recommendation = repository.create_log(
        Recommendation(
            recommendation_type="continue_task",
            title="Continue one task",
            message="Try ten minutes on one task.",
            priority="low",
            cooldown_key="continue_task",
        )
    )

    decision = engine.evaluate(recommendation, now=datetime(2026, 5, 28, 12, 0))

    assert decision.should_notify is False
    assert decision.reason == "quiet_mode"
