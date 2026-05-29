from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # LLM — qualquer provedor compatível com OpenAI (DeepSeek, Groq, OpenAI, Ollama...)
    llm_api_key: str
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"

    java_api_url: str = "http://localhost:8080"
    scraper_api_key: str = ""
    db_url: str = "postgresql://studgrasp:studgrasp@localhost:5432/studgrasp"
    redis_url: str = "redis://localhost:6379"


@lru_cache()
def get_settings() -> Settings:
    return Settings()