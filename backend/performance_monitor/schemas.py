"""Performance monitor schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from database.models import utc_now


@dataclass(frozen=True)
class PerformanceThresholds:
    """Warning thresholds for lightweight performance checks."""

    memory_warning_mb: float = 1024.0
    event_rate_warning_per_minute: int = 600
    worker_warning_count: int = 20


@dataclass(frozen=True)
class PerformanceSample:
    """One sampled performance snapshot."""

    memory_mb: float
    cpu_percent: float
    worker_count: int
    db_query_count: int
    workflow_concurrency: int
    event_throughput_per_minute: float
    polling_load: dict[str, float] = field(default_factory=dict)
    alerts: tuple[str, ...] = ()
    sampled_at: datetime = field(default_factory=utc_now)
