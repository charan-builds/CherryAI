"""Daily timeline schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class TimelineItem:
    """One item in the user's daily timeline."""

    entry_type: str
    title: str
    description: str
    started_at: datetime
    ended_at: datetime | None = None
    source_id: str = ""
    metadata: dict[str, object] = field(default_factory=dict)
    id: str = ""


@dataclass(frozen=True)
class DailyTimeline:
    """Timeline view for a single day."""

    timeline_date: date
    items: tuple[TimelineItem, ...]

    @property
    def item_count(self) -> int:
        """Return number of timeline items."""
        return len(self.items)
