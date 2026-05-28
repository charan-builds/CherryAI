import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from backend.task_engine.constants import TASK_STATUS_COMPLETED
from backend.task_engine.service import TaskEngine
from database.init_db import initialize_database
from frontend.tasks.tasks_page import TasksPage
from tests.helpers import make_test_settings


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_tasks_page_create_complete_and_filter_smoke(tmp_path):
    app = _app()
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    task_engine = TaskEngine(settings=settings)
    page = TasksPage(task_engine=task_engine)

    page.form.title_input.setText("Review local task UI")
    page.form.description_input.setPlainText("Use the widget flow.")
    page.form.priority_combo.setCurrentText("High")
    page.form.create_button.click()
    app.processEvents()

    all_tasks = task_engine.list_tasks(status_filter="all")
    assert len(all_tasks) == 1
    assert len(page.task_cards) == 1

    page.task_cards[0].complete_checkbox.click()
    app.processEvents()

    completed_task = task_engine.get_task(all_tasks[0].id)
    assert completed_task.status == TASK_STATUS_COMPLETED

    page.filter_bar.status_filter.setCurrentText("Completed")
    page.refresh_tasks()
    app.processEvents()

    assert len(page.task_cards) == 1
