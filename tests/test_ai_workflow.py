from backend.ai_engine.service import AIEngine
from backend.ollama_service.service import OllamaService
from backend.task_engine.service import TaskEngine
from database.init_db import initialize_database
from tests.helpers import make_test_settings


class WorkflowFakeOllama(OllamaService):
    def __init__(self, settings):
        super().__init__(settings)

    def check_connectivity(self):
        return True

    def generate(self, prompt, system_prompt="", model=None):
        if "Extract the user's intent as JSON only" in prompt:
            return '{"intent":"create_task","title":"study numpy","priority":"normal"}'
        return "Local conversational response"


def test_ai_workflow_creates_task_and_persists_interaction(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    task_engine = TaskEngine(settings=settings)
    ai_engine = AIEngine(
        settings=settings,
        task_engine=task_engine,
        ollama_service=WorkflowFakeOllama(settings),
    )

    session_id = ai_engine.start_session()
    result = ai_engine.handle_message("Add task study numpy", session_id=session_id)
    history = ai_engine.chat_sessions.get_recent_history(session_id)

    assert result.success is True
    assert result.detected_intent == "create_task"
    assert "study numpy" in result.response_text
    assert len(task_engine.list_tasks(status_filter="all")) == 1
    assert len(history) == 1
    assert history[0].detected_intent == "create_task"
