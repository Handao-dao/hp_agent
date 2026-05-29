from text_annotation_framework.chunking import TextChunker


def test_chunker_returns_empty_for_blank_text():
    assert TextChunker().split("   ") == []


def test_chunker_preserves_paragraph_spans():
    text = "First paragraph has context.\n\nSecond paragraph has metadata."

    chunks = TextChunker(min_chunk_words=100, max_chunk_words=100).split(text)

    assert len(chunks) == 1
    assert chunks[0].start_index == 0
    assert chunks[0].end_index == len(text)


def test_chunker_splits_long_paragraph_groups():
    text = "one two three\n\nfour five six\n\nseven eight nine"

    chunks = TextChunker(min_chunk_words=4, max_chunk_words=5).split(text)

    assert len(chunks) >= 2
    assert chunks[0].index == 1
