import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


class Configuration(BaseModel):
    """
    HP-Agent MVP 配置文件。

    当前阶段只接入 DeepSeek，但环境变量命名保持为 LLM_*，
    方便以后换成其他 OpenAI-compatible 模型。
    """

    app_name: str = Field(default="HP-Agent Backend")
    app_env: str = Field(default="dev")
    debug: bool = Field(default=True)

    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)

    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173"
    )

    llm_model_id: str = Field(default="deepseek-chat")
    llm_api_key: Optional[str] = Field(default=None)
    llm_base_url: str = Field(default="https://api.deepseek.com")
    llm_timeout: int = Field(default=60)
    llm_temperature: float = Field(default=0.2)

    min_chunk_words: int = Field(default=60)
    max_chunk_words: int = Field(default=180)

    data_dir: str = Field(default="./data")
    vocab_db_path: str = Field(default="./data/harry_potter_vocab.db")

    annotator_json_retry: int = Field(default=1)
    max_mastered_words_in_prompt: int = Field(default=300)

    @classmethod
    def from_env(cls, overrides: Optional[dict[str, Any]] = None) -> "Configuration":
        raw_values: dict[str, Any] = {}

        env_aliases = {
            "app_name": os.getenv("APP_NAME"),
            "app_env": os.getenv("APP_ENV"),
            "debug": os.getenv("DEBUG"),

            "host": os.getenv("HOST"),
            "port": os.getenv("PORT"),
            "cors_origins": os.getenv("CORS_ORIGINS"),

            "llm_model_id": os.getenv("LLM_MODEL_ID"),
            "llm_api_key": os.getenv("LLM_API_KEY"),
            "llm_base_url": os.getenv("LLM_BASE_URL"),
            "llm_timeout": os.getenv("LLM_TIMEOUT"),
            "llm_temperature": os.getenv("LLM_TEMPERATURE"),

            "min_chunk_words": os.getenv("MIN_CHUNK_WORDS"),
            "max_chunk_words": os.getenv("MAX_CHUNK_WORDS"),

            "data_dir": os.getenv("DATA_DIR"),
            "vocab_db_path": os.getenv("VOCAB_DB_PATH"),

            "annotator_json_retry": os.getenv("ANNOTATOR_JSON_RETRY"),
            "max_mastered_words_in_prompt": os.getenv("MAX_MASTERED_WORDS_IN_PROMPT"),
        }

        for key, value in env_aliases.items():
            if value is not None:
                raw_values[key] = value

        if overrides:
            for key, value in overrides.items():
                if value is not None:
                    raw_values[key] = value

        return cls(**raw_values)

    def resolved_cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    def ensure_data_dir(self) -> None:
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)

    def resolved_vocab_db_path(self) -> str:
        return str(Path(self.vocab_db_path).expanduser())

    def resolved_model(self) -> str:
        return self.llm_model_id