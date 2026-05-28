"""Working memory DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class WorkingMemoryRecord:
    """Temporary state used while Cherry is actively helping."""

    id: str
    state_key: str
    state_type: str
    content: str
    metadata: dict[str, object] = field(default_factory=dict)
    expires_at: datetime | None = None
    updated_at: datetime | None = None
