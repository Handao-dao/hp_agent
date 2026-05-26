import pytest

from hp_agent.utils import extract_json


def test_extract_json_parses_plain_json():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_parses_markdown_wrapped_nested_json():
    payload = """```json
{"a": {"b": 2}, "items": [{"word": "spell"}]}
```"""

    assert extract_json(payload) == {
        "a": {"b": 2},
        "items": [{"word": "spell"}],
    }


def test_extract_json_ignores_braces_inside_strings():
    payload = 'prefix {"text": "brace } inside", "value": {"ok": true}} suffix'

    assert extract_json(payload) == {
        "text": "brace } inside",
        "value": {"ok": True},
    }


def test_extract_json_raises_when_no_object_exists():
    with pytest.raises(ValueError):
        extract_json("no json here")
