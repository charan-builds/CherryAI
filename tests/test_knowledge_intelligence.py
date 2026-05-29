import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from backend.code_intelligence_engine.service import CodeIntelligenceEngine
from backend.content_summarization_engine.service import ContentSummarizationEngine
from backend.context_understanding_engine.service import ContextUnderstandingEngine
from backend.document_intelligence_engine.service import DocumentIntelligenceEngine
from backend.screen_intelligence_engine.service import ScreenIntelligenceEngine
from database.init_db import initialize_database
from frontend.knowledge.knowledge_center_page import KnowledgeCenterPage
from backend.service_registry import build_services
from tests.helpers import make_test_settings


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_pdf_parsing_tests(tmp_path):
    pdf_path = tmp_path / "ml_notes.pdf"
    pdf_path.write_bytes(
        b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /Contents 4 0 R >> endobj
4 0 obj << /Length 98 >> stream
BT /F1 12 Tf 72 720 Td (Machine Learning probability revision notes explain classification models.) Tj ET
endstream endobj
%%EOF"""
    )
    engine = DocumentIntelligenceEngine()

    analysis = engine.analyze_document(pdf_path)

    assert "Machine Learning" in analysis.text
    assert analysis.page_count == 1
    assert analysis.context.category == "machine_learning"
    assert analysis.key_concepts


def test_ocr_tests(tmp_path):
    image_path = tmp_path / "screen.png"
    image_path.write_bytes(b"fake image bytes")
    PathSidecar = tmp_path / "screen.png.txt"
    PathSidecar.write_text(
        "Dashboard button shows Probability Revision practice and Start focus timer.",
        encoding="utf-8",
    )
    engine = ScreenIntelligenceEngine()

    analysis = engine.analyze_screenshot(image_path)

    assert "Probability Revision" in analysis.extracted_text
    assert "button" in analysis.ui_elements
    assert analysis.context.category in {"study_material", "productivity", "user_interface"}


def test_code_explanation_tests(tmp_path):
    code_path = tmp_path / "service.py"
    code_path.write_text(
        """
import json
from pathlib import Path


class StudyPlanner:
    def create_plan(self):
        return ["Open notes", "Practice probability"]


def summarize_topic(topic):
    return topic.upper()
""",
        encoding="utf-8",
    )
    engine = CodeIntelligenceEngine()

    analysis = engine.analyze_file(code_path)
    walkthrough = engine.walkthrough_file(code_path)

    assert analysis.language == "Python"
    assert "StudyPlanner" in analysis.classes
    assert "summarize_topic" in analysis.functions
    assert "Defines classes" in walkthrough.steps[1]


def test_summarization_tests():
    text = (
        "Machine learning uses datasets to train models. "
        "Regression predicts continuous values from examples. "
        "Classification predicts labels and needs evaluation metrics. "
        "Practice notes should capture probability assumptions."
    )
    engine = ContentSummarizationEngine()

    summary = engine.summarize(text)

    assert "Machine learning" in summary.summary
    assert summary.word_count >= 20
    assert "Regression" in summary.key_concepts
    assert summary.notes


def test_context_classification_tests():
    engine = ContextUnderstandingEngine()

    analysis = engine.classify(
        "Machine learning model training uses dataset probability and classification.",
        source_type="document",
    )

    assert analysis.category == "machine_learning"
    assert "machine_learning" in analysis.tags
    assert "Probability" in analysis.study_topics


def test_knowledge_memory_persists_and_links_semantic_memory(tmp_path):
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    services = build_services(settings)

    record = services.knowledge_memory.store_summary(
        source_type="document",
        source_name="ml_notes.pdf",
        title="ML Notes",
        summary="Probability and classification revision notes.",
        notes=("Review probability assumptions.",),
        concepts=("Probability", "Classification"),
        tags=("machine_learning", "notes"),
    )

    memories = services.knowledge_memory.list_recent()

    assert memories[0].id == record.id
    assert memories[0].semantic_memory_id
    assert "Probability" in memories[0].concepts


def test_knowledge_center_ui_rendering(tmp_path):
    app = _app()
    settings = make_test_settings(tmp_path)
    initialize_database(settings)
    services = build_services(settings)

    page = KnowledgeCenterPage(services=services)
    page.notes_workspace.title_input.setText("Probability Notes")
    page.notes_workspace.notes_edit.setPlainText("Review Bayes theorem.")
    page.notes_workspace.save_button.click()
    app.processEvents()

    assert "Probability Notes" in page.history_panel.history_label.text()
