import json
import os
import threading
from pathlib import Path

DEFAULT_MODEL_ID = "deepseek-v4-pro"
DEFAULT_BASE_URL = "https://api.deepseek.com"


class SettingsStore:
    def __init__(self, data_dir: str):
        self._data_dir = Path(data_dir)
        self._path = self._data_dir / "app_settings.json"
        self._lock = threading.RLock()
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def _read_file(self) -> dict:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def save_llm_settings(
        self,
        api_key: str,
        base_url: str | None = None,
        timeout: int | None = None,
        temperature: float | None = None,
    ) -> dict:
        with self._lock:
            data = self._read_file()
            data["llm"] = {
                "api_key": api_key.strip(),
                "model_id": DEFAULT_MODEL_ID,
                "base_url": (base_url or DEFAULT_BASE_URL).strip(),
                "timeout": timeout,
                "temperature": temperature,
            }
            self._path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return data["llm"]

    def get_llm_settings(self) -> dict:
        with self._lock:
            data = self._read_file()
            return data.get("llm", {})

    def get_effective_llm_settings(self) -> dict:
        saved = self.get_llm_settings()
        api_key = saved.get("api_key") or os.getenv("LLM_API_KEY", "")
        base_url = saved.get("base_url") or os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL)
        model_id = DEFAULT_MODEL_ID

        timeout = saved.get("timeout")
        if timeout is None:
            timeout = int(os.getenv("LLM_TIMEOUT", "60"))

        temperature = saved.get("temperature")
        if temperature is None:
            temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))

        if saved.get("api_key"):
            source = "ui"
        elif os.getenv("LLM_API_KEY"):
            source = "env"
        else:
            source = "none"

        return {
            "api_key": api_key,
            "base_url": base_url,
            "model_id": model_id,
            "timeout": timeout,
            "temperature": temperature,
            "source": source,
        }

    def get_public_status(self) -> dict:
        settings = self.get_effective_llm_settings()
        api_key = settings.get("api_key", "")
        masked_key = ""
        if api_key:
            masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "已配置"

        return {
            "configured": bool(api_key),
            "api_key_masked": masked_key,
            "model_id": settings["model_id"],
            "base_url": settings["base_url"],
            "timeout": settings["timeout"],
            "temperature": settings["temperature"],
            "source": settings["source"],
        }
