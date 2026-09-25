from app.schemas.term_explanation import TermExplainRequest, TermExplainResponse
from app.core.config import get_settings
from app.services.term_explanation_service import generate_term_explanation


class _FakeLlmClient:
    def __init__(self, response: TermExplainResponse) -> None:
        self._response = response
        self.last_system_instruction: str | None = None
        self.last_user_content: str | None = None
        self.last_response_schema: type | None = None
        self.last_timeout_seconds: float | None = None

    def generate_structured(
        self,
        system_instruction,
        user_content,
        response_schema,
        timeout_seconds=None,
        thinking_level=None,
    ):
        self.last_timeout_seconds = timeout_seconds
        self.last_thinking_level = thinking_level
        self.last_system_instruction = system_instruction
        self.last_user_content = user_content
        self.last_response_schema = response_schema
        return self._response


def _build_request() -> TermExplainRequest:
    return TermExplainRequest(
        term="기준 중위소득 120%",
        context="본 사업은 기준 중위소득 120% 이하의 청년을 대상으로 합니다.",
    )


def test_generate_term_explanation_returns_llm_result():
    expected = TermExplainResponse(explanation="설명 문장")
    fake_client = _FakeLlmClient(expected)
    request = _build_request()

    result = generate_term_explanation(request, fake_client)

    assert result == expected


def test_generate_term_explanation_uses_term_explain_response_schema():
    fake_client = _FakeLlmClient(TermExplainResponse(explanation="설명 문장"))
    request = _build_request()

    generate_term_explanation(request, fake_client)

    assert fake_client.last_response_schema is TermExplainResponse


def test_generate_term_explanation_passes_term_and_context():
    fake_client = _FakeLlmClient(TermExplainResponse(explanation="설명 문장"))
    request = _build_request()

    generate_term_explanation(request, fake_client)

    assert "기준 중위소득 120%" in fake_client.last_user_content
    assert "청년을 대상으로 합니다" in fake_client.last_user_content


def test_generate_term_explanation_uses_term_timeout():
    fake_client = _FakeLlmClient(TermExplainResponse(explanation="설명 문장"))

    generate_term_explanation(_build_request(), fake_client)

    assert fake_client.last_timeout_seconds == get_settings().gemini_term_timeout_seconds
    assert fake_client.last_thinking_level == get_settings().gemini_fast_thinking_level
