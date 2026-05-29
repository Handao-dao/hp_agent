import json
import os
import re
from typing import Protocol

import httpx

from text_annotation_framework.profiles import AnnotationProfile
from text_annotation_framework.prompts import SYSTEM_PROMPT, build_user_prompt


class LLMClient(Protocol):
    """所有 LLM adapter 只需实现这个最小协议。"""

    def annotate(self, text: str, profile: AnnotationProfile, options: dict | None = None) -> str:
        ...


class MockLLMClient:
    """本地确定性 annotator：让 demo 和测试在没有 API Key 时也能跑通。"""

    _profile_terms = {
        "english_reading": {
            "resilient": "有韧性的",
            "timeout": "超时",
            "context": "上下文",
            "annotate": "标注",
            "obstacle": "障碍",
            "recover": "恢复",
            "recovered": "恢复",
        },
        "technical_terms": {
            "api": "接口",
            "configuration": "配置",
            "timeout": "超时",
            "streaming": "流式",
            "schema": "模式",
            "metadata": "元数据",
        },
        "general_keywords": {
            "framework": "框架",
            "annotation": "标注",
            "keywords": "关键词",
            "context": "上下文",
            "metadata": "元数据",
        },
    }

    def annotate(self, text: str, profile: AnnotationProfile, options: dict | None = None) -> str:
        """模拟 LLM 返回 JSON 字符串，便于复用真实解析链路。"""

        terms = self._profile_terms.get(profile.key, self._profile_terms["general_keywords"])
        annotations = []
        seen = set()
        for surface, label in terms.items():
            pattern = re.compile(rf"\b{re.escape(surface)}\b", re.IGNORECASE)
            match = pattern.search(text)
            if not match:
                continue
            key = match.group(0).lower()
            if key in seen:
                continue
            seen.add(key)
            annotations.append(
                {
                    "surface": match.group(0),
                    "label": label,
                    "type": "term" if profile.key == "technical_terms" else "keyword",
                    "context": _context_window(text, match.start(), match.end()),
                    "start_index": match.start(),
                    "end_index": match.end(),
                    "metadata": {"source": "mock"},
                }
            )

        return json.dumps(
            {"annotations": annotations, "metadata": {"llm": "mock"}},
            ensure_ascii=False,
        )


class OpenAICompatibleClient:
    """OpenAI 兼容 chat-completions adapter。"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 60,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def annotate(self, text: str, profile: AnnotationProfile, options: dict | None = None) -> str:
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(text, profile, options)},
                ],
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]


def create_llm_client_from_env() -> LLMClient:
    """有 LLM_API_KEY 时使用真实接口，否则退回 mock client。"""

    api_key = os.getenv("LLM_API_KEY", "").strip()
    if not api_key:
        return MockLLMClient()
    return OpenAICompatibleClient(
        api_key=api_key,
        base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        model=os.getenv("LLM_MODEL_ID", "gpt-4.1-mini"),
        timeout=float(os.getenv("LLM_TIMEOUT", "60")),
    )


def _context_window(text: str, start: int, end: int, radius: int = 48) -> str:
    return text[max(0, start - radius) : min(len(text), end + radius)].strip()
