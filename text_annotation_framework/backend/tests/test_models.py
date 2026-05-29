from text_annotation_framework.models import Annotation, AnnotationResult, Document, TextChunk


def test_schema_defaults_and_serialization():
    document = Document(text="hello", metadata={"source": "test"})
    chunk = TextChunk(index=1, text="hello", start_index=0, end_index=5)
    annotation = Annotation(surface="hello", label="你好")
    result = AnnotationResult(original_text=document.text, annotations=[annotation])

    payload = result.model_dump()

    assert document.metadata["source"] == "test"
    assert chunk.index == 1
    assert payload["annotations"][0]["type"] == "keyword"
    assert payload["annotations"][0]["metadata"] == {}
