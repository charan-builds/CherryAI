from backend.memory_classifier.schemas import (
    MEMORY_BEHAVIORAL,
    MEMORY_EPISODIC,
    MEMORY_SEMANTIC,
    MEMORY_WORKING,
    MemoryClassificationInput,
)
from backend.memory_classifier.service import MemoryClassifier


def test_memory_classifier_detects_supported_categories():
    classifier = MemoryClassifier()

    episodic = classifier.classify(
        MemoryClassificationInput(
            text="Completed study session on NumPy.",
            source_type="study_session",
        )
    )
    behavioral = classifier.classify("The user loses focus after 45 minutes.")
    semantic = classifier.classify("The user prefers studying ML at night.")
    working = classifier.classify(
        MemoryClassificationInput(
            text="Current active study session is linear algebra.",
            source_type="active_session",
        )
    )

    assert episodic.category == MEMORY_EPISODIC
    assert behavioral.category == MEMORY_BEHAVIORAL
    assert semantic.category == MEMORY_SEMANTIC
    assert working.category == MEMORY_WORKING
    assert all(item.confidence > 0 for item in (episodic, behavioral, semantic, working))
