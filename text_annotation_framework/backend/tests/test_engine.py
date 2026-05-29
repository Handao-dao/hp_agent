from text_annotation_framework.engine import TextAnnotationEngine
from text_annotation_framework.llm import MockLLMClient
from text_annotation_framework.profiles import default_profile_registry


def test_engine_annotates_single_text_with_mock_llm():
    engine = TextAnnotationEngine(MockLLMClient(), default_profile_registry())

    result = engine.annotate("The resilient framework recovered after a timeout.")

    assert result.original_text.startswith("The resilient")
    assert any(item.surface.lower() == "resilient" for item in result.annotations)
    assert result.annotated_text is not None
    assert result.metadata["profile"] == "english_reading"


def test_engine_returns_empty_result_for_empty_text():
    engine = TextAnnotationEngine(MockLLMClient(), default_profile_registry())

    result = engine.annotate("   ")

    assert result.original_text == ""
    assert result.annotations == []
    assert result.annotated_text == ""
