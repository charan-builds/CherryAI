"""Observability engine for diagnostics, tracing, and health reports."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from backend.application_state_manager.service import ApplicationStateManager
from backend.centralized_event_bus.schemas import PlatformEvent
from backend.observability_engine.schemas import (
    DiagnosticRecord,
    SystemHealthReport,
    TimingRecord,
)
from backend.observability_engine.trace_manager import TraceManager

logger = logging.getLogger(__name__)


@dataclass
class ObservabilityEngine:
    """Central diagnostics service for Cherry AI runtime."""

    state_manager: ApplicationStateManager | None = None
    trace_manager: TraceManager = field(default_factory=TraceManager)
    diagnostics: list[DiagnosticRecord] = field(default_factory=list)
    timings: list[TimingRecord] = field(default_factory=list)

    def handle_event(self, event: PlatformEvent) -> None:
        """Record event diagnostics and timing hints."""
        self.record_diagnostic(
            category=event.category,
            message=event.event_type,
            trace_id=event.trace_id,
            payload={
                "source": event.source,
                "priority": event.priority,
                "correlation_id": event.correlation_id,
            },
        )
        duration = event.payload.get("duration_ms")
        if isinstance(duration, (int, float)):
            self.record_timing(
                operation=event.event_type,
                duration_ms=float(duration),
                category=event.category,
                trace_id=event.trace_id,
            )

    def record_diagnostic(
        self,
        category: str,
        message: str,
        level: str = "info",
        trace_id: str = "",
        payload: dict[str, object] | None = None,
    ) -> DiagnosticRecord:
        """Store and log a structured diagnostic record."""
        record = DiagnosticRecord(
            category=category,
            message=message,
            level=level,
            trace_id=trace_id,
            payload=payload or {},
        )
        self.diagnostics.append(record)
        logger.log(
            logging.ERROR if level == "error" else logging.INFO,
            "diagnostic category=%s message=%s trace_id=%s",
            category,
            message,
            trace_id,
        )
        return record

    def record_timing(
        self,
        operation: str,
        duration_ms: float,
        category: str,
        trace_id: str = "",
        metadata: dict[str, object] | None = None,
    ) -> TimingRecord:
        """Store a performance timing record."""
        record = TimingRecord(
            operation=operation,
            duration_ms=duration_ms,
            category=category,
            trace_id=trace_id,
            metadata=metadata or {},
        )
        self.timings.append(record)
        return record

    def record_error(
        self,
        category: str,
        message: str,
        exc: Exception | None = None,
        trace_id: str = "",
    ) -> DiagnosticRecord:
        """Record an error diagnostic."""
        payload = {"exception": type(exc).__name__, "details": str(exc)} if exc else {}
        return self.record_diagnostic(
            category=category,
            message=message,
            level="error",
            trace_id=trace_id,
            payload=payload,
        )

    def health_report(self) -> SystemHealthReport:
        """Build a current health report."""
        snapshot = self.state_manager.snapshot() if self.state_manager else None
        checks = {
            "diagnostics": len(self.diagnostics),
            "timings": len(self.timings),
            "recent_errors": len(
                [record for record in self.diagnostics[-25:] if record.level == "error"]
            ),
        }
        if snapshot is not None:
            checks["state_updated_at"] = snapshot.updated_at.isoformat()
            checks["event_counters"] = snapshot.event_counters

        degraded = checks["recent_errors"] > 0
        return SystemHealthReport(
            status="degraded" if degraded else "healthy",
            degraded=degraded,
            checks=checks,
        )

    def recent_diagnostics(self, limit: int = 25) -> list[DiagnosticRecord]:
        """Return recent diagnostics newest-first."""
        return list(reversed(self.diagnostics[-limit:]))

    def recent_timings(self, limit: int = 25) -> list[TimingRecord]:
        """Return recent timings newest-first."""
        return list(reversed(self.timings[-limit:]))
