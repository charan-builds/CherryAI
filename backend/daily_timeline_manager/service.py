"""Daily timeline manager."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from config.settings import AppSettings
from database.models import utc_now
from backend.daily_timeline_manager.repository import DailyTimelineRepository
from backend.daily_timeline_manager.schemas import DailyTimeline, TimelineItem


@dataclass
class DailyTimelineManager:
    """Creates and returns daily companion timeline records."""

    settings: AppSettings
    repository: DailyTimelineRepository | None = None

    def __post_init__(self) -> None:
        self.repository = self.repository or DailyTimelineRepository.from_settings(
            self.settings
        )

    def record_item(
        self,
        entry_type: str,
        title: str,
        description: str = "",
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        source_id: str = "",
        metadata: dict[str, object] | None = None,
    ) -> TimelineItem:
        """Persist a timeline item."""
        item = TimelineItem(
            entry_type=entry_type,
            title=title.strip() or entry_type.replace("_", " ").title(),
            description=description.strip(),
            started_at=started_at or utc_now(),
            ended_at=ended_at,
            source_id=source_id,
            metadata=metadata or {},
        )
        return self.repository.create(item)

    def generate_for_day(self, day: date | None = None) -> DailyTimeline:
        """Return a timeline view for a day."""
        timeline_date = day or utc_now().date()
        return DailyTimeline(
            timeline_date=timeline_date,
            items=tuple(self.repository.list_for_day(timeline_date)),
        )

    def record_task_completed(self, task_title: str, task_id: str = "") -> TimelineItem:
        """Record a completed task in the timeline."""
        return self.record_item(
            entry_type="task_completed",
            title=task_title,
            description="Task completed.",
            source_id=task_id,
        )

    def record_workflow_event(
        self,
        workflow_name: str,
        status: str,
        workflow_id: str = "",
    ) -> TimelineItem:
        """Record workflow activity in the timeline."""
        return self.record_item(
            entry_type="workflow_execution",
            title=workflow_name,
            description=f"Workflow {status}.",
            source_id=workflow_id,
            metadata={"status": status},
        )

    def record_focus_period(
        self,
        title: str,
        focus_seconds: float,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
    ) -> TimelineItem:
        """Record a focus period."""
        return self.record_item(
            entry_type="focus_period",
            title=title,
            description=f"Focused for {int(focus_seconds // 60)} min.",
            started_at=started_at,
            ended_at=ended_at,
            metadata={"focus_seconds": focus_seconds},
        )
