"""Analytics engine.

Analytics are local-first by default. This service will record product health
and usage events without requiring cloud telemetry.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from config.settings import AppSettings


@dataclass
class AnalyticsEngine:
    """Records local application events."""

    settings: AppSettings
    events: list[dict[str, str]] = field(default_factory=list)

    def record(self, name: str, **properties: str) -> None:
        """Record an in-memory event placeholder."""
        self.events.append({"name": name, **properties})
