"""Observer engine.

This subsystem is the future home for screen, window, filesystem, and app-state
observation. It starts as a no-op service so the architecture is explicit.
"""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import AppSettings


@dataclass
class ObserverEngine:
    """Collects local context for agents."""

    settings: AppSettings

    def snapshot(self) -> dict[str, str]:
        """Return a minimal environment snapshot."""
        return {"environment": self.settings.app_env}
