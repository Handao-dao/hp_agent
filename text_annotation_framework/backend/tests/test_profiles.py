import pytest

from text_annotation_framework.profiles import default_profile_registry


def test_default_profiles_are_registered():
    registry = default_profile_registry()

    assert registry.get("english_reading").label == "English Reading"
    assert registry.get("technical_terms").key == "technical_terms"
    assert "general_keywords" in registry.keys()


def test_unknown_profile_raises():
    registry = default_profile_registry()

    with pytest.raises(KeyError):
        registry.get("missing")


def test_get_or_default_falls_back():
    registry = default_profile_registry()

    assert registry.get_or_default("missing").key == "english_reading"
