"""Runtime execution sandbox and safety controls."""

from __future__ import annotations

import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime

from database.models import utc_now
from backend.execution_sandbox.schemas import (
    ExecutionQuota,
    SandboxDecision,
    SandboxState,
)

SANDBOX_BLOCKED_KEYWORDS = (
    "delete",
    "format",
    "shutdown",
    "restart",
    "registry",
    "regedit",
    "powershell",
    "cmd.exe",
    "remove-item",
    "rm ",
)


@dataclass
class ExecutionSandbox:
    """Controls tool execution, rate limits, and emergency interruption."""

    safe_mode: bool = False
    emergency_stop: bool = False
    default_quota: ExecutionQuota = field(
        default_factory=lambda: ExecutionQuota(max_calls=20, window_seconds=60.0)
    )
    blocked_actions: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self._lock = threading.RLock()
        self._active_locks: set[str] = set()
        self._call_windows: dict[str, deque[datetime]] = defaultdict(deque)

    def block_action(self, action_name: str) -> None:
        """Add an action to the runtime blocklist."""
        with self._lock:
            self.blocked_actions.add(action_name)

    def unblock_action(self, action_name: str) -> None:
        """Remove an action from the runtime blocklist."""
        with self._lock:
            self.blocked_actions.discard(action_name)

    def set_safe_mode(self, enabled: bool) -> None:
        """Enable or disable safe mode."""
        with self._lock:
            self.safe_mode = enabled

    def trigger_emergency_stop(self) -> None:
        """Stop all new execution immediately."""
        with self._lock:
            self.emergency_stop = True
            self._active_locks.clear()

    def clear_emergency_stop(self) -> None:
        """Clear emergency stop after operator action."""
        with self._lock:
            self.emergency_stop = False

    def begin_execution(
        self,
        subject: str,
        action_name: str,
        parameters: dict[str, object] | None = None,
    ) -> SandboxDecision:
        """Evaluate and reserve permission to execute an action."""
        parameters = parameters or {}
        with self._lock:
            decision = self.evaluate_action(subject, action_name, parameters)
            if not decision.allowed:
                return decision
            lock_key = self._lock_key(subject, action_name)
            if lock_key in self._active_locks:
                return SandboxDecision(
                    allowed=False,
                    reason=f"Action already running: {action_name}.",
                    safe_mode=self.safe_mode,
                    emergency_stop=self.emergency_stop,
                )
            self._active_locks.add(lock_key)
            self._record_call(subject)
            return decision

    def end_execution(self, subject: str, action_name: str) -> None:
        """Release an execution lock."""
        with self._lock:
            self._active_locks.discard(self._lock_key(subject, action_name))

    def evaluate_action(
        self,
        subject: str,
        action_name: str,
        parameters: dict[str, object] | None = None,
    ) -> SandboxDecision:
        """Return whether an action is safe to execute."""
        parameters = parameters or {}
        if self.emergency_stop:
            return SandboxDecision(
                allowed=False,
                reason="Emergency stop is active.",
                safe_mode=self.safe_mode,
                emergency_stop=True,
                safety_score=0.0,
            )
        if action_name in self.blocked_actions:
            return SandboxDecision(
                allowed=False,
                reason=f"Action is blocked by sandbox: {action_name}.",
                safe_mode=self.safe_mode,
                safety_score=0.0,
            )
        unsafe_keyword = self._blocked_keyword(parameters)
        if unsafe_keyword:
            return SandboxDecision(
                allowed=False,
                reason=f"Sandbox blocked unsafe keyword: {unsafe_keyword}.",
                safe_mode=self.safe_mode,
                safety_score=0.0,
            )
        if not self._within_quota(subject):
            return SandboxDecision(
                allowed=False,
                reason=f"Rate limit exceeded for {subject}.",
                safe_mode=self.safe_mode,
                safety_score=0.2,
            )
        if self.safe_mode and action_name not in {"open_app", "open_website", "play_music", "notify", "noop"}:
            return SandboxDecision(
                allowed=False,
                reason=f"Safe mode blocked action: {action_name}.",
                safe_mode=True,
                safety_score=0.4,
            )
        return SandboxDecision(
            allowed=True,
            reason="Sandbox allowed execution.",
            safe_mode=self.safe_mode,
            safety_score=1.0,
        )

    def score_workflow(self, steps: list[dict[str, object]]) -> float:
        """Return a simple workflow safety score between 0 and 1."""
        if not steps:
            return 0.0
        score = 1.0
        automation_count = 0
        for step in steps:
            action_name = str(step.get("action_name", ""))
            parameters = dict(step.get("parameters", {}) or {})
            if action_name in self.blocked_actions or self._blocked_keyword(parameters):
                score -= 0.5
            if step.get("action_type") == "automation_tool":
                automation_count += 1
        if automation_count > 10:
            score -= 0.25
        return max(min(score, 1.0), 0.0)

    def state(self) -> SandboxState:
        """Return current sandbox state."""
        with self._lock:
            return SandboxState(
                safe_mode=self.safe_mode,
                emergency_stop=self.emergency_stop,
                blocked_actions=tuple(sorted(self.blocked_actions)),
                active_locks=tuple(sorted(self._active_locks)),
                quota_usage={key: len(value) for key, value in self._call_windows.items()},
            )

    def _within_quota(self, subject: str) -> bool:
        now = utc_now()
        window = self._call_windows[subject]
        while window and (now - window[0]).total_seconds() > self.default_quota.window_seconds:
            window.popleft()
        return len(window) < self.default_quota.max_calls

    def _record_call(self, subject: str) -> None:
        self._call_windows[subject].append(utc_now())

    def _blocked_keyword(self, parameters: dict[str, object]) -> str:
        haystack = " ".join(str(value).lower() for value in parameters.values())
        for keyword in SANDBOX_BLOCKED_KEYWORDS:
            if keyword in haystack:
                return keyword.strip()
        return ""

    def _lock_key(self, subject: str, action_name: str) -> str:
        return f"{subject}:{action_name}"
