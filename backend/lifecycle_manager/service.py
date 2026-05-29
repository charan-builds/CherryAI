"""Centralized application lifecycle manager."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable

from backend.centralized_event_bus.schemas import (
    EVENT_CATEGORY_LIFECYCLE,
    PRIORITY_HIGH,
    PlatformEvent,
)
from backend.centralized_event_bus.service import CentralizedEventBus
from backend.lifecycle_manager.schemas import LifecycleState, LifecycleStep

logger = logging.getLogger(__name__)

LifecycleFn = Callable[[], object]


@dataclass
class LifecycleManager:
    """Manages deterministic startup and graceful shutdown."""

    event_bus: CentralizedEventBus | None = None
    steps: dict[str, LifecycleStep] = field(default_factory=dict)
    startup_order: list[str] = field(default_factory=list)
    stopped_steps: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def register(
        self,
        name: str,
        start: LifecycleFn | None = None,
        stop: LifecycleFn | None = None,
        dependencies: tuple[str, ...] = (),
    ) -> None:
        """Register one lifecycle managed component."""
        self.steps[name] = LifecycleStep(
            name=name,
            start=start,
            stop=stop,
            dependencies=dependencies,
        )

    def start_all(self) -> LifecycleState:
        """Start all registered steps in dependency order."""
        for name in self._ordered_step_names():
            step = self.steps[name]
            if step.started:
                continue
            try:
                if step.start is not None:
                    step.start()
                step.started = True
                self.startup_order.append(name)
                self._publish("lifecycle_started", name)
            except Exception as exc:
                logger.exception("Lifecycle start failed: %s", name)
                self.errors.append(f"{name}: {exc}")
                self._publish("lifecycle_start_failed", name, str(exc))
        return self.state()

    def shutdown_all(self) -> LifecycleState:
        """Stop all started steps in reverse startup order."""
        for name in reversed(self.startup_order):
            step = self.steps[name]
            if not step.started:
                continue
            try:
                if step.stop is not None:
                    step.stop()
                step.started = False
                self.stopped_steps.append(name)
                self._publish("lifecycle_stopped", name)
            except Exception as exc:
                logger.exception("Lifecycle stop failed: %s", name)
                self.errors.append(f"{name}: {exc}")
                self._publish("lifecycle_stop_failed", name, str(exc))
        return self.state()

    def state(self) -> LifecycleState:
        """Return current lifecycle state."""
        return LifecycleState(
            started_steps=tuple(self.startup_order),
            stopped_steps=tuple(self.stopped_steps),
            errors=tuple(self.errors),
        )

    def _ordered_step_names(self) -> list[str]:
        ordered: list[str] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            if name in visiting:
                raise ValueError(f"Lifecycle dependency cycle at {name}")
            visiting.add(name)
            step = self.steps[name]
            for dependency in step.dependencies:
                if dependency not in self.steps:
                    raise ValueError(f"Missing lifecycle dependency: {dependency}")
                visit(dependency)
            visiting.remove(name)
            visited.add(name)
            ordered.append(name)

        for name in self.steps:
            visit(name)
        return ordered

    def _publish(self, event_type: str, step_name: str, error: str = "") -> None:
        if self.event_bus is None:
            return
        self.event_bus.publish(
            PlatformEvent(
                event_type=event_type,
                source="lifecycle_manager",
                category=EVENT_CATEGORY_LIFECYCLE,
                priority=PRIORITY_HIGH,
                payload={
                    "step": step_name,
                    "status": event_type,
                    "error": error,
                },
            )
        )
