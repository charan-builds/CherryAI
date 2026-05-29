"""Small publish-subscribe bus for workflow updates."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from backend.workflow_state_manager.schemas import WorkflowEvent

logger = logging.getLogger(__name__)

WorkflowEventHandler = Callable[[WorkflowEvent], None]


@dataclass
class WorkflowEventBus:
    """Publishes workflow state changes to interested services."""

    subscribers: dict[str, list[WorkflowEventHandler]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def subscribe(self, event_type: str, handler: WorkflowEventHandler) -> None:
        """Subscribe a handler to an event type or '*' for every event."""
        self.subscribers[event_type].append(handler)

    def publish(self, event: WorkflowEvent) -> None:
        """Publish an event without letting one subscriber break the engine."""
        handlers = list(self.subscribers.get(event.event_type, []))
        handlers.extend(self.subscribers.get("*", []))

        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception("Workflow event handler failed")
