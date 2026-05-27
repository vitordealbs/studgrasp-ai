from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    java_api_url: str = "http://localhost:8080"
    db_url: str = "postgresql://studgrasp:studgrasp@localhost:5432/studgrasp"
    redis_url: str = "redis://localhost:6379"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
