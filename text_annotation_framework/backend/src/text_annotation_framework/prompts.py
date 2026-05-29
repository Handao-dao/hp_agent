from text_annotation_framework.profiles import AnnotationProfile

SYSTEM_PROMPT = """
You are a generic text annotation engine.

Return valid JSON only. Do not use Markdown or code fences.

The output JSON must have this shape:
{
  "annotations": [
    {
      "surface": "exact text span from the input",
      "label": "short label or explanation",
      "type": "keyword | term | phrase | entity | concept",
      "context": "short source context",
      "start_index": 0,
      "end_index": 10,
      "metadata": {}
    }
  ],
  "metadata": {}
}

Rules:
- Preserve the original input text. Do not rewrite it.
- Every surface must appear exactly in the input text.
- Prefer spans that matter to the selected profile.
- Keep labels concise.
- Use character indexes when you can determine them. If unsure, use null.
- Do not invent facts not supported by the text.
""".strip()


def build_user_prompt(text: str, profile: AnnotationProfile, options: dict | None = None) -> str:
    option_text = options or {}
    return f"""
Profile: {profile.label}
Allowed annotation types: {", ".join(profile.annotation_types)}

Profile instructions:
{profile.instructions}

Options:
{option_text}

Input text:
<text>
{text}
</text>
""".strip()
