"""
文档处理服务：文本切分 + 并行 LLM 标注 + SSE 流式推送。

核心流程：
1. _split_paragraphs：按空行切分段落
2. _pack_paragraphs：将短段落合并为 300 词以内的 chunk
3. process_chapter_stream：asyncio.Semaphore(3) 并行请求 LLM，
   按完成顺序推送进度，按原始顺序组装结果

去重策略：同一单词的不同大小写形式归一化（lower），首次出现保留原文形式。
"""

import asyncio
import re
from collections.abc import AsyncGenerator

from hp_agent.utils import sse_event


class DocumentProcessor:
    def __init__(
        self,
        annotator_service,
        min_chunk_words: int = 150,
        max_chunk_words: int = 300,
        max_concurrency: int = 3
    ):
        """
        annotator_service: AnnotatorService 实例
        min_chunk_words: 尽量把过短段落合并到这个词数以上
        max_chunk_words: 单次送给 Agent 的最大词数，避免上下文过长
        max_concurrency: 并行处理 chunk 的最大并发数，避免 API 限流
        """
        self.annotator = annotator_service
        self.min_chunk_words = min_chunk_words
        self.max_chunk_words = max_chunk_words
        self.max_concurrency = max_concurrency

    def _normalize_quotes(self, text: str) -> str:
        """将中文引号和标点替换为英文对应符号，避免 LLM 输出格式不一致。"""
        if not text:
            return text

        return (
            text
            .replace("“", '"')
            .replace("”", '"')        
            .replace("‘", "'")
            .replace("’", "'")
            .replace("，", ",")
            .replace("。", ".")
        )

    async def process_chapter_stream(
    self,
    long_text: str,
    mastered_words: list[str] | None = None,
    level: str = "intermediate"
) -> AsyncGenerator[str, None]:
        """
        并行流式处理整章文本。

        SSE 事件：
        1. start：告诉前端总块数
        2. progress：每完成一个 chunk 发送进度
        3. completed：所有 chunk 完成后发送完整 annotated_text
        """

        mastered_words = mastered_words or []

        paragraphs = self._split_paragraphs(long_text)
        chunks = self._pack_paragraphs(paragraphs)

        total_chunks = len(chunks)

        yield sse_event({
            "type": "start",
            "total": total_chunks
        })

        if total_chunks == 0:
            yield sse_event({
                "type": "completed",
                "annotated_text": "",
                "total_vocab": []
            })
            return

        # 并行处理所有 chunk，Semaphore 控制并发上限
        sem = asyncio.Semaphore(self.max_concurrency)

        async def process_one(idx: int, chunk_text: str):
            async with sem:
                try:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.annotator.annotate_text,
                            chunk_text,
                            mastered_words,
                            level
                        ),
                        timeout=120.0
                    )
                    annotated = self._normalize_quotes(result.annotated_text or chunk_text)
                    return (idx, annotated, result.vocabulary, None)
                except asyncio.CancelledError:
                    raise
                except TimeoutError:
                    print(f"第 {idx} 个文本块处理超时，降级返回原文本")
                    fallback = self._normalize_quotes(chunk_text)
                    return (idx, fallback, [], "timeout")
                except Exception as e:
                    print(f"第 {idx} 个文本块处理失败，降级返回原文本: {e}")
                    fallback = self._normalize_quotes(chunk_text)
                    return (idx, fallback, [], str(e))

        tasks = [
            process_one(idx, text)
            for idx, text in enumerate(chunks, start=1)
        ]

        # 按完成顺序接收结果，仅发送进度事件
        results: dict[int, tuple] = {}
        completed_count = 0

        for coro in asyncio.as_completed(tasks):
            idx, annotated, vocab, error = await coro
            completed_count += 1
            results[idx] = (annotated, vocab, error)

            yield sse_event({
                "type": "progress",
                "current": completed_count,
                "total": total_chunks
            })

        # 按 chunk 原始顺序组装最终结果
        unique_vocabulary: dict[str, dict] = {}
        annotated_parts: list[str] = []

        for idx in sorted(results.keys()):
            annotated, vocab, error = results[idx]
            annotated_parts.append(annotated)

            if not error:
                for v in vocab:
                    word = v.word.strip()
                    if not word:
                        continue
                    normalized_key = word.lower()
                    if normalized_key not in unique_vocabulary:
                        unique_vocabulary[normalized_key] = {
                            "word": word,
                            "translation": v.translation.strip(),
                            "context": v.context.strip()
                        }

        full_annotated_text = "\n\n".join(annotated_parts)

        yield sse_event({
            "type": "completed",
            "annotated_text": full_annotated_text,
            "total_vocab": list(unique_vocabulary.values())
        })

    def _split_paragraphs(self, text: str) -> list[str]:
        """按自然段切分文本"""

        text = text.strip()

        if not text:
            return []

        # 兼容 Windows / Linux 换行
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 优先按空行切分；如果没有空行，则退化为按单行切分
        if "\n\n" in text:
            paragraphs = re.split(r"\n\s*\n+", text)
        else:
            paragraphs = text.split("\n")

        return [p.strip() for p in paragraphs if p.strip()]

    def _pack_paragraphs(self, paragraphs: list[str]) -> list[str]:
        """
        将短段落合并成适合 LLM 处理的 chunk。

        合并策略：
        - 逐段累加，超过 max_chunk_words 时封包
        - 达到 min_chunk_words 时提前封包，避免 chunk 过小
        - 单个超长段落独占一个 chunk（不在语义中间截断）
        这样可以减少 LLM 调用次数并降低短对话被跳过的风险。
        """

        chunks = []
        current_parts = []
        current_words = 0

        for paragraph in paragraphs:
            word_count = len(paragraph.split())

            if current_words + word_count > self.max_chunk_words and current_parts:
                chunks.append("\n\n".join(current_parts))
                current_parts = [paragraph]
                current_words = word_count
            else:
                current_parts.append(paragraph)
                current_words += word_count

            if current_words >= self.min_chunk_words:
                chunks.append("\n\n".join(current_parts))
                current_parts = []
                current_words = 0

        if current_parts:
            chunks.append("\n\n".join(current_parts))

        return chunks
