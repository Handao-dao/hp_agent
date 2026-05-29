from typing import Any, Literal

from pydantic import BaseModel, Field

AnnotationType = Literal["keyword", "term", "phrase", "entity", "concept"]
EventType = Literal["start", "progress", "chunk_completed", "completed", "error"]


class Document(BaseModel):
    """完整输入文档；metadata 用来承载调用方自己的来源、标题等信息。"""

    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class TextChunk(BaseModel):
    """长文本切分后的处理单元，索引位置仍然指向原始文档。"""

    index: int
    text: str
    start_index: int
    end_index: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class Annotation(BaseModel):
    """单个标注项，是框架最核心的可复用数据结构。"""

    surface: str
    label: str
    type: AnnotationType = "keyword"
    context: str = ""
    start_index: int | None = None
    end_index: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnnotationResult(BaseModel):
    """一次标注任务的最终结果；annotations 是主数据，annotated_text 仅作兼容展示。"""

    original_text: str
    annotations: list[Annotation] = Field(default_factory=list)
    annotated_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnnotationEvent(BaseModel):
    """流式处理事件，用同一结构表达进度、分块结果和最终完成状态。"""

    type: EventType
    current: int | None = None
    total: int | None = None
    chunk_index: int | None = None
    result: AnnotationResult | None = None
    message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
