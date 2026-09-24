from app.schemas.chat_response import (
    ChatResponseRequest,
    ChatResponseResponse,
    ChatTurn,
    GroundingPolicy,
    GroundingUnresolvedCondition,
    PolicyDetailGrounding,
)
from app.core.config import get_settings
from app.services.chat_response_service import generate_chat_response


class _FakeLlmClient:
    def __init__(self, response: ChatResponseResponse) -> None:
        self._response = response
        self.last_system_instruction: str | None = None
        self.last_user_content: str | None = None
        self.last_response_schema: type | None = None
        self.last_timeout_seconds: float | None = None

    def generate_structured(
        self, system_instruction, user_content, response_schema, timeout_seconds=None
    ):
        self.last_timeout_seconds = timeout_seconds
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


def test_generate_chat_response_uses_chat_timeout():
    fake_client = _FakeLlmClient(_build_response())
    request = ChatResponseRequest(message="질문입니다.")

    generate_chat_response(request, fake_client)

    assert fake_client.last_timeout_seconds == get_settings().gemini_chat_timeout_seconds


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


def test_generate_chat_response_handles_request_without_history():
    fake_client = _FakeLlmClient(_build_response())
    request = ChatResponseRequest(message="국민취업지원제도가 뭐야?")

    result = generate_chat_response(request, fake_client)

    assert result == _build_response()
    assert "대화 기록: 없음" in fake_client.last_user_content


def test_generate_chat_response_includes_history_in_user_content():
    fake_client = _FakeLlmClient(_build_response())
    request = ChatResponseRequest(
        message="그거 신청 기간은?",
        history=[
            ChatTurn(
                message="국민취업지원제도 알려줘",
                reply="국민취업지원제도는 구직자를 지원하는 제도입니다.",
            )
        ],
    )

    generate_chat_response(request, fake_client)

    assert "국민취업지원제도 알려줘" in fake_client.last_user_content
    assert "국민취업지원제도는 구직자를 지원하는 제도입니다." in fake_client.last_user_content


def test_generate_chat_response_includes_history_and_grounding_together():
    fake_client = _FakeLlmClient(_build_response())
    request = ChatResponseRequest(
        message="그중 첫 번째는 신청 기간이 언제야?",
        history=[
            ChatTurn(message="서울 사는 취준생이 받을 정책 있어?", reply="이런 정책들이 있어요.")
        ],
        grounding_policies=[
            GroundingPolicy(
                policy_id=1,
                title="국민취업지원제도",
                eligibility_status="ELIGIBLE",
                application_end_date=None,
            )
        ],
        unresolved_conditions=[
            GroundingUnresolvedCondition(axis="employment_status", raw_text="프리랜서")
        ],
    )

    generate_chat_response(request, fake_client)

    assert "서울 사는 취준생이 받을 정책 있어?" in fake_client.last_user_content
    assert "국민취업지원제도" in fake_client.last_user_content
    assert "ELIGIBLE" in fake_client.last_user_content
    assert "employment_status" in fake_client.last_user_content
    assert "프리랜서" in fake_client.last_user_content


def test_generate_chat_response_includes_policy_summary_when_present():
    fake_client = _FakeLlmClient(_build_response())
    request = ChatResponseRequest(
        message="청년 월세 알려줘",
        grounding_policies=[
            GroundingPolicy(
                policy_id=1,
                title="서울시 청년월세지원",
                eligibility_status="NEEDS_REVIEW",
                summary="서울 거주 무주택 청년의 월세 부담 완화",
            ),
            GroundingPolicy(
                policy_id=2,
                title="청년월세 특별지원",
                eligibility_status="ELIGIBLE",
            ),
        ],
    )

    generate_chat_response(request, fake_client)

    assert "summary=서울 거주 무주택 청년의 월세 부담 완화" in fake_client.last_user_content
    policy2_line = next(
        line for line in fake_client.last_user_content.splitlines() if "policyId=2" in line
    )
    assert "summary=" not in policy2_line


def test_grounding_policy_accepts_summary_alias_and_defaults_to_none():
    with_summary = GroundingPolicy.model_validate(
        {"policyId": 1, "title": "정책", "eligibilityStatus": "ELIGIBLE", "summary": "요약"}
    )
    without_summary = GroundingPolicy.model_validate(
        {"policyId": 2, "title": "정책", "eligibilityStatus": "ELIGIBLE"}
    )

    assert with_summary.summary == "요약"
    assert without_summary.summary is None



def test_generate_chat_response_includes_optional_policy_detail_fields_when_present():
    fake_client = _FakeLlmClient(_build_response())
    request = ChatResponseRequest(
        message="국민취업지원제도가 뭐야?",
        policy_detail=PolicyDetailGrounding(
            title="국민취업지원제도",
            summary="요약",
            eligibility="만 15~69세 구직자",
            application_period="상시",
            organization="고용노동부",
            benefit="구직촉진수당 월 50만원, 최대 6개월",
            application_method="고용24 온라인 신청",
            required_documents="신분증",
            contact="1350",
            application_url="https://www.work24.go.kr",
        ),
    )

    generate_chat_response(request, fake_client)

    content = fake_client.last_user_content
    assert "benefit=구직촉진수당 월 50만원, 최대 6개월" in content
    assert "applicationMethod=고용24 온라인 신청" in content
    assert "requiredDocuments=신분증" in content
    assert "contact=1350" in content
    assert "applicationUrl=https://www.work24.go.kr" in content


def test_policy_detail_optional_fields_default_to_none_and_are_omitted():
    detail = PolicyDetailGrounding.model_validate(
        {
            "title": "정책",
            "summary": "요약",
            "eligibility": "대상",
            "applicationPeriod": "상시",
            "organization": "기관",
        }
    )
    fake_client = _FakeLlmClient(_build_response())

    generate_chat_response(
        ChatResponseRequest(message="정책이 뭐야?", policy_detail=detail), fake_client
    )

    assert detail.benefit is None
    assert detail.application_url is None
    assert "benefit=" not in fake_client.last_user_content
    assert "requiredDocuments=" not in fake_client.last_user_content
