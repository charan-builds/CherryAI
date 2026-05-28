from datetime import timedelta

from backend.observer_engine.observer_event_bus.events import (
    APP_CHANGED,
    DISTRACTION_DETECTED,
    STUDY_COMPLETED,
    STUDY_STARTED,
    ObserverEvent,
)
from backend.observer_engine.observer_event_bus.service import ObserverEventBus
from backend.observer_engine.observer_state_manager.repository import (
    ObserverStateRepository,
)
from backend.observer_engine.service import ObserverEngine
from backend.observer_engine.schemas import WindowSnapshot
from database.init_db import initialize_database
from database.models import utc_now
from tests.helpers import make_test_settings


class FakeWindowProvider:
    def __init__(self, snapshots):
        self.snapshots = list(snapshots)
        self.index = 0

    def get_active_window(self):
        snapshot = self.snapshots[min(self.index, len(self.snapshots) - 1)]
        self.index += 1
        return snapshot


class FakeIdleProvider:
    def __init__(self, values):
        self.values = list(values)
        self.index = 0

    def get_idle_seconds(self):
        value = self.values[min(self.index, len(self.values) - 1)]
        self.index += 1
        return value


def test_observer_event_bus_dispatches_events():
    bus = ObserverEventBus()
    received = []

    bus.subscribe(APP_CHANGED, received.append)
    event = ObserverEvent(APP_CHANGED, {"application_name": "Code.exe"})
    bus.publish(event)

    assert received == [event]


def test_observer_persists_activity_and_events(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    repository = ObserverStateRepository.from_settings(settings)
    started_at = utc_now()

    activity_id = repository.start_activity("Code.exe", "Cherry AI", started_at)
    repository.end_activity(activity_id, started_at + timedelta(seconds=12))
    repository.record_event(APP_CHANGED, {"application_name": "Code.exe"}, utc_now())

    assert repository.count_activity_logs() == 1
    assert repository.count_events(APP_CHANGED) == 1


def test_observer_engine_tracks_app_changes_and_distractions(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    now = utc_now()
    window_provider = FakeWindowProvider(
        [
            WindowSnapshot("Code.exe", "Cherry AI", now),
            WindowSnapshot("YouTube.exe", "Study break", now + timedelta(seconds=5)),
        ]
    )
    idle_provider = FakeIdleProvider([0, 0])
    engine = ObserverEngine(
        settings=settings,
        active_window_provider=window_provider,
        idle_provider=idle_provider,
    )

    engine.start_study_session("NumPy")
    engine.sample_once()
    status = engine.sample_once()

    assert status.active_app == "YouTube.exe"
    assert status.distraction_count == 1
    assert status.app_switch_count == 1
    assert engine.state_manager.repository.count_events(DISTRACTION_DETECTED) == 1


def test_study_session_workflow_persists_events(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    now = utc_now()
    engine = ObserverEngine(
        settings=settings,
        active_window_provider=FakeWindowProvider(
            [WindowSnapshot("Code.exe", "Cherry AI", now)]
        ),
        idle_provider=FakeIdleProvider([0]),
    )

    started = engine.start_study_session("Linear algebra")
    engine.sample_once()
    completed = engine.stop_study_session()

    assert started.status == "active"
    assert completed is not None
    assert completed.status == "completed"
    assert engine.state_manager.repository.count_events(STUDY_STARTED) == 1
    assert engine.state_manager.repository.count_events(STUDY_COMPLETED) == 1
