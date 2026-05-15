import json
import re
from typing import List, Dict
from dataclasses import dataclass

from hello_agents import HelloAgentsLLM, SimpleAgent
from hello_agents.tools import ToolRegistry

# 1. 定义数据结构
@dataclass
class VocabItem:
    word: str
    translation: str
    context: str

@dataclass
class AnnotationResult:
    annotated_text: str
    vocabulary: List[VocabItem]

# 2. 系统提示词预设
ANNOTATOR_SYSTEM_PROMPT = """
# Role
You are an expert English-Chinese reading assistant specialized in the Harry Potter series.

Your job is to help Chinese readers understand real reading obstacles in Harry Potter, especially British colloquial expressions, everyday object and tool vocabulary, wizarding-world terms, idioms, phrasal verbs, tone words, and context-dependent meanings, while preserving the original reading experience.

# Task
You will receive one English paragraph or several English paragraphs.

You must:
1. Identify words or expressions that may confuse the target English learner.
2. Insert a short Chinese translation using the [[word|translation]] format.
3. Extract the identified vocabulary into a separate vocabulary list.

# Annotation Rules
1. Preserve the original text exactly. Do not rewrite, summarize, reorder, or correct the input text.
2. Only insert Chinese translations using the [[word|translation]] format after selected words or expressions.
3. Annotation format must be:
   [[word|中文]]
   [[phrase|中文翻译]]
   Use double square brackets, English word or phrase, pipe character |, Chinese translation.
   Do NOT use parentheses for annotations. ONLY use the [[word|translation]] format.
   Do NOT include the pipe character | inside the word or translation text.
4. The Chinese translation must match the exact meaning in context.
   - "spell" in a magical context should be translated as "咒语", not "拼写".
   - "bark" should be translated according to context, such as "树皮" or "狗叫".
   - "Sickle" in Harry Potter currency context should be translated as "西可", not "镰刀".
5. Keep translations concise. Prefer 1-4 Chinese characters. For proper nouns or magical terms, up to 6 Chinese characters is acceptable.
6. Follow the reader-level rules to decide whether a word or expression is worth annotating.
7. Prioritize real reading obstacles for Chinese readers: British slang, colloquial dialogue, everyday object/tool/household vocabulary, Harry Potter-specific magical terms, idioms, phrasal verbs, fixed expressions, tone-bearing words, and common-looking words with special meanings in context, such as spell, charm, house, prefect, trunk, sort, bark, and Sickle.
8. Do not annotate ordinary character names, such as Harry, Ron, Hermione, Dumbledore, Hagrid, unless the name itself is being explained as a title, place, spell, object, or special concept.
9. If a phrase is the real difficult unit, annotate the whole phrase instead of a single word.
   Example:
   "[[put up with|忍受]]"
   not "[[put|放]] [[up|上]] [[with|和]]"
10. If the same word appears multiple times in the text, you may annotate it each time in annotated_text, but include it only once in extracted_vocabulary.
11. In extracted_vocabulary, use the base form of the word.
   - "wands" -> "wand"
   - "whispered" -> "whisper"
   - "creatures" -> "creature"
12. For proper nouns and Harry Potter terms, keep the standard capitalization in the vocabulary list.
13. If there are no words worth annotating, return the original text and an empty vocabulary list.

# Context Rules
1. Translation must be based strictly on the sentence context.
2. Do not hallucinate meanings that are not supported by the text.
3. Do not add background explanations inside annotated_text.
4. The annotation inside the text should be short. Longer explanation can be left to another agent.

# Output Rules
You must output valid JSON only.
Do not output Markdown.
Do not wrap the JSON in code fences.
Do not add explanations before or after the JSON.
Use double quotes for all JSON keys and string values.
Do not use trailing commas.

# Output Format
{
  "annotated_text": "Original text with concise Chinese annotations inserted.",
  "extracted_vocabulary": [
    {
      "word": "base form or phrase",
      "translation": "中文翻译",
      "context": "short context from the original sentence"
    }
  ]
}
""".strip()


