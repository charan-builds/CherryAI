"""Trace span management."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from database.models import utc_now
from backend.observability_engine.schemas import TraceSpan


@dataclass
class TraceManager:
    """Creates and stores lightweight execution spans."""

    completed_spans: list[TraceSpan] = field(default_factory=list)

    def new_trace_id(self) -> str:
        """Return a new trace id."""
        return str(uuid4())

    @contextmanager
    def span(
        self,
        name: str,
        trace_id: str | None = None,
        parent_span_id: str = "",
        **attributes: object,
    ):
        """Context manager that records operation duration."""
        active = TraceSpan(
            name=name,
            trace_id=trace_id or self.new_trace_id(),
            parent_span_id=parent_span_id,
            attributes=attributes,
        )
        try:
            yield active
        finally:
            ended_at = utc_now()
            self.completed_spans.append(
                TraceSpan(
                    name=active.name,
                    trace_id=active.trace_id,
                    span_id=active.span_id,
                    parent_span_id=active.parent_span_id,
                    started_at=active.started_at,
                    ended_at=ended_at,
                    duration_ms=_duration_ms(active.started_at, ended_at),
                    attributes=active.attributes,
                )
            )

    def recent_spans(self, limit: int = 25) -> list[TraceSpan]:
        """Return recent completed spans newest-first."""
        return list(reversed(self.completed_spans[-limit:]))


def _duration_ms(started_at: datetime, ended_at: datetime) -> float:
    if started_at.tzinfo is None and ended_at.tzinfo is not None:
        ended_at = ended_at.replace(tzinfo=None)
    if started_at.tzinfo is not None and ended_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=None)
    return max((ended_at - started_at).total_seconds() * 1000.0, 0.0)
