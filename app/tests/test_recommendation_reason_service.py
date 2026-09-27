from app.schemas.recommendation_reason import (
    Condition,
    ConditionStatus,
    ConditionType,
    EligibilityStatus,
    RecommendationExplainRequest,
    RecommendationExplainResponse,
)
from app.core.config import get_settings
from app.services.recommendation_reason_service import generate_recommendation_explanation


class _FakeLlmClient:
    def __init__(self, response: RecommendationExplainResponse) -> None:
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


def _build_request() -> RecommendationExplainRequest:
    return RecommendationExplainRequest(
        policy_title="청년내일채움공제",
        eligibility_status=EligibilityStatus.ELIGIBLE,
        conditions=[
            Condition(
                type=ConditionType.AGE,
                status=ConditionStatus.MATCHED,
                reason="만 25세는 19~34세 조건을 충족합니다",
            ),
            Condition(
                type=ConditionType.INCOME,
                status=ConditionStatus.NEEDS_REVIEW,
                reason="소득 정보가 등록되지 않았습니다",
            ),
        ],
    )


def test_generate_recommendation_explanation_returns_llm_result():
    expected = RecommendationExplainResponse(reason="설명 문장")
    fake_client = _FakeLlmClient(expected)
    request = _build_request()

    result = generate_recommendation_explanation(request, fake_client)

    assert result == expected


def test_generate_recommendation_explanation_uses_recommendation_explain_response_schema():
    fake_client = _FakeLlmClient(RecommendationExplainResponse(reason="설명 문장"))
    request = _build_request()

    generate_recommendation_explanation(request, fake_client)

    assert fake_client.last_response_schema is RecommendationExplainResponse


def test_generate_recommendation_explanation_passes_request_fields_without_recomputing():
    fake_client = _FakeLlmClient(RecommendationExplainResponse(reason="설명 문장"))
    request = _build_request()

    generate_recommendation_explanation(request, fake_client)

    assert "청년내일채움공제" in fake_client.last_user_content
    assert "ELIGIBLE" in fake_client.last_user_content
    assert "NEEDS_REVIEW" in fake_client.last_user_content
    # request 자체는 변경되지 않는다 (재판정/재계산 없음)
    assert request.eligibility_status == EligibilityStatus.ELIGIBLE
    assert request.conditions[1].status == ConditionStatus.NEEDS_REVIEW


def test_generate_recommendation_explanation_uses_reason_timeout():
    fake_client = _FakeLlmClient(RecommendationExplainResponse(reason="설명 문장"))

    generate_recommendation_explanation(_build_request(), fake_client)

    assert fake_client.last_timeout_seconds == get_settings().gemini_reason_timeout_seconds
    assert fake_client.last_thinking_level == get_settings().gemini_fast_thinking_level
