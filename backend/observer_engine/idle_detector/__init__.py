"""Idle detection."""

from backend.observer_engine.idle_detector.service import (
    IdleDetector,
    IdleProvider,
    WindowsIdleProvider,
)

__all__ = ["IdleDetector", "IdleProvider", "WindowsIdleProvider"]
