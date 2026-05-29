from hp_agent.settings_store import DEFAULT_BASE_URL, DEFAULT_MODEL_ID, SettingsStore


def test_settings_store_reports_unconfigured_without_env(tmp_path, monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    store = SettingsStore(str(tmp_path))
    status = store.get_public_status()

    assert status["configured"] is False
    assert status["api_key_masked"] == ""
    assert status["model_id"] == DEFAULT_MODEL_ID
    assert status["base_url"] == DEFAULT_BASE_URL
    assert status["source"] == "none"


def test_settings_store_persists_ui_key_and_masks_status(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-env-key")

    store = SettingsStore(str(tmp_path))
    store.save_llm_settings(
        api_key="sk-ui-1234567890",
        base_url="https://example.test",
        timeout=90,
        temperature=0.1,
    )

    effective = store.get_effective_llm_settings()
    status = store.get_public_status()

    assert effective["api_key"] == "sk-ui-1234567890"
    assert effective["model_id"] == DEFAULT_MODEL_ID
    assert effective["base_url"] == "https://example.test"
    assert effective["source"] == "ui"
    assert status["configured"] is True
    assert status["api_key_masked"] == "sk-u...7890"
