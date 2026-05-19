import json
import re


def sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def extract_json(response: str) -> dict:
    """从 LLM 响应中提取 JSON 对象"""
    response = response.strip()

    # 优先尝试直接解析
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # 非贪婪正则兜底：匹配第一个完整 JSON 对象（正确处理嵌套花括号）
    json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", response, re.DOTALL)
    if not json_match:
        raise ValueError(f"无法从响应中提取 JSON。\n完整响应: {response}")

    json_str = json_match.group(0)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 解析失败: {e}\n提取内容: {json_str}")
