from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MOZIP-AI"
    environment: Literal["local", "development", "production"] = "local"
    ontology_file_path: str = "app/ontology/mozip.owl"


@lru_cache
def get_settings() -> Settings:
    return Settings()
