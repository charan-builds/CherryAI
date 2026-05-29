"""Knowledge Center page for documents, screenshots, code, and notes."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from backend.code_intelligence_engine.schemas import ProjectSummary
from backend.document_intelligence_engine.schemas import DocumentAnalysis
from backend.screen_intelligence_engine.schemas import ScreenAnalysis
from backend.service_registry import ServiceRegistry
from frontend.knowledge.knowledge_worker import KnowledgeAnalysisWorker


class DocumentViewerPanel(QFrame):
    """Document path input and extracted preview."""

    analyze_requested = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("KnowledgePanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title = QLabel("Document Viewer")
        title.setObjectName("PanelTitle")
        self.path_input = QLineEdit()
        self.path_input.setObjectName("KnowledgePathInput")
        self.path_input.setPlaceholderText("PDF, notes, or text file path")
        self.analyze_button = QPushButton("Analyze")
        self.analyze_button.setObjectName("TaskPrimaryButton")
        self.analyze_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.preview_label = QLabel("No document loaded.")
        self.preview_label.setObjectName("KnowledgeText")
        self.preview_label.setWordWrap(True)

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(self.path_input, stretch=1)
        row.addWidget(self.analyze_button)

        layout.addWidget(title)
        layout.addLayout(row)
        layout.addWidget(self.preview_label)

        self.analyze_button.clicked.connect(self._emit_request)

    def update_analysis(self, analysis: DocumentAnalysis) -> None:
        """Render parsed document content."""
        self.preview_label.setText(
            f"{analysis.title}\n"
            f"Pages: {analysis.page_count} | Words: {analysis.summary.word_count}\n"
            f"{analysis.text[:420]}"
        )

    def _emit_request(self) -> None:
        path = self.path_input.text().strip()
        if path:
            self.analyze_requested.emit(path)


class SummaryPanel(QFrame):
    """Shared summary and concept panel."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("KnowledgePanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        title = QLabel("Summary")
        title.setObjectName("PanelTitle")
        self.summary_label = QLabel("Knowledge summaries will appear here.")
        self.summary_label.setObjectName("KnowledgeText")
        self.summary_label.setWordWrap(True)
        self.concepts_label = QLabel("Concepts: none")
        self.concepts_label.setObjectName("PanelSubtitle")
        self.concepts_label.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.concepts_label)

    def update_document(self, analysis: DocumentAnalysis) -> None:
        """Render a document summary."""
        self.summary_label.setText(analysis.summary.summary)
        self.concepts_label.setText("Concepts: " + ", ".join(analysis.key_concepts))

    def update_screen(self, analysis: ScreenAnalysis) -> None:
        """Render a screenshot summary."""
        self.summary_label.setText(analysis.explanation)
        self.concepts_label.setText("Context: " + analysis.context.category)

    def update_project(self, summary: ProjectSummary) -> None:
        """Render a project summary."""
        self.summary_label.setText(summary.architecture_summary)
        self.concepts_label.setText("Languages: " + ", ".join(summary.languages))


