from backend.application_state_manager.service import ApplicationStateManager
from backend.centralized_event_bus.schemas import (
    EVENT_CATEGORY_WORKFLOW,
    EventFilter,
    PlatformEvent,
)
from backend.centralized_event_bus.service import CentralizedEventBus
from backend.error_recovery_engine.service import ErrorRecoveryEngine
from backend.execution_sandbox.schemas import ExecutionQuota
from backend.execution_sandbox.service import ExecutionSandbox
from backend.lifecycle_manager.service import LifecycleManager
from backend.observability_engine.service import ObservabilityEngine
from backend.performance_monitor.service import PerformanceMonitor
from backend.structured_config_system.service import StructuredConfigSystem
from tests.helpers import make_test_settings


def test_centralized_event_bus_filters_and_records_metrics():
    bus = CentralizedEventBus()
    received = []

    bus.subscribe(
        received.append,
        EventFilter(categories=(EVENT_CATEGORY_WORKFLOW,)),
        name="workflow_test",
    )
    bus.publish(
        PlatformEvent(
            event_type="workflow_started",
            source="test",
            category=EVENT_CATEGORY_WORKFLOW,
            payload={"workflow_id": "wf-1"},
        )
    )
    bus.publish(
        PlatformEvent(
            event_type="ai_request_started",
            source="test",
            category="ai",
        )
    )

    metrics = bus.metrics()

    assert len(received) == 1
    assert received[0].trace_id
    assert metrics.published_count == 2
    assert metrics.delivered_count == 1


def test_application_state_manager_updates_from_events():
    state = ApplicationStateManager()
    snapshots = []
    state.subscribe("*", snapshots.append)

    state.handle_event(
        PlatformEvent(
            event_type="workflow_started",
            source="test",
            category=EVENT_CATEGORY_WORKFLOW,
            correlation_id="wf-1",
            payload={"workflow_id": "wf-1", "message": "started"},
        )
    )

    snapshot = state.snapshot()

    assert "wf-1" in snapshot.active_workflows
    assert snapshot.event_counters[EVENT_CATEGORY_WORKFLOW] == 1
    assert snapshots


def test_structured_config_validation_uses_safe_fallback(tmp_path):
    settings = make_test_settings(tmp_path)
    system = StructuredConfigSystem(settings=settings)
    config = system.load()

    assert config.profile == "test"
    assert system.validate(config).is_valid is True
    assert system.feature_enabled("automation_enabled") is True


def test_observability_records_diagnostics_and_health():
    state = ApplicationStateManager()
    observability = ObservabilityEngine(state_manager=state)

    observability.handle_event(
        PlatformEvent(
            event_type="workflow_completed",
            source="test",
            category=EVENT_CATEGORY_WORKFLOW,
            payload={"duration_ms": 12.5},
        )
    )
    observability.record_error("test", "boom", RuntimeError("boom"))
    report = observability.health_report()

    assert observability.recent_timings()[0].duration_ms == 12.5
    assert report.degraded is True
    assert report.checks["recent_errors"] == 1


def test_execution_sandbox_rate_limits_and_emergency_stop():
    sandbox = ExecutionSandbox(
        default_quota=ExecutionQuota(max_calls=1, window_seconds=60.0)
    )

    first = sandbox.begin_execution("automation", "open_app", {"app_name": "vscode"})
    sandbox.end_execution("automation", "open_app")
    second = sandbox.begin_execution("automation", "open_app", {"app_name": "vscode"})
    sandbox.trigger_emergency_stop()
    stopped = sandbox.evaluate_action("automation", "open_app", {})

    assert first.allowed is True
    assert second.allowed is False
    assert "Rate limit" in second.reason
    assert stopped.allowed is False
    assert stopped.emergency_stop is True


def test_performance_monitor_samples_event_throughput():
    bus = CentralizedEventBus()
    monitor = PerformanceMonitor()
    bus.publish(PlatformEvent(event_type="test_event", source="test", category="system"))

    sample = monitor.sample(bus)

    assert sample.worker_count >= 1
    assert sample.event_throughput_per_minute >= 0
    assert monitor.latest_sample() == sample


def test_lifecycle_manager_starts_and_stops_in_order():
    order = []
    lifecycle = LifecycleManager()
    lifecycle.register("database", start=lambda: order.append("start_db"), stop=lambda: order.append("stop_db"))
    lifecycle.register(
        "workers",
        start=lambda: order.append("start_workers"),
        stop=lambda: order.append("stop_workers"),
        dependencies=("database",),
    )

    started = lifecycle.start_all()
    stopped = lifecycle.shutdown_all()

    assert started.started_steps == ("database", "workers")
    assert stopped.stopped_steps == ("workers", "database")
    assert order == ["start_db", "start_workers", "stop_workers", "stop_db"]


def test_error_recovery_categorizes_and_falls_back():
    recovery = ErrorRecoveryEngine()

    result = recovery.recover(RuntimeError("ollama unavailable"), "chat")
    value = recovery.safe_execute(
        lambda: (_ for _ in ()).throw(RuntimeError("database locked")),
        fallback="fallback",
        context="database",
    )

    assert result.category == "ai"
    assert result.degraded_mode is True
    assert value == "fallback"
