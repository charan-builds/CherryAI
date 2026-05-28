"""Memory engine.

Long-term memory will live behind this interface. The first implementation is
small so database-backed memory can be added without changing UI code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from config.settings import AppSettings


@dataclass
class MemoryEngine:
    """Stores and retrieves assistant memory."""

    settings: AppSettings
    _items: list[str] = field(default_factory=list)

    def remember(self, item: str) -> None:
        """Store a memory item in the current process."""
        self._items.append(item)

    def recent(self, limit: int = 10) -> list[str]:
        """Return recent memory items."""
        return self._items[-limit:]
