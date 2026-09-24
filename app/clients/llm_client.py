from functools import lru_cache
from typing import TypeVar

from google import genai
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.exceptions import AppException

T = TypeVar("T", bound=BaseModel)


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
    ) -> T:
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
                timeout=timeout_seconds if timeout_seconds is not None else self._timeout_seconds,
            )
        except Exception as exc:
            raise AppException(
                "LLM 호출에 실패했습니다.", code="INTERNAL_ERROR", status_code=500
            ) from exc

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
    client = genai.Client(api_key=settings.gemini_api_key)
    return LlmClient(client, settings.gemini_model, settings.gemini_timeout_seconds)
