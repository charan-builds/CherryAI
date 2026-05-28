"""Simple local notification coordinator."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


class NotificationCenter(QObject):
    """Routes lightweight UI notifications.

    This class is intentionally small today. Later it can bridge toast widgets,
    system tray notifications, or the planned floating assistant widget.
    """

    notification_emitted = pyqtSignal(str, str)

    def notify(self, level: str, message: str) -> None:
        """Emit a local notification."""
        self.notification_emitted.emit(level, message)
