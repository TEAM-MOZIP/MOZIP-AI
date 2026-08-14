from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MOZIP-AI"
    environment: Literal["local", "development", "production"] = "local"
    ontology_file_path: str = "app/ontology/mozip.owl"
    gemini_api_key: str | None = None
    # alias(gemini-flash-lite-latest)가 아니라 확인된 구체 stable 모델 ID를 고정한다 —
    # alias는 Google이 가리키는 대상을 예고 없이 바꿀 수 있어 latency/품질 특성이
    # 실측(1.3초대, thought_tokens=0)과 달라질 수 있다.
    gemini_model: str = "gemini-3.5-flash-lite"
    # 실측 5건 latency(최대 1991ms)가 2.0초 예산과 여유가 사실상 없어 2.5초로 조정함.
    # SERVER→AI timeout(현재 3초, Semantic Match 값)은 이 값을 그대로 복사한 게 아니라
    # B-1 SERVER 연동 Issue에서 이번 실측 데이터를 근거로 별도로 재설계한다.
    gemini_timeout_seconds: float = 2.5


@lru_cache
def get_settings() -> Settings:
    return Settings()