# 分级的用户提示词
LEVEL_PROFILES = {
    "beginner": {
        "label": "a beginner English learner, roughly A1-A2 level",
        "rules": (
            "Annotate frequently enough to help a beginner understand the text, "
            "but do not annotate every content word. "
            "Skip only very common function words and very basic everyday vocabulary. "
            "Annotate most content words beyond A1-A2 level, especially unfamiliar nouns, verbs, adjectives, and adverbs. "
            "Annotate all idioms, phrasal verbs, fixed expressions, British slang, culturally specific expressions, "
            "and Harry Potter or wizarding-world terms that may affect understanding. "
            "For idioms and phrasal verbs, annotate the whole expression rather than individual words. "
            "Avoid repeated annotations of the same word within the same passage unless the meaning changes. "
            "Target annotation density: relatively high, about 25%-40% of meaningful content words."
        ),
    },

    "intermediate": {
        "label": "an intermediate English learner, roughly B1-B2 level",
        "rules": (
            "Do not annotate A1-B1 high-frequency vocabulary that an intermediate learner should know. "
            "Focus on B2+ vocabulary, uncommon verbs, descriptive adjectives, adverbs with subtle meanings, "
            "less common nouns, literary words, and words whose meaning depends strongly on context. "
            "Annotate Harry Potter-specific magical terms, wizarding-world jargon, British slang, culturally specific expressions, "
            "idioms, and phrasal verbs whose meaning is not obvious from the individual words. "
            "For idioms, phrasal verbs, and fixed expressions, annotate the whole expression rather than separate words. "
            "Avoid repeated annotations of the same word within the same passage unless necessary. "
            "Target annotation density: moderate, about 8%-18% of meaningful content words."
        ),
    },

    "advanced": {
        "label": "an advanced English learner, roughly C1-C2 level",
        "rules": (
            "Annotate only words or expressions that may challenge an advanced or near-fluent English reader. "
            "Do not annotate ordinary descriptive adjectives, common adverbs, common phrasal verbs, common idioms, "
            "or standard academic vocabulary. "
            "Focus only on truly rare, archaic, literary, metaphorical, dialectal, culturally specific, or contextually subtle expressions. "
            "Annotate Harry Potter or wizarding-world terms only if they are obscure, important for understanding the sentence, "
            "or appear for the first time as a key term. "
            "For complex literary expressions, annotate the whole phrase when appropriate rather than isolated words. "
            "When in doubt, do not annotate. "
            "Target annotation density: low, about 2%-6% of meaningful content words."
        ),
    },
}

# 用户提示词模板
ANNOTATOR_USER_PROMPT_TEMPLATE = """
Please annotate the following text for {level_label}.

# Annotation Level Rules
{level_rules}

Mastered words:
{mastered_words}

Rules for mastered words:
- Do not annotate any word or expression listed in mastered_words.
- If mastered_words is empty, ignore this section.

Original text:
<text>
{text}
</text>

Return valid JSON only.
""".strip()

# 3. 核心服务类
class AnnotatorService:
    def __init__(self, llm):
        self._agent = SimpleAgent( 
            name="HP Annotator",
            system_prompt=ANNOTATOR_SYSTEM_PROMPT,
            llm=llm
        )
    
    def annotate_text(self, text: str, mastered_words: List[str] = None, level: str = "intermediate") -> AnnotationResult:
        """处理文本并返回带有翻译的文本和生词本"""
        mastered_words = mastered_words or []
        profile = LEVEL_PROFILES.get(level, LEVEL_PROFILES["intermediate"])
        mastered_str = json.dumps(mastered_words, ensure_ascii=False)
        user_prompt = ANNOTATOR_USER_PROMPT_TEMPLATE.format(
            level_label=profile["label"],
            level_rules=profile["rules"],
            mastered_words=mastered_str,
            text=text
        )
        
        # 调用 Agent（关闭 v4-pro 思考模式以提速）
        response = self._agent.run(
            user_prompt,
            extra_body={"thinking": {"type": "disabled"}}
        )
        
        # 解析 JSON
        parsed_payload = self._extract_json(response)
        
        # 验证并创建返回对象
        vocab_items = []
        for item in parsed_payload.get("extracted_vocabulary", []):
            vocab_items.append(
                VocabItem(
                    word=item.get("word", ""),
                    translation=item.get("translation", ""),
                    context=item.get("context", "")
                )
            )
            
        return AnnotationResult(
            annotated_text=parsed_payload.get("annotated_text", text), # fallback 为原文本
            vocabulary=vocab_items
        )
    
    def _extract_json(self, response: str) -> dict:
        """从 Agent 响应中提取 JSON 对象 (Dict)"""
        # 这里提取第一个 { 到最后一个 } 之间的内容
		# json.loads再把提取的内容转换成py字典，分为annotated_text 和 extracted_vocabulary两个部分
        response = response.strip()

		# 优先尝试直接解析完整响应。只有完整解析失败，才用正则兜底。
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if not json_match:
            raise ValueError(f"无法从响应中提取 JSON。\n完整响应: {response}")

        json_str = json_match.group(0)

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析失败: {e}\nAgent 返回内容: {json_str}")