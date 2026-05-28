"""Persistence models for proactive intelligence features."""

from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
from database.models import utc_now


class ProductivitySummary(Base):
    """Daily deterministic productivity summary."""

    __tablename__ = "productivity_summaries"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    summary_date: Mapped[date] = mapped_column(Date, index=True, unique=True)
    productivity_score: Mapped[float] = mapped_column(Float, default=0.0)
    consistency_score: Mapped[float] = mapped_column(Float, default=0.0)
    focus_score: Mapped[float] = mapped_column(Float, default=0.0)
    completed_tasks: Mapped[int] = mapped_column(Integer, default=0)
    open_tasks: Mapped[int] = mapped_column(Integer, default=0)
    study_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    focus_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    distraction_count: Mapped[int] = mapped_column(Integer, default=0)
    interruption_count: Mapped[int] = mapped_column(Integer, default=0)
    summary_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    focus_report: Mapped[str] = mapped_column(Text, default="", nullable=False)
    task_report: Mapped[str] = mapped_column(Text, default="", nullable=False)
    study_statistics_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    ai_insight: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class RecommendationLog(Base):
    """Audit trail for proactive recommendations and notification decisions."""

    __tablename__ = "recommendation_logs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    recommendation_type: Mapped[str] = mapped_column(String(80), index=True)
    cooldown_key: Mapped[str] = mapped_column(String(160), index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(32), index=True, default="normal")
    context_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    status: Mapped[str] = mapped_column(String(40), index=True, default="generated")
    suppression_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BehavioralPattern(Base):
    """Learned local behavior pattern with confidence metadata."""

    __tablename__ = "behavioral_patterns"
    __table_args__ = (
        UniqueConstraint("pattern_type", "pattern_key", name="uq_behavioral_pattern"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    pattern_type: Mapped[str] = mapped_column(String(80), index=True)
    pattern_key: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
