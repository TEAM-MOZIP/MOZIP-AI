from app.schemas.chat_response import (
    ChatResponseRequest,
    ChatResponseResponse,
    GroundingPolicy,
    GroundingUnresolvedCondition,
    PolicyDetailGrounding,
)
from app.services.chat_response_service import generate_chat_response


class _FakeLlmClient:
    def __init__(self, response: ChatResponseResponse) -> None:
        self._response = response
        self.last_system_instruction: str | None = None
        self.last_user_content: str | None = None
        self.last_response_schema: type | None = None

    def generate_structured(self, system_instruction, user_content, response_schema):
        self.last_system_instruction = system_instruction
        self.last_user_content = user_content
        self.last_response_schema = response_schema
        return self._response


def _build_response() -> ChatResponseResponse:
    return ChatResponseResponse(reply="답변입니다.")


def test_generate_chat_response_returns_llm_result():
    expected = _build_response()
    fake_client = _FakeLlmClient(expected)
    request = ChatResponseRequest(message="서울 사는 취준생이 받을 정책 있어?")

    result = generate_chat_response(request, fake_client)

    assert result == expected


def test_generate_chat_response_uses_chat_response_response_schema():
    fake_client = _FakeLlmClient(_build_response())
    request = ChatResponseRequest(message="질문입니다.")

    generate_chat_response(request, fake_client)

    assert fake_client.last_response_schema is ChatResponseResponse


def test_generate_chat_response_includes_grounding_policies_in_user_content():
    fake_client = _FakeLlmClient(_build_response())
    request = ChatResponseRequest(
        message="서울 사는 취준생이 받을 정책 있어?",
        grounding_policies=[
            GroundingPolicy(
                policy_id=1,
                title="국민취업지원제도",
                eligibility_status="ELIGIBLE",
                application_end_date=None,
            )
        ],
    )

    generate_chat_response(request, fake_client)

    assert "국민취업지원제도" in fake_client.last_user_content
    assert "ELIGIBLE" in fake_client.last_user_content


def test_generate_chat_response_includes_policy_detail_in_user_content():
    fake_client = _FakeLlmClient(_build_response())
    request = ChatResponseRequest(
        message="국민취업지원제도가 뭐야?",
        policy_detail=PolicyDetailGrounding(
            title="국민취업지원제도",
            summary="요약",
            eligibility="자격 요건",
            application_period="상시",
            organization="고용노동부",
        ),
    )

    generate_chat_response(request, fake_client)

    assert "국민취업지원제도" in fake_client.last_user_content
    assert "고용노동부" in fake_client.last_user_content


def test_generate_chat_response_includes_unresolved_conditions_in_user_content():
    fake_client = _FakeLlmClient(_build_response())
    request = ChatResponseRequest(
        message="프리랜서인데 받을 정책 있어?",
        unresolved_conditions=[
            GroundingUnresolvedCondition(axis="employment_status", raw_text="프리랜서")
        ],
    )

    generate_chat_response(request, fake_client)

    assert "employment_status" in fake_client.last_user_content
    assert "프리랜서" in fake_client.last_user_content


def test_generate_chat_response_handles_request_without_grounding():
    fake_client = _FakeLlmClient(_build_response())
    request = ChatResponseRequest(message="기준중위소득이 뭐야?")

    result = generate_chat_response(request, fake_client)

    assert result == _build_response()
    assert "조건에 맞는 정책 목록: 없음" in fake_client.last_user_content
    assert "정책 상세 정보: 없음" in fake_client.last_user_content
    assert "확인하지 못한 조건: 없음" in fake_client.last_user_content
