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
    # 챗봇 답변(/chat/respond)은 여러 문단의 긴 답변 + 대화 이력을 다뤄 2.5초 안에 끝나지
    # 않는 경우가 잦다(되묻기 턴에서 INTERNAL_ERROR). 챗봇 호출에만 넉넉한 timeout을 쓴다.
    gemini_chat_timeout_seconds: float = 15.0
    # 신청 가이드(/guides/generate)는 여러 단계와 준비 서류를 구조화해 생성하느라 2.5초를 자주 넘긴다.
    # 넘기면 SERVER가 원문을 그대로 한 단계로 보여주므로 가이드에도 넉넉한 timeout을 쓴다.
    gemini_guide_timeout_seconds: float = 12.0
    # 정책 요약·추천 이유·용어 설명도 응답이 느려질 때 2.5초를 넘겨 500이 나던 문제가 있어 각각 넉넉히 둔다.
    # 요약은 SERVER가 정책별로 저장하므로 처음 한 번만 느리다.
    # SERVER 대기(14초)와 운영 nginx(15초) 안에 끝나도록 요약·가이드는 12초를 넘기지 않는다.
    gemini_summary_timeout_seconds: float = 12.0
    gemini_reason_timeout_seconds: float = 8.0
    gemini_term_timeout_seconds: float = 8.0
    # 정책 요약·신청 가이드·추천 이유·용어 설명 호출의 thinking 수준(minimal/low/medium/high).
    # 기본은 미지정(모델 기본값). "minimal" 지정 시 모든 호출이 응답 없이 timeout 나는 문제가 있어 끔.
    # 챗봇 답변·조건 추출에는 적용하지 않는다.
    gemini_fast_thinking_level: str | None = None
    # Gemini SDK 요청 시도 횟수(첫 요청 포함). 1이면 재시도하지 않고 429/503 같은 실제 오류를 바로 드러낸다.
    gemini_max_attempts: int = 1


@lru_cache
def get_settings() -> Settings:
    return Settings()
