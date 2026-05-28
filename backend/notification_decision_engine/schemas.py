"""Notification decision DTOs."""

from __future__ import annotations

from dataclasses import dataclass

from backend.recommendation_engine.schemas import Recommendation


@dataclass(frozen=True)
class NotificationDecision:
    """Decision for whether a recommendation should become a notification."""

    recommendation: Recommendation
    should_notify: bool
    priority: str
    reason: str
