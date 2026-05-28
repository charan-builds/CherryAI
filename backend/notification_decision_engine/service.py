"""Safe notification timing and suppression decisions."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, time

from config.settings import AppSettings
from database.models import utc_now
from backend.notification_decision_engine.schemas import NotificationDecision
from backend.recommendation_engine.repository import RecommendationLogRepository
from backend.recommendation_engine.schemas import Recommendation

logger = logging.getLogger(__name__)


@dataclass
class NotificationDecisionEngine:
    """Controls timing, priority, cooldowns, quiet mode, and duplicates."""

    settings: AppSettings
    repository: RecommendationLogRepository | None = None

    def __post_init__(self) -> None:
        if self.repository is None:
            self.repository = RecommendationLogRepository.from_settings(self.settings)

    def evaluate(
        self,
        recommendation: Recommendation,
        now: datetime | None = None,
    ) -> NotificationDecision:
        """Decide whether to emit a notification for a recommendation."""
        current_time = now or utc_now()

        if self._is_quiet_time(current_time) and recommendation.priority != "high":
            return self._suppress(recommendation, "quiet_mode")

        if self.repository.has_recent(
            recommendation.cooldown_key,
            current_time,
            self.settings.notification_duplicate_window_seconds,
            statuses=("delivered",),
        ):
            return self._suppress(recommendation, "duplicate_suppressed")

        if (
            recommendation.priority != "high"
            and self.repository.has_any_recent_delivery(
                current_time,
                self.settings.notification_global_cooldown_seconds,
            )
        ):
            return self._suppress(recommendation, "global_cooldown")

        if recommendation.id is not None:
            self.repository.mark_status(
                recommendation.id,
                status="delivered",
                delivered_at=current_time,
            )
        logger.info("Notification allowed: %s", recommendation.cooldown_key)
        return NotificationDecision(
            recommendation=recommendation,
            should_notify=True,
            priority=recommendation.priority,
            reason="allowed",
        )

    def _suppress(self, recommendation: Recommendation, reason: str) -> NotificationDecision:
        if recommendation.id is not None:
            self.repository.mark_status(
                recommendation.id,
                status="suppressed",
                suppression_reason=reason,
            )
        logger.debug("Notification suppressed [%s]: %s", reason, recommendation.cooldown_key)
        return NotificationDecision(
            recommendation=recommendation,
            should_notify=False,
            priority=recommendation.priority,
            reason=reason,
        )

    def _is_quiet_time(self, now: datetime) -> bool:
        if not self.settings.notification_quiet_mode_enabled:
            return False

        start = self._parse_clock(self.settings.notification_quiet_hours_start)
        end = self._parse_clock(self.settings.notification_quiet_hours_end)
        current = now.time().replace(second=0, microsecond=0)

        if start <= end:
            return start <= current < end
        return current >= start or current < end

    def _parse_clock(self, raw_value: str) -> time:
        try:
            hour_text, minute_text = raw_value.split(":", 1)
            return time(hour=int(hour_text), minute=int(minute_text))
        except Exception:
            return time(hour=22, minute=0)
