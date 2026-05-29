"""Error recovery schemas."""

from __future__ import annotations

from dataclasses import dataclass, field

ERROR_CATEGORY_AI = "ai"
ERROR_CATEGORY_AUTOMATION = "automation"
ERROR_CATEGORY_DATABASE = "database"
ERROR_CATEGORY_OBSERVER = "observer"
ERROR_CATEGORY_WORKFLOW = "workflow"
ERROR_CATEGORY_UNKNOWN = "unknown"


@dataclass(frozen=True)
class RetryStrategy:
    """Simple retry strategy."""

    max_attempts: int = 1
    delay_seconds: float = 0.0


@dataclass(frozen=True)
class RecoveryResult:
    """Result of centralized recovery handling."""

    recovered: bool
    category: str
    message: str
    degraded_mode: bool = False
    attempts: int = 0
    metadata: dict[str, object] = field(default_factory=dict)
