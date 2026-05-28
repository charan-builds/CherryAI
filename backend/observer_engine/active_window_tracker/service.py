"""Active window tracking service."""

from __future__ import annotations

import ctypes
import logging
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from database.models import utc_now
from backend.observer_engine.observer_event_bus.events import APP_CHANGED, ObserverEvent
from backend.observer_engine.schemas import WindowSnapshot

logger = logging.getLogger(__name__)


class ActiveWindowProvider(Protocol):
    """Provider interface for active window snapshots."""

    def get_active_window(self) -> WindowSnapshot:
        """Return the current active window."""


class WindowsActiveWindowProvider:
    """Windows foreground-window provider using ctypes."""

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    def get_active_window(self) -> WindowSnapshot:
        """Read active app and title from Windows APIs."""
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            title = self._get_window_title(hwnd)
            app_name = self._get_process_name(hwnd)
        except Exception as exc:
            logger.warning("Failed to read active window: %s", exc)
            title = "Unavailable"
            app_name = "Unknown"

        return WindowSnapshot(
            application_name=app_name or "Unknown",
            window_title=title or "",
            observed_at=utc_now(),
        )

    def _get_window_title(self, hwnd: int) -> str:
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value

    def _get_process_name(self, hwnd: int) -> str:
        process_id = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))

        handle = ctypes.windll.kernel32.OpenProcess(
            self.PROCESS_QUERY_LIMITED_INFORMATION,
            False,
            process_id.value,
        )
        if not handle:
            return "Unknown"

        try:
            buffer = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(len(buffer))
            ok = ctypes.windll.kernel32.QueryFullProcessImageNameW(
                handle,
                0,
                buffer,
                ctypes.byref(size),
            )
            if not ok:
                return "Unknown"
            return Path(buffer.value).name or "Unknown"
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)


@dataclass
class ActiveWindowTracker:
    """Tracks active window changes and emits app_changed events."""

    provider: ActiveWindowProvider
    last_snapshot: WindowSnapshot | None = None

    def sample(self) -> tuple[WindowSnapshot, ObserverEvent | None]:
        """Return current active window and optional change event."""
        snapshot = self.provider.get_active_window()
        if self.last_snapshot is None:
            self.last_snapshot = snapshot
            return snapshot, ObserverEvent(
                event_type=APP_CHANGED,
                payload=self._event_payload(snapshot),
                created_at=snapshot.observed_at,
            )

        changed = (
            self.last_snapshot.application_name != snapshot.application_name
            or self.last_snapshot.window_title != snapshot.window_title
        )
        self.last_snapshot = snapshot

        if not changed:
            return snapshot, None

        return snapshot, ObserverEvent(
            event_type=APP_CHANGED,
            payload=self._event_payload(snapshot),
            created_at=snapshot.observed_at,
        )

    def _event_payload(self, snapshot: WindowSnapshot) -> dict[str, object]:
        return {
            "application_name": snapshot.application_name,
            "window_title": snapshot.window_title,
        }
