import logging
import time
from functools import lru_cache
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.exceptions import AppException

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger("mozip_ai.llm")


class LlmClient:
    def __init__(self, client: genai.Client, model: str, timeout_seconds: float) -> None:
        self._client = client
        self._model = model
        self._timeout_seconds = timeout_seconds

    def generate_structured(
        self,
        system_instruction: str,
        user_content: str,
        response_schema: type[T],
        timeout_seconds: float | None = None,
        thinking_level: str | None = None,
    ) -> T:
        timeout = timeout_seconds if timeout_seconds is not None else self._timeout_seconds
        # thinking_level을 주면 그 호출만 모델의 추론(thinking) 수준을 바꾼다. 비우면 모델 기본값을 쓴다.
        # 요약·정리처럼 추론이 필요 없는 호출만 낮추고, 챗봇 답변처럼 품질이 중요한 호출은 기본값을 유지한다.
        extra_kwargs = (
            {"generation_config": {"thinking_level": thinking_level}} if thinking_level else {}
        )
        started_at = time.perf_counter()
        try:
            interaction = self._client.interactions.create(
                model=self._model,
                input=user_content,
                system_instruction=system_instruction,
                store=False,
                # top-level response_mime_type을 response_format과 함께 보내면 실제 API가
                # "responseFormat must be set" 400을 반환한다(실측 확인, SDK docstring과
                # 반대). mime_type은 response_format 안에만 넣는다.
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": response_schema.model_json_schema(),
                },
                timeout=timeout,
                **extra_kwargs,
            )
        except Exception as exc:
            # 500 원인이 timeout인지, 429(호출 한도)·503(과부하)·인증 오류인지 구분할 수 있게 원인을 남긴다.
            logger.warning(
                "llm call failed schema=%s model=%s timeout_seconds=%s elapsed_ms=%.0f "
                "error_type=%s error=%s",
                response_schema.__name__,
                self._model,
                timeout,
                (time.perf_counter() - started_at) * 1000,
                type(exc).__name__,
                str(exc)[:300],
            )
            raise AppException(
                "LLM 호출에 실패했습니다.", code="INTERNAL_ERROR", status_code=500
            ) from exc

        usage = getattr(interaction, "usage", None)
        logger.info(
            "llm call completed schema=%s elapsed_ms=%.0f thought_tokens=%s output_tokens=%s",
            response_schema.__name__,
            (time.perf_counter() - started_at) * 1000,
            getattr(usage, "total_thought_tokens", None),
            getattr(usage, "total_output_tokens", None),
        )

        if interaction.output_text is None:
            raise AppException(
                "LLM 응답에 결과 텍스트가 없습니다.", code="INTERNAL_ERROR", status_code=500
            )

        try:
            return response_schema.model_validate_json(interaction.output_text)
        except ValidationError as exc:
            raise AppException(
                "LLM 응답이 예상한 형식과 다릅니다.", code="INTERNAL_ERROR", status_code=500
            ) from exc

    def close(self) -> None:
        self._client.close()


@lru_cache
def get_llm_client() -> LlmClient:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise AppException(
            "GEMINI_API_KEY가 설정되지 않았습니다.", code="LLM_NOT_CONFIGURED", status_code=500
        )
    # SDK는 기본으로 429·5xx·timeout을 최대 3회까지 조용히 재시도한다. 우리 timeout(8~15초) 안에서 재시도가
    # 일어나면 실제 원인(429 호출 한도, 503 과부하)이 가려지고 전부 APITimeoutError로만 보인다.
    # 재시도 횟수를 설정으로 두고 기본은 재시도 없이(1회) 실제 오류를 그대로 드러낸다.
    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(attempts=settings.gemini_max_attempts)
        ),
    )
    return LlmClient(client, settings.gemini_model, settings.gemini_timeout_seconds)
