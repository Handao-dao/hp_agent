from text_annotation_framework.json_utils import extract_json_object
from text_annotation_framework.llm import LLMClient
from text_annotation_framework.models import Annotation, AnnotationResult
from text_annotation_framework.profiles import ProfileRegistry


class TextAnnotationEngine:
    """通用标注引擎：选择 profile、调用 LLM、解析 JSON、归一化结果。"""

    def __init__(
        self,
        llm: LLMClient,
        profiles: ProfileRegistry,
        json_retry_count: int = 1,
    ):
        self.llm = llm
        self.profiles = profiles
        self.json_retry_count = json_retry_count

    def annotate(
        self,
        text: str,
        profile: str = "english_reading",
        options: dict | None = None,
    ) -> AnnotationResult:
        """处理单段文本；长文本并发和流式输出由 StreamingAnnotationService 负责。"""

        clean_text = text.strip()
        if not clean_text:
            return AnnotationResult(
                original_text="",
                annotations=[],
                annotated_text="",
                metadata={},
            )

        selected_profile = self.profiles.get_or_default(profile)
        parsed_payload = None
        last_error = None

        for _attempt in range(self.json_retry_count + 1):
            try:
                response = self.llm.annotate(clean_text, selected_profile, options)
                parsed_payload = extract_json_object(response)
                break
            except Exception as exc:
                last_error = exc

        if parsed_payload is None:
            raise ValueError("LLM did not return valid annotation JSON") from last_error

        annotations = [
            self._normalize_annotation(item, clean_text)
            for item in parsed_payload.get("annotations", [])
            if isinstance(item, dict)
        ]
        annotations = [item for item in annotations if item is not None]

        return AnnotationResult(
            original_text=clean_text,
            annotations=annotations,
            annotated_text=self._to_inline_text(clean_text, annotations),
            metadata={
                "profile": selected_profile.key,
                **parsed_payload.get("metadata", {}),
            },
        )

    def _normalize_annotation(self, item: dict, text: str) -> Annotation | None:
        """把 LLM 的宽松 JSON 输出收敛为框架内部稳定 schema。"""

        surface = str(item.get("surface", "")).strip()
        label = str(item.get("label", "")).strip()
        if not surface or not label:
            return None

        start_index = item.get("start_index")
        end_index = item.get("end_index")

        if not isinstance(start_index, int) or not isinstance(end_index, int):
            # LLM 偶尔会漏掉位置；这里用 surface 做一次保守回填。
            found_at = text.find(surface)
            if found_at >= 0:
                start_index = found_at
                end_index = found_at + len(surface)
            else:
                start_index = None
                end_index = None

        if isinstance(start_index, int) and isinstance(end_index, int):
            if start_index < 0 or end_index > len(text) or start_index >= end_index:
                start_index = None
                end_index = None

        annotation_type = item.get("type", "keyword")
        if annotation_type not in {"keyword", "term", "phrase", "entity", "concept"}:
            annotation_type = "keyword"

        return Annotation(
            surface=surface,
            label=label,
            type=annotation_type,
            context=str(item.get("context", "")),
            start_index=start_index,
            end_index=end_index,
            metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
        )

    def _to_inline_text(self, text: str, annotations: list[Annotation]) -> str:
        """生成旧式 [[surface|label]] 文本，方便兼容已有 inline marker 渲染方式。"""

        positioned = [
            item
            for item in annotations
            if item.start_index is not None and item.end_index is not None
        ]
        positioned.sort(key=lambda item: (item.start_index, -(item.end_index - item.start_index)))

        result = []
        cursor = 0
        for item in positioned:
            start = item.start_index
            end = item.end_index
            if start is None or end is None or start < cursor:
                # 重叠标注先跳过，结构化 annotations 里仍然保留完整信息。
                continue
            result.append(text[cursor:start])
            result.append(f"[[{text[start:end]}|{item.label}]]")
            cursor = end
        result.append(text[cursor:])
        return "".join(result)
