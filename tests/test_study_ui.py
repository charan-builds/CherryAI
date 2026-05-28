import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import timedelta

from PyQt6.QtWidgets import QApplication

from backend.observer_engine.schemas import WindowSnapshot
from backend.observer_engine.service import ObserverEngine
from database.init_db import initialize_database
from database.models import utc_now
from frontend.study.study_page import StudyModePage
from tests.helpers import make_test_settings
from tests.test_observer_engine import FakeIdleProvider, FakeWindowProvider


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_study_page_start_stop_smoke(tmp_path):
    app = _app()
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    now = utc_now()
    engine = ObserverEngine(
        settings=settings,
        active_window_provider=FakeWindowProvider(
            [
                WindowSnapshot("Code.exe", "Cherry AI", now),
                WindowSnapshot("Code.exe", "Cherry AI", now + timedelta(seconds=2)),
            ]
        ),
        idle_provider=FakeIdleProvider([0, 0]),
    )
    page = StudyModePage(observer_engine=engine)

    page.topic_input.setText("NumPy")
    page.start_button.click()
    engine.sample_once()
    page.update_status(engine.get_status())
    app.processEvents()

    assert "NumPy" in page.session_status_label.text()

    page.stop_button.click()
    app.processEvents()

    assert "No active" in page.session_status_label.text()
