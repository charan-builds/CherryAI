"""Dashboard page for the assistant workspace."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout

from backend.observer_engine.schemas import ObserverStatus
from frontend.widgets.chat_display import ChatDisplayArea
from frontend.widgets.command_input import CommandInputArea


class DashboardPage(QFrame):
    """Primary assistant workspace with chat and command input."""

    command_submitted = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("DashboardPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.chat_display = ChatDisplayArea()
        self.command_input = CommandInputArea()
        self.command_input.submitted.connect(self.command_submitted.emit)
        self.observer_summary = QLabel("Activity: waiting for observer")
        self.observer_summary.setObjectName("DashboardObserverSummary")

        layout.addWidget(self.observer_summary)
        layout.addWidget(self.chat_display, stretch=1)
        layout.addWidget(self.command_input)

    def add_startup_message(self) -> None:
        """Add the initial system message."""
        self.chat_display.add_system_message(
            "Cherry AI interface is online. Local database and logging are ready."
        )

    def add_user_message(self, message: str) -> None:
        """Append a user message to the chat."""
        self.chat_display.add_user_message(message)

    def add_assistant_message(self, message: str) -> None:
        """Append an assistant message to the chat."""
        self.chat_display.add_assistant_message(message)

    def show_loading(self, message: str) -> None:
        """Show loading state in the chat and input."""
        self.chat_display.show_loading(message)
        self.command_input.set_loading(True)

    def hide_loading(self) -> None:
        """Hide loading state in the chat and input."""
        self.chat_display.hide_loading()
        self.command_input.set_loading(False)

    def update_observer_summary(self, status: ObserverStatus) -> None:
        """Update dashboard activity summary."""
        state = "idle" if status.is_idle else "active"
        self.observer_summary.setText(
            f"Activity: {status.active_app} | {state} | "
            f"Focus {int(status.focus_seconds)}s"
        )
