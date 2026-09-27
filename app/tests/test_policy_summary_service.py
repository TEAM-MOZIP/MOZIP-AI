import pytest
from pydantic import ValidationError

from app.schemas.policy_summary import PolicySummaryRequest, PolicySummaryResponse
from app.core.config import get_settings
from app.services.policy_summary_service import generate_policy_summary


class _FakeLlmClient:
    def __init__(self, response: PolicySummaryResponse) -> None:
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


def _build_response() -> PolicySummaryResponse:
    return PolicySummaryResponse(summary="요약 문단")


def test_generate_policy_summary_returns_llm_result():
    expected = _build_response()
    fake_client = _FakeLlmClient(expected)
    request = PolicySummaryRequest(
        title="국민취업지원제도",
        description="취업지원서비스와 소득지원을 결합한 한국형 실업부조 제도입니다.",
        target_description="만 15세 이상 69세 이하 구직자 중 소득·재산 요건을 충족하는 자",
        benefit_description="구직촉진수당 월 50만원씩 최대 6개월 지급",
    )

    result = generate_policy_summary(request, fake_client)

    assert result == expected


def test_generate_policy_summary_uses_policy_summary_response_schema():
    fake_client = _FakeLlmClient(_build_response())
    request = PolicySummaryRequest(
        title="국민취업지원제도",
        target_description="만 15세 이상 69세 이하 구직자",
    )

    generate_policy_summary(request, fake_client)

    assert fake_client.last_response_schema is PolicySummaryResponse


def test_generate_policy_summary_includes_all_sources_when_present():
    fake_client = _FakeLlmClient(_build_response())
    request = PolicySummaryRequest(
        title="국민취업지원제도",
        description="한국형 실업부조 제도입니다.",
        target_description="만 15세 이상 69세 이하 구직자",
        benefit_description="구직촉진수당 월 50만원 지급",
    )

    generate_policy_summary(request, fake_client)

    assert "국민취업지원제도" in fake_client.last_user_content
    assert "한국형 실업부조 제도입니다." in fake_client.last_user_content
    assert "만 15세 이상 69세 이하 구직자" in fake_client.last_user_content
    assert "구직촉진수당 월 50만원 지급" in fake_client.last_user_content


def test_generate_policy_summary_only_target_description_present():
    fake_client = _FakeLlmClient(_build_response())
    request = PolicySummaryRequest(
        title="국민취업지원제도",
        target_description="만 15세 이상 69세 이하 구직자",
    )

    generate_policy_summary(request, fake_client)

    assert "만 15세 이상 69세 이하 구직자" in fake_client.last_user_content
    assert "정책 설명" not in fake_client.last_user_content
    assert "지원 혜택" not in fake_client.last_user_content


def test_generate_policy_summary_only_benefit_description_present():
    fake_client = _FakeLlmClient(_build_response())
    request = PolicySummaryRequest(
        title="국민취업지원제도",
        benefit_description="구직촉진수당 월 50만원 지급",
    )

    generate_policy_summary(request, fake_client)

    assert "구직촉진수당 월 50만원 지급" in fake_client.last_user_content
    assert "정책 설명" not in fake_client.last_user_content
    assert "지원 대상" not in fake_client.last_user_content


def test_generate_policy_summary_omits_missing_optional_sources():
    fake_client = _FakeLlmClient(_build_response())
    request = PolicySummaryRequest(
        title="국민취업지원제도",
        description="한국형 실업부조 제도입니다.",
    )

    generate_policy_summary(request, fake_client)

    assert "지원 대상" not in fake_client.last_user_content
    assert "지원 혜택" not in fake_client.last_user_content


@pytest.mark.parametrize("value", ["", "   "])
def test_policy_summary_response_rejects_blank_summary(value):
    with pytest.raises(ValidationError):
        PolicySummaryResponse(summary=value)


def test_policy_summary_response_accepts_non_blank_summary():
    response = PolicySummaryResponse(
        summary="청년 구직자를 대상으로 취업 지원 서비스를 제공하는 정책입니다."
    )

    assert response.summary == "청년 구직자를 대상으로 취업 지원 서비스를 제공하는 정책입니다."


def test_generate_policy_summary_uses_summary_timeout():
    fake_client = _FakeLlmClient(_build_response())
    request = PolicySummaryRequest(title="국민취업지원제도", description="실업부조 제도입니다.")

    generate_policy_summary(request, fake_client)

    assert fake_client.last_timeout_seconds == get_settings().gemini_summary_timeout_seconds
    assert fake_client.last_thinking_level == get_settings().gemini_fast_thinking_level
