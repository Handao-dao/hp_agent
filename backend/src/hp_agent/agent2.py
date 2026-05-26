"""
点击查词服务 (WordLookupService)。

独立于批注流程，仅在用户点击单词时触发。每次请求 LLM 做两件事：
1. 单词的上下文感知翻译（词级）
2. 所在句子的整体翻译（句级）

与 AnnotatorService 完全解耦：独立系统提示词、独立 temperature、独立调用时机。
"""

import os

from hello_agents import HelloAgentsLLM, SimpleAgent

from hp_agent.utils import extract_json

# WordLookupService 系统提示词：英汉词典角色，输出严格 JSON
LOOKUP_SYSTEM_PROMPT = """
# Role
You are an expert English-Chinese dictionary and translation assistant specialized in the Harry Potter series.

Your job is to help Chinese readers understand a specific English word in context. You receive one word and the sentence containing it. You provide a concise Chinese translation of the word and a natural Chinese translation of the entire sentence.

# Task
You will receive:
1. A single English word or short phrase
2. One English sentence that contains this word

You must:
1. Translate the word accurately according to its context in the sentence.
2. Translate the entire sentence into natural Chinese.

# Rules
1. Word translation must match the exact meaning in context.
   - "spell" in a magical context → "咒语", not "拼写".
   - "bark" → "树皮" or "狗叫" depending on context.
   - "Sickle" in Harry Potter → "西可", not "镰刀".
2. Keep the word translation concise. Prefer 1-4 Chinese characters.
3. The sentence translation should be natural Chinese, preserving the original meaning and tone.
4. Do not add explanations, notes, or commentary.

# Output Rules
You must output valid JSON only.
Do not output Markdown.
Do not wrap the JSON in code fences.
Use double quotes for all JSON keys and string values.

# Output Format
{
  "word": "the original word",
  "word_cn": "中文翻译",
  "sentence_cn": "整句中文翻译"
}
""".strip()

# 用户提示词模板：注入 word 和 sentence
LOOKUP_USER_PROMPT_TEMPLATE = """
Word: {word}

Sentence:
<text>
{sentence}
</text>

Return valid JSON only.
""".strip()


class WordLookupService:
    """点击查词 Agent，给定单词 + 所在句子，返回词翻译和句翻译。"""

    def __init__(self, llm: HelloAgentsLLM):
        self._agent = SimpleAgent(
            name="Word Lookup",
            system_prompt=LOOKUP_SYSTEM_PROMPT,
            llm=llm
        )

    def _json_retry_count(self) -> int:
        try:
            return max(0, int(os.getenv("LOOKUP_JSON_RETRY", "1")))
        except ValueError:
            return 1

    def lookup(self, word: str, sentence: str) -> dict:
        """
        执行查词。关闭 thinking mode 以加速响应。
        返回 {"word", "word_cn", "sentence_cn"}。
        """
        user_prompt = LOOKUP_USER_PROMPT_TEMPLATE.format(
            word=word,
            sentence=sentence
        )
        last_error = None

        for attempt in range(self._json_retry_count() + 1):
            prompt = user_prompt
            if attempt > 0:
                prompt += (
                    "\n\nYour previous response was not valid JSON. "
                    "Return the lookup result again as valid JSON only."
                )

            response = self._agent.run(
                prompt,
                extra_body={"thinking": {"type": "disabled"}}
            )

            try:
                return extract_json(response)
            except ValueError as exc:
                last_error = exc

        raise last_error or ValueError("LLM did not return valid JSON")
