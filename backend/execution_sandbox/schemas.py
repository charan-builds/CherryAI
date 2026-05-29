"""Execution sandbox schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from database.models import utc_now


@dataclass(frozen=True)
class SandboxDecision:
    """Decision returned by the execution sandbox."""

    allowed: bool
    reason: str
    safe_mode: bool = False
    emergency_stop: bool = False
    safety_score: float = 1.0


@dataclass(frozen=True)
class ExecutionQuota:
    """Execution quota for a subject over a rolling window."""

    max_calls: int
    window_seconds: float


@dataclass(frozen=True)
class SandboxState:
    """Runtime sandbox state snapshot."""

    safe_mode: bool
    emergency_stop: bool
    blocked_actions: tuple[str, ...]
    active_locks: tuple[str, ...]
    quota_usage: dict[str, int] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=utc_now)
