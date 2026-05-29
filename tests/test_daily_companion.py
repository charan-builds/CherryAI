import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from backend.companion_interaction_manager.schemas import CompanionMessage
from backend.workspace_preparation_engine.service import WorkspacePreparationEngine
from database.init_db import initialize_database
from frontend.companion.companion_panels import DailyBriefingPanel
from backend.service_registry import build_services
from tests.helpers import make_test_settings


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_startup_briefing_generation(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    services = build_services(settings)
    services.tasks.create_task("Probability Revision", priority="high")
    services.tasks.create_task("Kaggle Practice")

    briefing = services.startup_briefings.generate()

    assert settings.user_display_name in briefing.greeting
    assert "Probability Revision" in briefing.pending_tasks
    assert briefing.suggested_first_action


def test_daily_reflection_generation(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    services = build_services(settings)
    task = services.tasks.create_task("Finish notes")
    services.tasks.complete_task(task.id)

    reflection = services.daily_reflections.generate()

    assert reflection.completed_tasks == 1
    assert reflection.study_duration_minutes >= 0
    assert "1 task" in reflection.summary_text


def test_contextual_recommendations(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    services = build_services(settings)
    services.tasks.create_task("ML practice")

    recommendations = services.contextual_recommendations.generate()

    assert recommendations
    assert "task" in recommendations[0].message.lower()


def test_workspace_preparation_workflow(tmp_path):
    settings = make_test_settings(tmp_path)
    engine = WorkspacePreparationEngine(settings=settings)

    workspace = engine.get_workspace("ml_study")

    assert workspace.name == "ML Study Workspace"
    assert "Open VS Code" in workspace.steps
    assert workspace.workflow_plan.steps[-1].name == "Enable Study Mode"


def test_companion_interactions(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    services = build_services(settings)

    decision = services.companion_interactions.coaching_nudge(
        "Tiny restart",
        "Open one task and work for ten minutes.",
        "tiny_restart",
    )

    assert decision.should_emit is True
    assert decision.message is not None
    assert "ten minutes" in decision.message.message


def test_timeline_generation(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    services = build_services(settings)

    services.daily_timeline.record_task_completed("Probability Revision", "task-1")
    timeline = services.daily_timeline.generate_for_day()

    assert timeline.item_count == 1
    assert timeline.items[0].entry_type == "task_completed"


def test_companion_cooldowns(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    services = build_services(settings)
    message = CompanionMessage(
        interaction_type="coaching",
        title="Focus",
        message="Return to the next small step.",
        cooldown_key="focus_nudge",
    )

    first = services.companion_interactions.maybe_emit(message, cooldown_seconds=3600)
    second = services.companion_interactions.maybe_emit(message, cooldown_seconds=3600)

    assert first.should_emit is True
    assert second.should_emit is False
    assert services.companion_interactions.repository.count() == 1


def test_briefing_ui_rendering(tmp_path):
    app = _app()
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    services = build_services(settings)
    services.tasks.create_task("Probability Revision")
    panel = DailyBriefingPanel()

    panel.update_briefing(services.startup_briefings.generate())
    app.processEvents()

    assert "Good" in panel.greeting_label.text()
    assert "Probability Revision" in panel.detail_label.text()
