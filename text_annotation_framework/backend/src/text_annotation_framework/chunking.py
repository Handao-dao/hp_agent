import re

from text_annotation_framework.models import TextChunk


class TextChunker:
    """按自然段组合 chunk，尽量不在句子或段落中间切开文本。"""

    def __init__(self, min_chunk_words: int = 120, max_chunk_words: int = 280):
        self.min_chunk_words = min_chunk_words
        self.max_chunk_words = max_chunk_words

    def split(self, text: str) -> list[TextChunk]:
        """返回带原文位置的 chunk，方便后续把局部标注映射回全文。"""

        clean_text = text.strip()
        if not clean_text:
            return []

        paragraphs = self._paragraph_spans(clean_text)
        chunks: list[TextChunk] = []
        current_parts: list[tuple[str, int, int]] = []
        current_words = 0

        for paragraph, start, end in paragraphs:
            word_count = len(paragraph.split())
            if current_parts and current_words + word_count > self.max_chunk_words:
                chunks.append(self._make_chunk(len(chunks) + 1, current_parts))
                current_parts = [(paragraph, start, end)]
                current_words = word_count
            else:
                current_parts.append((paragraph, start, end))
                current_words += word_count

            if current_words >= self.min_chunk_words:
                chunks.append(self._make_chunk(len(chunks) + 1, current_parts))
                current_parts = []
                current_words = 0

        if current_parts:
            chunks.append(self._make_chunk(len(chunks) + 1, current_parts))

        return chunks

    def _paragraph_spans(self, text: str) -> list[tuple[str, int, int]]:
        """识别段落及其在全文中的字符范围。"""

        spans = []
        for match in re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\Z)", text, flags=re.S):
            paragraph = match.group(0).strip()
            if paragraph:
                leading_offset = len(match.group(0)) - len(match.group(0).lstrip())
                start = match.start() + leading_offset
                end = start + len(paragraph)
                spans.append((paragraph, start, end))
        return spans

    def _make_chunk(self, index: int, parts: list[tuple[str, int, int]]) -> TextChunk:
        """把相邻段落打包成一个 chunk，并保留整体字符范围。"""

        text = "\n\n".join(part[0] for part in parts)
        return TextChunk(
            index=index,
            text=text,
            start_index=parts[0][1],
            end_index=parts[-1][2],
        )
