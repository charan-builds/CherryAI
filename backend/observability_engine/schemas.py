"""Observability and diagnostics models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from database.models import utc_now


@dataclass(frozen=True)
class TraceSpan:
    """One timed operation span."""

    name: str
    trace_id: str
    span_id: str = field(default_factory=lambda: str(uuid4()))
    parent_span_id: str = ""
    started_at: datetime = field(default_factory=utc_now)
    ended_at: datetime | None = None
    duration_ms: float = 0.0
    attributes: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class DiagnosticRecord:
    """Structured diagnostic record."""

    category: str
    message: str
    level: str = "info"
    trace_id: str = ""
    payload: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class TimingRecord:
    """Recorded operation timing."""

    operation: str
    duration_ms: float
    category: str
    trace_id: str = ""
    metadata: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class SystemHealthReport:
    """Runtime health summary."""

    status: str
    degraded: bool
    checks: dict[str, object]
    generated_at: datetime = field(default_factory=utc_now)
