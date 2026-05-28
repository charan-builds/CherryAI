"""Chat display area."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout

from frontend.widgets.response_panel import ScrollableResponsePanel


class ChatDisplayArea(QFrame):
    """Panel containing chat heading and scrollable response history."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("ChatDisplayArea")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Assistant Console")
        title.setObjectName("PanelTitle")

        subtitle = QLabel("Placeholder interactions are local and ready for model wiring.")
        subtitle.setObjectName("PanelSubtitle")

        self.response_panel = ScrollableResponsePanel()

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.response_panel, stretch=1)

    def add_user_message(self, body: str) -> None:
        """Append a user message."""
        self.response_panel.add_message("user", "You", body)

    def add_assistant_message(self, body: str) -> None:
        """Append an assistant message."""
        self.response_panel.add_message("assistant", "Cherry AI", body)

    def add_system_message(self, body: str) -> None:
        """Append a system message."""
        self.response_panel.add_system_message(body)

    def show_loading(self, message: str) -> None:
        """Show a loading placeholder."""
        self.response_panel.show_loading(message)

    def hide_loading(self) -> None:
        """Hide the loading placeholder."""
        self.response_panel.hide_loading()
