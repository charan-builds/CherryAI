import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from backend.ai_engine.service import AIEngine
from backend.ollama_service.service import OllamaService
from backend.service_registry import build_services
from database.init_db import initialize_database
from frontend.windows.main_window import MainWindow
from tests.helpers import make_test_settings


class DashboardFakeOllama(OllamaService):
    def generate(self, prompt, system_prompt="", model=None):
        if "Extract the user's intent as JSON only" in prompt:
            return '{"intent":"create_task","title":"study numpy","priority":"normal"}'
        return "Dashboard response"


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_dashboard_chat_worker_creates_task_smoke(tmp_path):
    app = _app()
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    services = build_services(settings)
    services.ai = AIEngine(
        settings=settings,
        task_engine=services.tasks,
        ollama_service=DashboardFakeOllama(settings),
    )
    window = MainWindow(settings=settings, services=services)

    window._handle_prompt("Add task study numpy")

    deadline = time.time() + 5
    while window.chat_workers and time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)

    app.processEvents()

    assert not window.chat_workers
    assert len(services.tasks.list_tasks(status_filter="all")) == 1
    assert len(services.ai.chat_sessions.get_recent_history(window.chat_session_id)) == 1
