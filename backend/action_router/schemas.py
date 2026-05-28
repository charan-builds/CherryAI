"""Action router schemas."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RoutedActionResult:
    """Result of routing a parsed intent to backend services."""

    intent: str
    success: bool
    message: str
    data: dict[str, object] = field(default_factory=dict)
