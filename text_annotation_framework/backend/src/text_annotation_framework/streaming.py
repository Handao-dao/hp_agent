import asyncio
from collections.abc import AsyncGenerator

from text_annotation_framework.chunking import TextChunker
from text_annotation_framework.engine import TextAnnotationEngine
from text_annotation_framework.models import Annotation, AnnotationEvent, AnnotationResult


class StreamingAnnotationService:
    """长文本流式服务：切分文本、并发标注、按事件输出进度和结果。"""

    def __init__(
        self,
        engine: TextAnnotationEngine,
        chunker: TextChunker | None = None,
        max_concurrency: int = 3,
        timeout_seconds: float = 120,
    ):
        self.engine = engine
        self.chunker = chunker or TextChunker()
        self.max_concurrency = max_concurrency
        self.timeout_seconds = timeout_seconds

    async def annotate_stream(
        self,
        text: str,
        profile: str = "english_reading",
        options: dict | None = None,
    ) -> AsyncGenerator[AnnotationEvent, None]:
        """流式标注入口；调用者可以直接把事件转成 SSE、WebSocket 或 CLI 输出。"""

        chunks = self.chunker.split(text)
        total = len(chunks)

        yield AnnotationEvent(type="start", current=0, total=total)

        if total == 0:
            yield AnnotationEvent(
                type="completed",
                current=0,
                total=0,
                result=AnnotationResult(original_text="", annotated_text="", annotations=[]),
            )
            return

        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def process_chunk(chunk):
            async with semaphore:
                try:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(self.engine.annotate, chunk.text, profile, options),
                        timeout=self.timeout_seconds,
                    )
                    shifted = [
                        _shift_annotation(annotation, chunk.start_index)
                        for annotation in result.annotations
                    ]
                    return chunk.index, result.model_copy(update={"annotations": shifted}), None
                except Exception as exc:
                    fallback = AnnotationResult(
                        original_text=chunk.text,
                        annotated_text=chunk.text,
                        annotations=[],
                        metadata={"error": str(exc)},
                    )
                    return chunk.index, fallback, str(exc)

        tasks = [process_chunk(chunk) for chunk in chunks]
        results = {}
        completed = 0

        for task in asyncio.as_completed(tasks):
            # 按完成顺序推送 chunk 进度，最终结果再按原始顺序合并。
            index, result, error = await task
            completed += 1
            results[index] = result
            yield AnnotationEvent(
                type="chunk_completed",
                current=completed,
                total=total,
                chunk_index=index,
                result=result,
                message=error,
            )
            yield AnnotationEvent(type="progress", current=completed, total=total)

        merged_annotations: list[Annotation] = []
        annotated_parts: list[str] = []
        for index in sorted(results):
            result = results[index]
            merged_annotations.extend(result.annotations)
            annotated_parts.append(result.annotated_text or result.original_text)

        yield AnnotationEvent(
            type="completed",
            current=total,
            total=total,
            result=AnnotationResult(
                original_text=text.strip(),
                annotated_text="\n\n".join(annotated_parts),
                annotations=_dedupe_annotations(merged_annotations),
                metadata={"profile": profile, "chunks": total},
            ),
        )


def _shift_annotation(annotation: Annotation, offset: int) -> Annotation:
    """把 chunk 内局部坐标平移回原始全文坐标。"""

    if annotation.start_index is None or annotation.end_index is None:
        return annotation
    return annotation.model_copy(
        update={
            "start_index": annotation.start_index + offset,
            "end_index": annotation.end_index + offset,
        }
    )


def _dedupe_annotations(annotations: list[Annotation]) -> list[Annotation]:
    """去掉完全重复的标注项，保留同一 surface 在不同位置的出现。"""

    seen = set()
    unique = []
    for annotation in annotations:
        key = (
            annotation.surface.lower(),
            annotation.label,
            annotation.type,
            annotation.start_index,
            annotation.end_index,
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(annotation)
    return unique
