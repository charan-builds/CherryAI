"""Centralized error categorization and recovery."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, TypeVar

from sqlalchemy.exc import SQLAlchemyError

from backend.centralized_event_bus.schemas import (
    EVENT_CATEGORY_SYSTEM,
    PRIORITY_HIGH,
    PlatformEvent,
)
from backend.centralized_event_bus.service import CentralizedEventBus
from backend.error_recovery_engine.schemas import (
    ERROR_CATEGORY_AI,
    ERROR_CATEGORY_AUTOMATION,
    ERROR_CATEGORY_DATABASE,
    ERROR_CATEGORY_OBSERVER,
    ERROR_CATEGORY_UNKNOWN,
    ERROR_CATEGORY_WORKFLOW,
    RecoveryResult,
    RetryStrategy,
)
from backend.ollama_service.service import OllamaGenerationError

logger = logging.getLogger(__name__)
T = TypeVar("T")


@dataclass
class ErrorRecoveryEngine:
    """Handles known failure modes without crashing the runtime."""

    event_bus: CentralizedEventBus | None = None
    retry_strategies: dict[str, RetryStrategy] = field(default_factory=dict)
    degraded_mode: bool = False

    def __post_init__(self) -> None:
        self.retry_strategies.setdefault(
            ERROR_CATEGORY_AI,
            RetryStrategy(max_attempts=1, delay_seconds=0.1),
        )
        self.retry_strategies.setdefault(
            ERROR_CATEGORY_AUTOMATION,
            RetryStrategy(max_attempts=0, delay_seconds=0.0),
        )
        self.retry_strategies.setdefault(
            ERROR_CATEGORY_DATABASE,
            RetryStrategy(max_attempts=1, delay_seconds=0.1),
        )

    def categorize(self, exc: Exception, context: str = "") -> str:
        """Map an exception to a recovery category."""
        text = f"{type(exc).__name__} {exc} {context}".lower()
        if isinstance(exc, OllamaGenerationError) or "ollama" in text:
            return ERROR_CATEGORY_AI
        if isinstance(exc, SQLAlchemyError) or "database" in text or "sqlite" in text:
            return ERROR_CATEGORY_DATABASE
        if "automation" in text or "pyautogui" in text or "timeout" in text:
            return ERROR_CATEGORY_AUTOMATION
        if "observer" in text:
            return ERROR_CATEGORY_OBSERVER
        if "workflow" in text:
            return ERROR_CATEGORY_WORKFLOW
        return ERROR_CATEGORY_UNKNOWN

    def recover(
        self,
        exc: Exception,
        context: str = "",
    ) -> RecoveryResult:
        """Record a recovery result and enter degraded mode when appropriate."""
        category = self.categorize(exc, context)
        degraded = category in {ERROR_CATEGORY_AI, ERROR_CATEGORY_DATABASE}
        self.degraded_mode = self.degraded_mode or degraded
        result = RecoveryResult(
            recovered=category != ERROR_CATEGORY_DATABASE,
            category=category,
            message=self._message_for(category),
            degraded_mode=self.degraded_mode,
            metadata={"context": context, "exception": str(exc)},
        )
        self._publish(result)
        return result

    def safe_execute(
        self,
        operation: Callable[[], T],
        fallback: T,
        context: str = "",
    ) -> T:
        """Run an operation with category-aware retries and fallback."""
        last_error: Exception | None = None
        category = ERROR_CATEGORY_UNKNOWN
        attempts = 1
        for attempt in range(1, 4):
            try:
                return operation()
            except Exception as exc:
                last_error = exc
                category = self.categorize(exc, context)
                strategy = self.retry_strategies.get(category, RetryStrategy())
                attempts = attempt
                if attempt > strategy.max_attempts:
                    break
                if strategy.delay_seconds:
                    time.sleep(strategy.delay_seconds)

        if last_error is not None:
            result = self.recover(last_error, context)
            logger.warning(
                "Recovery fallback used category=%s attempts=%s message=%s",
                category,
                attempts,
                result.message,
            )
        return fallback

    def _message_for(self, category: str) -> str:
        messages = {
            ERROR_CATEGORY_AI: "AI runtime is unavailable; using local fallback behavior.",
            ERROR_CATEGORY_AUTOMATION: "Automation failed safely; action was stopped.",
            ERROR_CATEGORY_DATABASE: "Database access failed; runtime entered degraded mode.",
            ERROR_CATEGORY_OBSERVER: "Observer failed; keeping last known activity state.",
            ERROR_CATEGORY_WORKFLOW: "Workflow failed; recovery suggestions will be generated.",
        }
        return messages.get(category, "Unexpected error handled safely.")

    def _publish(self, result: RecoveryResult) -> None:
        if self.event_bus is None:
            return
        self.event_bus.publish(
            PlatformEvent(
                event_type="error_recovery",
                source="error_recovery_engine",
                category=EVENT_CATEGORY_SYSTEM,
                priority=PRIORITY_HIGH,
                payload={
                    "category": result.category,
                    "message": result.message,
                    "degraded": result.degraded_mode,
                },
            )
        )
