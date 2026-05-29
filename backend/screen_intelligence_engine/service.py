"""OCR extraction and screenshot explanation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from config.settings import AppSettings
from backend.content_summarization_engine.service import ContentSummarizationEngine
from backend.context_understanding_engine.service import ContextUnderstandingEngine
from backend.screen_intelligence_engine.schemas import ScreenAnalysis


@dataclass
class ScreenIntelligenceEngine:
    """Understands screenshots using optional OCR plus deterministic fallback."""

    settings: AppSettings | None = None
    summarizer: ContentSummarizationEngine | None = None
    context_engine: ContextUnderstandingEngine | None = None

    def __post_init__(self) -> None:
        self.summarizer = self.summarizer or ContentSummarizationEngine()
        self.context_engine = self.context_engine or ContextUnderstandingEngine()

    def analyze_screenshot(self, image_path: str | Path) -> ScreenAnalysis:
        """Extract visible text and explain the screen."""
        path = Path(image_path)
        text = self.extract_ocr_text(path)
        context = self.context_engine.classify(text, source_type="screenshot")
        summary = self.summarizer.summarize(text)
        ui_elements = self.detect_ui_elements(text)
        explanation = self._screen_explanation(summary.summary, ui_elements)
        return ScreenAnalysis(
            image_path=str(path),
            extracted_text=text,
            explanation=explanation,
            ui_elements=tuple(ui_elements),
            study_explanation=self._study_explanation(context, summary.key_concepts),
            context=context,
        )

    def extract_ocr_text(self, image_path: str | Path) -> str:
        """Extract OCR text, preferring deterministic sidecar files in tests."""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Screenshot not found: {path}")

        sidecar_text = self._read_sidecar_text(path)
        if sidecar_text:
            return sidecar_text

        ocr_text = self._extract_with_tesseract(path)
        if ocr_text:
            return ocr_text

        if path.suffix.lower() in {".txt", ".md"}:
            return self._normalize(path.read_text(encoding="utf-8", errors="ignore"))
        return ""

    def detect_ui_elements(self, text: str) -> list[str]:
        """Detect common UI controls from OCR text."""
        lowered = (text or "").lower()
        checks = {
            "button": ("button", "submit", "cancel", "save", "start", "open"),
            "menu": ("menu", "file", "edit", "view", "settings"),
            "form": ("name", "email", "password", "input", "field"),
            "navigation": ("sidebar", "dashboard", "home", "back", "next"),
            "study_content": ("chapter", "lecture", "problem", "practice", "revision"),
        }
        detected = []
        for label, keywords in checks.items():
            if any(keyword in lowered for keyword in keywords):
                detected.append(label)
        return detected

    def _read_sidecar_text(self, path: Path) -> str:
        candidates = [
            Path(f"{path}.txt"),
            path.with_suffix(".txt"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return self._normalize(candidate.read_text(encoding="utf-8", errors="ignore"))
        return ""

    def _extract_with_tesseract(self, path: Path) -> str:
        try:
            from PIL import Image  # type: ignore
            import pytesseract  # type: ignore
        except Exception:
            return ""

        try:
            return self._normalize(pytesseract.image_to_string(Image.open(path)))
        except Exception:
            return ""

    def _screen_explanation(self, summary: str, ui_elements: list[str]) -> str:
        controls = ", ".join(ui_elements) if ui_elements else "no obvious controls"
        return f"The screen appears to show {controls}. {summary}"

    def _study_explanation(
        self,
        context,
        key_concepts: tuple[str, ...],
    ) -> str:
        if context.study_topics:
            return "Study topics detected: " + ", ".join(context.study_topics)
        if key_concepts:
            return "Important visible concepts: " + ", ".join(key_concepts[:5])
        return "No study-specific content was detected."

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()