class ScreenshotExplanationPanel(QFrame):
    """Screenshot OCR and explanation panel."""

    analyze_requested = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("KnowledgePanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title = QLabel("Screenshot Explanation")
        title.setObjectName("PanelTitle")
        self.path_input = QLineEdit()
        self.path_input.setObjectName("KnowledgePathInput")
        self.path_input.setPlaceholderText("Screenshot path")
        self.analyze_button = QPushButton("Explain")
        self.analyze_button.setObjectName("TaskSecondaryButton")
        self.analyze_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ocr_label = QLabel("No screenshot loaded.")
        self.ocr_label.setObjectName("KnowledgeText")
        self.ocr_label.setWordWrap(True)

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(self.path_input, stretch=1)
        row.addWidget(self.analyze_button)

        layout.addWidget(title)
        layout.addLayout(row)
        layout.addWidget(self.ocr_label)

        self.analyze_button.clicked.connect(self._emit_request)

    def update_analysis(self, analysis: ScreenAnalysis) -> None:
        """Render screenshot OCR and explanation."""
        elements = ", ".join(analysis.ui_elements) or "none"
        self.ocr_label.setText(
            f"{analysis.explanation}\n"
            f"UI: {elements}\n"
            f"OCR: {analysis.extracted_text[:360]}"
        )

    def _emit_request(self) -> None:
        path = self.path_input.text().strip()
        if path:
            self.analyze_requested.emit(path)


class CodeProjectPanel(QFrame):
    """Project architecture summary panel."""

    analyze_requested = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("KnowledgePanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title = QLabel("Code Context")
        title.setObjectName("PanelTitle")
        self.path_input = QLineEdit()
        self.path_input.setObjectName("KnowledgePathInput")
        self.path_input.setPlaceholderText("Project folder path")
        self.analyze_button = QPushButton("Summarize")
        self.analyze_button.setObjectName("TaskSecondaryButton")
        self.analyze_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.summary_label = QLabel("No project loaded.")
        self.summary_label.setObjectName("KnowledgeText")
        self.summary_label.setWordWrap(True)

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(self.path_input, stretch=1)
        row.addWidget(self.analyze_button)

        layout.addWidget(title)
        layout.addLayout(row)
        layout.addWidget(self.summary_label)

        self.analyze_button.clicked.connect(self._emit_request)

    def update_summary(self, summary: ProjectSummary) -> None:
        """Render code project summary."""
        self.summary_label.setText(summary.architecture_summary)

    def _emit_request(self) -> None:
        path = self.path_input.text().strip()
        if path:
            self.analyze_requested.emit(path)


class NotesWorkspacePanel(QFrame):
    """Workspace for saving notes into knowledge memory."""

    save_requested = pyqtSignal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("KnowledgePanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title = QLabel("Notes Workspace")
        title.setObjectName("PanelTitle")
        self.title_input = QLineEdit()
        self.title_input.setObjectName("KnowledgePathInput")
        self.title_input.setPlaceholderText("Note title")
        self.notes_edit = QTextEdit()
        self.notes_edit.setObjectName("KnowledgeNotesInput")
        self.notes_edit.setPlaceholderText("Notes")
        self.save_button = QPushButton("Save Notes")
        self.save_button.setObjectName("TaskPrimaryButton")
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)

        layout.addWidget(title)
        layout.addWidget(self.title_input)
        layout.addWidget(self.notes_edit)
        layout.addWidget(self.save_button)

        self.save_button.clicked.connect(self._emit_request)

    def _emit_request(self) -> None:
        title = self.title_input.text().strip() or "Knowledge Notes"
        text = self.notes_edit.toPlainText().strip()
        if text:
            self.save_requested.emit(title, text)


class KnowledgeHistoryPanel(QFrame):
    """Recent knowledge memory records."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("KnowledgePanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        title = QLabel("Knowledge History")
        title.setObjectName("PanelTitle")
        self.history_label = QLabel("No knowledge memories yet.")
        self.history_label.setObjectName("KnowledgeText")
        self.history_label.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(self.history_label)

    def update_history(self, services: ServiceRegistry) -> None:
        """Render recent knowledge memories."""
        memories = services.knowledge_memory.list_recent(limit=6)
        if not memories:
            self.history_label.setText("No knowledge memories yet.")
            return
        self.history_label.setText(
            "\n".join(f"{item.title} | {item.source_type}" for item in memories)
        )


class KnowledgeCenterPage(QFrame):
    """Knowledge Intelligence Layer frontend surface."""

    def __init__(self, services: ServiceRegistry) -> None:
        super().__init__()
        self.services = services
        self.workers: list[KnowledgeAnalysisWorker] = []
        self.setObjectName("KnowledgeCenterPage")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(12)

        self.document_viewer = DocumentViewerPanel()
        self.summary_panel = SummaryPanel()
        self.screenshot_panel = ScreenshotExplanationPanel()
        self.code_panel = CodeProjectPanel()
        self.notes_workspace = NotesWorkspacePanel()
        self.history_panel = KnowledgeHistoryPanel()
        self.status_label = QLabel("Knowledge Center ready.")
        self.status_label.setObjectName("PanelSubtitle")

        scroll = QScrollArea()
        scroll.setObjectName("TaskScrollArea")
        scroll.setWidgetResizable(True)
        viewport = QWidget()
        viewport.setObjectName("TaskScrollViewport")
        grid = QGridLayout(viewport)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.addWidget(self.document_viewer, 0, 0)
        grid.addWidget(self.summary_panel, 0, 1)
        grid.addWidget(self.screenshot_panel, 1, 0)
        grid.addWidget(self.code_panel, 1, 1)
        grid.addWidget(self.notes_workspace, 2, 0)
        grid.addWidget(self.history_panel, 2, 1)
        scroll.setWidget(viewport)

        root_layout.addWidget(scroll)
        root_layout.addWidget(self.status_label)

        self.document_viewer.analyze_requested.connect(
            lambda path: self._start_analysis("document", path)
        )
        self.screenshot_panel.analyze_requested.connect(
            lambda path: self._start_analysis("screenshot", path)
        )
        self.code_panel.analyze_requested.connect(
            lambda path: self._start_analysis("project", path)
        )
        self.notes_workspace.save_requested.connect(self._save_notes)
        self.refresh()

    def refresh(self) -> None:
        """Refresh knowledge history."""
        self.history_panel.update_history(self.services)

    def _start_analysis(self, mode: str, path: str) -> None:
        worker = KnowledgeAnalysisWorker(self.services, mode, path)
        worker.completed.connect(self._handle_analysis_completed)
        worker.failed.connect(self._handle_analysis_failed)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        self.workers.append(worker)
        self.status_label.setText(f"Analyzing {mode}...")
        worker.start()

    def _handle_analysis_completed(self, mode: str, result: object) -> None:
        if mode == "document" and isinstance(result, DocumentAnalysis):
            self.document_viewer.update_analysis(result)
            self.summary_panel.update_document(result)
            self.services.knowledge_memory.store_summary(
                source_type="document",
                source_name=result.document_path,
                title=result.title,
                summary=result.summary.summary,
                notes=result.notes,
                concepts=result.key_concepts,
                tags=result.context.tags,
            )
        elif mode == "screenshot" and isinstance(result, ScreenAnalysis):
            self.screenshot_panel.update_analysis(result)
            self.summary_panel.update_screen(result)
            self.services.knowledge_memory.store_summary(
                source_type="screenshot",
                source_name=result.image_path,
                title="Screenshot Explanation",
                summary=result.explanation,
                notes=(result.study_explanation,),
                concepts=result.context.topics,
                tags=result.context.tags,
            )
        elif mode == "project" and isinstance(result, ProjectSummary):
            self.code_panel.update_summary(result)
            self.summary_panel.update_project(result)
            self.services.knowledge_memory.store_summary(
                source_type="code_project",
                source_name=result.root_path,
                title="Project Architecture",
                summary=result.architecture_summary,
                notes=result.important_files,
                concepts=result.languages,
                tags=("code", "project"),
            )
        self.status_label.setText("Knowledge analysis complete.")
        self.refresh()

    def _handle_analysis_failed(self, message: str) -> None:
        self.status_label.setText(f"Knowledge analysis failed: {message}")

    def _save_notes(self, title: str, text: str) -> None:
        lines = tuple(line.strip() for line in text.splitlines() if line.strip())
        self.services.knowledge_memory.store_notes(
            source_name="notes_workspace",
            title=title,
            notes=lines or (text,),
        )
        self.status_label.setText("Notes saved to knowledge memory.")
        self.refresh()

    def _cleanup_worker(self, worker: KnowledgeAnalysisWorker) -> None:
        if worker in self.workers:
            self.workers.remove(worker)
        worker.deleteLater()
