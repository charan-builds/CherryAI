"""Keyboard and mouse idle detection."""

from __future__ import annotations

import ctypes
import logging
from ctypes import wintypes
from dataclasses import dataclass
from typing import Protocol

from database.models import utc_now
from backend.observer_engine.observer_event_bus.events import IDLE_DETECTED, ObserverEvent
from backend.observer_engine.schemas import IdleSnapshot

logger = logging.getLogger(__name__)


class IdleProvider(Protocol):
    """Provider interface for keyboard/mouse idle duration."""

    def get_idle_seconds(self) -> float:
        """Return seconds since last keyboard or mouse input."""


class LASTINPUTINFO(ctypes.Structure):
    """Windows LASTINPUTINFO structure."""

    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("dwTime", wintypes.DWORD),
    ]


class WindowsIdleProvider:
    """Windows keyboard/mouse idle provider."""

    def get_idle_seconds(self) -> float:
        """Return seconds since last input using GetLastInputInfo."""
        try:
            last_input = LASTINPUTINFO()
            last_input.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(last_input)):
                return 0.0
            tick_count = ctypes.windll.kernel32.GetTickCount()
            return max((tick_count - last_input.dwTime) / 1000.0, 0.0)
        except Exception as exc:
            logger.warning("Failed to read idle duration: %s", exc)
            return 0.0


@dataclass
class IdleDetector:
    """Detects transitions into idle state."""

    provider: IdleProvider
    idle_threshold_seconds: float
    was_idle: bool = False

    def sample(self) -> tuple[IdleSnapshot, ObserverEvent | None]:
        """Return current idle state and optional idle_detected event."""
        idle_seconds = self.provider.get_idle_seconds()
        is_idle = idle_seconds >= self.idle_threshold_seconds
        observed_at = utc_now()
        snapshot = IdleSnapshot(
            idle_seconds=idle_seconds,
            is_idle=is_idle,
            observed_at=observed_at,
        )

        event = None
        if is_idle and not self.was_idle:
            event = ObserverEvent(
                event_type=IDLE_DETECTED,
                payload={"idle_seconds": round(idle_seconds, 2)},
                created_at=observed_at,
            )

        self.was_idle = is_idle
        return snapshot, event
