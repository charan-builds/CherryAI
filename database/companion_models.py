"""Daily companion experience persistence models."""

from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import Date, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
from database.models import utc_now


class DailyTimelineEntry(Base):
    """Persisted timeline item for one day."""

    __tablename__ = "daily_timeline_entries"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    entry_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    entry_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_id: Mapped[str] = mapped_column(String(120), default="", index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class CompanionInteractionLog(Base):
    """Persisted companion message/cooldown history."""

    __tablename__ = "companion_interaction_logs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    interaction_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    cooldown_key: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(32), default="normal", index=True)
    status: Mapped[str] = mapped_column(String(40), default="generated", index=True)
    context_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
