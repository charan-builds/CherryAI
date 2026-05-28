"""Intent parser schemas."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParsedIntent:
    """Structured intent extracted from a user message."""

    intent: str
    title: str = ""
    description: str = ""
    priority: str = "normal"
    raw: dict[str, object] = field(default_factory=dict)
