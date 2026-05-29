"""Persistence models for the knowledge intelligence layer."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
from database.models import utc_now


class KnowledgeMemory(Base):
    """Durable summaries, notes, concepts, and tags from user knowledge sources."""

    __tablename__ = "knowledge_memories"
    __table_args__ = (
        UniqueConstraint("content_hash", name="uq_knowledge_memory_content_hash"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    source_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    source_name: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    notes_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    concepts_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    tags_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    semantic_memory_id: Mapped[str] = mapped_column(String(36), default="", index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
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
