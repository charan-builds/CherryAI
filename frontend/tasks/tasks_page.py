"""Task management page."""

from __future__ import annotations

import logging

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from backend.task_engine.service import TaskEngine
from frontend.widgets.task_card import TaskCard
from frontend.widgets.task_filters import TaskFilterBar
from frontend.widgets.task_form import TaskFormWidget
from frontend.widgets.task_summary import TaskSummaryWidget

logger = logging.getLogger(__name__)


class TasksPage(QFrame):
    """Functional task management workspace."""

    status_message = pyqtSignal(str)

    def __init__(self, task_engine: TaskEngine) -> None:
        super().__init__()
        self.task_engine = task_engine
        self.task_cards: list[TaskCard] = []
        self.setObjectName("TasksPage")

        self.form = TaskFormWidget()
        self.summary = TaskSummaryWidget()
        self.filter_bar = TaskFilterBar()
        self.empty_label = QLabel("No tasks match the current filters.")
        self.empty_label.setObjectName("TaskEmptyLabel")
        self.empty_label.setWordWrap(True)

        self._build_layout()
        self._connect_signals()
        self.refresh_tasks()

    def refresh_tasks(self) -> None:
        """Reload persisted tasks and redraw the list."""
        status_filter, priority_filter = self.filter_bar.current_filters()
        tasks = self.task_engine.list_tasks(
            status_filter=status_filter,
            priority_filter=priority_filter,
        )

        self._clear_task_cards()
        for task in tasks:
            card = TaskCard(task)
            card.completion_changed.connect(self._set_task_completion)
            card.delete_requested.connect(self._delete_task)
            self.task_list_layout.insertWidget(
                self.task_list_layout.count() - 1,
                card,
            )
            self.task_cards.append(card)

        self.empty_label.setVisible(not tasks)
        self._refresh_summary()
        logger.info("Loaded %s tasks for filter %s/%s", len(tasks), status_filter, priority_filter)

    def _build_layout(self) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(12)

        left_column = QVBoxLayout()
        left_column.setSpacing(12)
        left_column.addWidget(self.form)
        left_column.addWidget(self.summary)
        left_column.addStretch(1)

        left_panel = QFrame()
        left_panel.setObjectName("TaskSidePanel")
        left_panel.setFixedWidth(340)
        left_panel.setLayout(left_column)

        list_panel = QFrame()
        list_panel.setObjectName("TaskListPanel")
        list_layout = QVBoxLayout(list_panel)
        list_layout.setContentsMargins(16, 16, 16, 16)
        list_layout.setSpacing(12)

        title = QLabel("Task List")
        title.setObjectName("PanelTitle")

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("TaskScrollArea")
        self.scroll_area.setWidgetResizable(True)

        self.scroll_viewport = QWidget()
        self.scroll_viewport.setObjectName("TaskScrollViewport")

        self.task_list_layout = QVBoxLayout(self.scroll_viewport)
        self.task_list_layout.setContentsMargins(0, 0, 0, 0)
        self.task_list_layout.setSpacing(10)
        self.task_list_layout.addWidget(self.empty_label)
        self.task_list_layout.addStretch(1)

        self.scroll_area.setWidget(self.scroll_viewport)

        list_layout.addWidget(title)
        list_layout.addWidget(self.filter_bar)
        list_layout.addWidget(self.scroll_area, stretch=1)

        root_layout.addWidget(left_panel)
        root_layout.addWidget(list_panel, stretch=1)

    def _connect_signals(self) -> None:
        self.form.task_created.connect(self._create_task)
        self.filter_bar.filter_changed.connect(lambda *_: self.refresh_tasks())
        self.filter_bar.refresh_requested.connect(self.refresh_tasks)

    def _create_task(self, title: str, description: str, priority: str) -> None:
        try:
            task = self.task_engine.create_task(title, description, priority)
        except ValueError as exc:
            self.status_message.emit(str(exc))
            return

        self.status_message.emit(f"Task created: {task.title}")
        self.refresh_tasks()
        self.form.focus_title()

    def _set_task_completion(self, task_id: str, completed: bool) -> None:
        if completed:
            task = self.task_engine.complete_task(task_id)
            self.status_message.emit(f"Completed: {task.title}")
        else:
            task = self.task_engine.reopen_task(task_id)
            self.status_message.emit(f"Reopened: {task.title}")

        self.refresh_tasks()

    def _delete_task(self, task_id: str) -> None:
        self.task_engine.delete_task(task_id)
        self.status_message.emit("Task deleted")
        self.refresh_tasks()

    def _refresh_summary(self) -> None:
        self.summary.update_summary(
            statistics=self.task_engine.get_statistics(),
            daily_summary=self.task_engine.generate_daily_summary(),
        )

    def _clear_task_cards(self) -> None:
        for card in self.task_cards:
            self.task_list_layout.removeWidget(card)
            card.deleteLater()
        self.task_cards.clear()
