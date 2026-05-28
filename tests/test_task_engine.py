import pytest

from backend.task_engine.constants import (
    TASK_PRIORITY_HIGH,
    TASK_PRIORITY_LOW,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_PENDING,
)
from backend.task_engine.repository import TaskNotFoundError
from backend.task_engine.service import TaskEngine
from database.init_db import initialize_database
from tests.helpers import make_test_settings


def test_task_crud_workflow(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    tasks = TaskEngine(settings=settings)

    created = tasks.create_task(
        title="Draft Cherry AI task plan",
        description="Prepare first productivity workflow.",
        priority=TASK_PRIORITY_HIGH,
    )

    assert created.id
    assert created.status == TASK_STATUS_PENDING
    assert created.priority == TASK_PRIORITY_HIGH

    updated = tasks.update_task(
        task_id=created.id,
        title="Draft task plan",
        description="Shorter description.",
        priority=TASK_PRIORITY_LOW,
    )

    assert updated.title == "Draft task plan"
    assert updated.priority == TASK_PRIORITY_LOW

    completed = tasks.complete_task(created.id)

    assert completed.status == TASK_STATUS_COMPLETED
    assert completed.completed_at is not None

    reopened = tasks.reopen_task(created.id)

    assert reopened.status == TASK_STATUS_PENDING
    assert reopened.completed_at is None

    tasks.delete_task(created.id)

    with pytest.raises(TaskNotFoundError):
        tasks.get_task(created.id)


def test_task_persistence_across_service_instances(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)

    first_service = TaskEngine(settings=settings)
    created = first_service.create_task("Persisted task", priority=TASK_PRIORITY_HIGH)

    second_service = TaskEngine(settings=settings)
    persisted = second_service.get_task(created.id)

    assert persisted.title == "Persisted task"
    assert persisted.priority == TASK_PRIORITY_HIGH


def test_task_filters_statistics_and_daily_summary(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    tasks = TaskEngine(settings=settings)

    high = tasks.create_task("High priority", priority=TASK_PRIORITY_HIGH)
    tasks.create_task("Low priority", priority=TASK_PRIORITY_LOW)
    tasks.complete_task(high.id)

    completed = tasks.list_tasks(status_filter="completed")
    high_priority = tasks.list_tasks(status_filter="all", priority_filter="high")
    statistics = tasks.get_statistics()
    daily_summary = tasks.generate_daily_summary()

    assert len(completed) == 1
    assert len(high_priority) == 1
    assert statistics.total == 2
    assert statistics.completed_count == 1
    assert statistics.completed_today == 1
    assert daily_summary.created_today == 2
    assert daily_summary.completed_today == 1
    assert "Today:" in daily_summary.summary_text
