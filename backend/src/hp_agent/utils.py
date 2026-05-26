"""
hp_agent 公共工具：SSE 事件格式化和 LLM 响应 JSON 提取。
"""

import json


def sse_event(payload: dict) -> str:
    """将 dict 序列化为 SSE 标准格式：data: {...}\n\n"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _find_first_json_object(text: str) -> str | None:
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escaped = False

        for idx in range(start, len(text)):
            char = text[idx]

            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start:idx + 1]

        start = text.find("{", start + 1)

    return None


def extract_json(response: str) -> dict:
    """
    从 LLM 原始响应中提取 JSON 对象。

    LLM 有时在 JSON 前后附加说明文字或 markdown 代码块，
    需要先尝试直接解析，失败后扫描第一个完整 JSON 对象。
    """
    response = response.strip()

    # 优先：直接解析（LLM 按要求只输出 JSON 时的快速路径）
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    json_str = _find_first_json_object(response)
    if not json_str:
        raise ValueError(f"无法从响应中提取 JSON。\n完整响应: {response}")

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 解析失败: {e}\n提取内容: {json_str}") from e
