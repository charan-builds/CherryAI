from backend.action_router.service import ActionRouter
from backend.intent_parser.schemas import ParsedIntent
from backend.task_engine.service import TaskEngine
from database.init_db import initialize_database
from tests.helpers import make_test_settings


def test_action_router_creates_task(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    task_engine = TaskEngine(settings=settings)
    router = ActionRouter(task_engine=task_engine)

    result = router.route(
        ParsedIntent(intent="create_task", title="study numpy", priority="normal")
    )

    assert result.success is True
    assert len(task_engine.list_tasks(status_filter="all")) == 1


def test_action_router_summarizes_tasks(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    task_engine = TaskEngine(settings=settings)
    task_engine.create_task("study numpy")
    router = ActionRouter(task_engine=task_engine)

    result = router.route(ParsedIntent(intent="summarize_tasks"))

    assert result.success is True
    assert "statistics" in result.data
    assert "summary" in result.data
