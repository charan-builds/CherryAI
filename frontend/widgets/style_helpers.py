"""Small Qt styling helpers."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget


def refresh_style(widget: QWidget) -> None:
    """Re-apply QSS after dynamic properties change."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
