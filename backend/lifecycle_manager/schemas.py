"""Lifecycle manager schemas."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LifecycleStep:
    """One startup/shutdown lifecycle step."""

    name: str
    start: object | None = None
    stop: object | None = None
    dependencies: tuple[str, ...] = ()
    started: bool = False


@dataclass(frozen=True)
class LifecycleState:
    """Lifecycle runtime state."""

    started_steps: tuple[str, ...] = field(default_factory=tuple)
    stopped_steps: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
