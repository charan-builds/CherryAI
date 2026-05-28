"""Scrollable chat response panel."""

from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class MessageBubble(QFrame):
    """A reusable chat message bubble."""

    def __init__(self, role: str, title: str, body: str) -> None:
        super().__init__()
        self.setObjectName("MessageBubble")
        self.setProperty("role", role)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("MessageTitle")

        body_label = QLabel(body)
        body_label.setObjectName("MessageBody")
        body_label.setWordWrap(True)
        body_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        layout.addWidget(title_label)
        layout.addWidget(body_label)


class ScrollableResponsePanel(QFrame):
    """Scroll area that owns chat messages and loading placeholders."""

    def __init__(self) -> None:
        super().__init__()
        self.loading_bubble: MessageBubble | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("ResponseScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.viewport = QWidget()
        self.viewport.setObjectName("ResponseViewport")

        self.message_layout = QVBoxLayout(self.viewport)
        self.message_layout.setContentsMargins(0, 0, 0, 0)
        self.message_layout.setSpacing(12)
        self.message_layout.addStretch(1)

        self.scroll_area.setWidget(self.viewport)
        layout.addWidget(self.scroll_area)

    def add_message(self, role: str, title: str, body: str) -> MessageBubble:
        """Append a message and scroll to it."""
        bubble = MessageBubble(role=role, title=title, body=body)
        self.message_layout.insertWidget(self.message_layout.count() - 1, bubble)
        self._scroll_to_bottom_later()
        return bubble

    def add_system_message(self, body: str) -> MessageBubble:
        """Append a system message."""
        return self.add_message("system", "System", body)

    def show_loading(self, message: str = "Cherry AI is thinking...") -> None:
        """Show a temporary loading message."""
        self.hide_loading()
        self.loading_bubble = self.add_message("loading", "Cherry AI", message)

    def hide_loading(self) -> None:
        """Remove the loading message if present."""
        if self.loading_bubble is None:
            return

        self.message_layout.removeWidget(self.loading_bubble)
        self.loading_bubble.deleteLater()
        self.loading_bubble = None

    def clear(self) -> None:
        """Remove all messages from the panel."""
        self.hide_loading()
        while self.message_layout.count() > 1:
            item = self.message_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _scroll_to_bottom_later(self) -> None:
        QTimer.singleShot(0, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        scroll_bar = self.scroll_area.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())
