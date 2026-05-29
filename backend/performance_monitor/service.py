"""Lightweight internal performance monitor."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field

from backend.centralized_event_bus.service import CentralizedEventBus
from backend.performance_monitor.schemas import PerformanceSample, PerformanceThresholds


@dataclass
class PerformanceMonitor:
    """Samples runtime performance without blocking the UI."""

    thresholds: PerformanceThresholds = field(default_factory=PerformanceThresholds)
    db_query_count: int = 0
    workflow_concurrency: int = 0

    def __post_init__(self) -> None:
        self._started_at = time.monotonic()
        self._last_event_count = 0
        self._last_sample_at = time.monotonic()
        self.samples: list[PerformanceSample] = []

    def record_db_query(self) -> None:
        """Increment DB query counter for future instrumentation."""
        self.db_query_count += 1

    def set_workflow_concurrency(self, value: int) -> None:
        """Update current workflow concurrency."""
        self.workflow_concurrency = max(value, 0)

    def sample(self, event_bus: CentralizedEventBus | None = None) -> PerformanceSample:
        """Collect a lightweight performance sample."""
        now = time.monotonic()
        event_count = event_bus.metrics().published_count if event_bus else 0
        elapsed = max(now - self._last_sample_at, 0.001)
        event_delta = max(event_count - self._last_event_count, 0)
        throughput = (event_delta / elapsed) * 60.0
        self._last_event_count = event_count
        self._last_sample_at = now

        sample = PerformanceSample(
            memory_mb=self._memory_mb(),
            cpu_percent=0.0,
            worker_count=threading.active_count(),
            db_query_count=self.db_query_count,
            workflow_concurrency=self.workflow_concurrency,
            event_throughput_per_minute=round(throughput, 2),
            alerts=tuple(self._alerts(throughput)),
        )
        self.samples.append(sample)
        return sample

    def latest_sample(self) -> PerformanceSample | None:
        """Return latest sample if available."""
        return self.samples[-1] if self.samples else None

    def _alerts(self, event_throughput: float) -> list[str]:
        alerts: list[str] = []
        memory_mb = self._memory_mb()
        if memory_mb > self.thresholds.memory_warning_mb:
            alerts.append(f"Memory above {self.thresholds.memory_warning_mb:.0f} MB")
        if event_throughput > self.thresholds.event_rate_warning_per_minute:
            alerts.append("High event throughput")
        if threading.active_count() > self.thresholds.worker_warning_count:
            alerts.append("High worker count")
        return alerts

    def _memory_mb(self) -> float:
        try:
            import psutil

            return round(psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024, 2)
        except Exception:
            return 0.0
