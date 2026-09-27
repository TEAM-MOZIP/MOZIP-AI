from app.schemas.chat_response import (
    ChatBlock,
    ChatBlockPolicy,
    ChatBlockType,
    ChatComparisonRow,
    ChatPolicyNote,
    PolicyFit,
    ChatResponseType,
    ChatStep,
    GroundingConditionResult,
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

    assert result.reply == expected.reply


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

    assert result.reply == _build_response().reply
    assert "조건에 맞는 정책 목록: 없음" in fake_client.last_user_content
    assert "정책 상세 정보: 없음" in fake_client.last_user_content
    assert "확인하지 못한 조건: 없음" in fake_client.last_user_content


def test_generate_chat_response_handles_request_without_history():
    fake_client = _FakeLlmClient(_build_response())
    request = ChatResponseRequest(message="국민취업지원제도가 뭐야?")

    result = generate_chat_response(request, fake_client)

    assert result.reply == _build_response().reply
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


def _grounding(policy_id: int, title: str = "정책") -> GroundingPolicy:
    return GroundingPolicy(policy_id=policy_id, title=title, eligibility_status="ELIGIBLE")


def test_sanitize_drops_unknown_policy_ids_and_duplicates():
    response = ChatResponseResponse(
        reply="요약",
        response_type=ChatResponseType.RECOMMEND,
        blocks=[
            ChatBlock(
                type=ChatBlockType.POLICY_GROUP,
                title="딱 맞는 정책",
                policies=[
                    ChatBlockPolicy(policy_id=1, reason="이유1"),
                    ChatBlockPolicy(policy_id=99, reason="지어낸 정책"),
                ],
            ),
            ChatBlock(
                type=ChatBlockType.POLICY_GROUP,
                title="함께 보면 좋은 정책",
                policies=[ChatBlockPolicy(policy_id=1, reason="중복")],
            ),
        ],
    )
    request = ChatResponseRequest(message="질문", grounding_policies=[_grounding(1)])

    result = generate_chat_response(request, _FakeLlmClient(response))

    assert len(result.blocks) == 1
    assert [policy.policy_id for policy in result.blocks[0].policies] == [1]


def test_sanitize_realigns_comparison_columns_to_known_policies():
    response = ChatResponseResponse(
        reply="비교",
        response_type=ChatResponseType.COMPARE,
        blocks=[
            ChatBlock(
                type=ChatBlockType.COMPARISON,
                policy_ids=[1, 99, 2],
                rows=[
                    ChatComparisonRow(label="지원 방식", values=["현금", "?", "대출"]),
                    ChatComparisonRow(label="칸 수가 틀린 행", values=["a"]),
                ],
            )
        ],
    )
    request = ChatResponseRequest(
        message="비교해줘", grounding_policies=[_grounding(1), _grounding(2)]
    )

    result = generate_chat_response(request, _FakeLlmClient(response))

    block = result.blocks[0]
    assert block.policy_ids == [1, 2]
    assert [row.label for row in block.rows] == ["지원 방식"]
    assert block.rows[0].values == ["현금", "대출"]


def test_sanitize_accepts_policy_detail_id_and_drops_empty_blocks():
    response = ChatResponseResponse(
        reply="신청 방법",
        response_type=ChatResponseType.HOW_TO_APPLY,
        blocks=[
            ChatBlock(type=ChatBlockType.TEXT, text="  "),
            ChatBlock(type=ChatBlockType.STEPS, title="신청 절차", steps=[ChatStep(title="복지로 접속")]),
            ChatBlock(type=ChatBlockType.CHECKLIST, title="준비 서류", items=["", " "]),
            ChatBlock(
                type=ChatBlockType.POLICY_GROUP,
                title="이 정책 자세히 보기",
                policies=[ChatBlockPolicy(policy_id=7, reason="물어본 정책")],
            ),
        ],
    )
    request = ChatResponseRequest(
        message="신청 방법",
        policy_detail=PolicyDetailGrounding(
            title="정책",
            summary="요약",
            eligibility="대상",
            application_period="상시",
            organization="기관",
            policy_id=7,
        ),
    )

    result = generate_chat_response(request, _FakeLlmClient(response))

    assert [block.type for block in result.blocks] == [
        ChatBlockType.STEPS,
        ChatBlockType.POLICY_GROUP,
    ]


def test_sanitize_limits_follow_ups_and_falls_back_to_reply_text():
    response = ChatResponseResponse(
        reply="안녕하세요!",
        follow_ups=["a", "a", "b", " ", "c", "d"],
    )
    request = ChatResponseRequest(message="안녕")

    result = generate_chat_response(request, _FakeLlmClient(response))

    assert result.follow_ups == ["a", "b", "c"]
    assert result.blocks == [ChatBlock(type=ChatBlockType.TEXT, text="안녕하세요!")]


def test_user_content_includes_target_benefit_and_condition_results():
    fake_client = _FakeLlmClient(_build_response())
    request = ChatResponseRequest(
        message="나 받을 수 있어?",
        grounding_policies=[
            GroundingPolicy(
                policy_id=1,
                title="월세 지원",
                eligibility_status="ELIGIBLE",
                target="무주택 청년",
                benefit="월 20만 원",
            )
        ],
        policy_detail=PolicyDetailGrounding(
            title="월세 지원",
            summary="요약",
            eligibility="대상",
            application_period="상시",
            organization="기관",
            policy_id=1,
            eligibility_status="NEEDS_REVIEW",
            condition_results=[
                GroundingConditionResult(type="INCOME", status="NEEDS_REVIEW", reason="소득 정보 없음")
            ],
        ),
    )

    generate_chat_response(request, fake_client)

    content = fake_client.last_user_content
    assert "target=무주택 청년" in content
    assert "benefit=월 20만 원" in content
    assert "policyId=1" in content
    assert "conditionResult: type=INCOME, status=NEEDS_REVIEW, reason=소득 정보 없음" in content


def test_sanitize_builds_cards_from_policy_ids_when_policies_empty():
    response = ChatResponseResponse(
        reply="요약",
        response_type=ChatResponseType.RECOMMEND,
        blocks=[ChatBlock(type=ChatBlockType.POLICY_GROUP, title="딱 맞는 정책", policy_ids=[2, 1])],
    )
    request = ChatResponseRequest(message="질문", grounding_policies=[_grounding(1), _grounding(2)])

    result = generate_chat_response(request, _FakeLlmClient(response))

    assert [policy.policy_id for policy in result.blocks[0].policies] == [2, 1]


def test_sanitize_appends_grounding_cards_when_model_ids_are_all_unknown():
    response = ChatResponseResponse(
        reply="요약",
        response_type=ChatResponseType.RECOMMEND,
        blocks=[
            ChatBlock(type=ChatBlockType.TEXT, text="골라봤어요."),
            ChatBlock(
                type=ChatBlockType.POLICY_GROUP,
                title="딱 맞는 정책",
                policies=[ChatBlockPolicy(policy_id=99, reason="지어낸 정책")],
            ),
        ],
    )
    request = ChatResponseRequest(
        message="질문", grounding_policies=[_grounding(10775), _grounding(11516)]
    )

    result = generate_chat_response(request, _FakeLlmClient(response))

    assert [block.type for block in result.blocks] == [ChatBlockType.TEXT, ChatBlockType.POLICY_GROUP]
    assert [policy.policy_id for policy in result.blocks[1].policies] == [10775, 11516]


def test_sanitize_maps_list_number_and_title_to_real_policy_ids():
    response = ChatResponseResponse(
        reply="요약",
        response_type=ChatResponseType.RECOMMEND,
        blocks=[
            ChatBlock(
                type=ChatBlockType.POLICY_GROUP,
                title="딱 맞는 정책",
                policies=[
                    # 순번(2번째 정책)을 id로 쓴 경우
                    ChatBlockPolicy(policy_id=2, reason="순번"),
                    # id는 틀렸지만 제목이 맞는 경우
                    ChatBlockPolicy(policy_id=12345, title="월세 지원", reason="제목"),
                ],
            ),
        ],
    )
    request = ChatResponseRequest(
        message="질문",
        grounding_policies=[_grounding(10775, "월세 지원"), _grounding(11516, "전세 대출")],
    )

    result = generate_chat_response(request, _FakeLlmClient(response))

    policies = result.blocks[0].policies
    assert [policy.policy_id for policy in policies] == [11516, 10775]
    assert [policy.reason for policy in policies] == ["순번", "제목"]


def test_policy_notes_build_best_and_related_groups_and_drop_excluded():
    response = ChatResponseResponse(
        reply="요약",
        response_type=ChatResponseType.RECOMMEND,
        blocks=[
            ChatBlock(type=ChatBlockType.TEXT, text="주거 정책을 골랐어요."),
            ChatBlock(type=ChatBlockType.QUICK_REPLIES, items=["소득 알려주기"]),
        ],
        policy_notes=[
            ChatPolicyNote(policy_id=1, title="아이돌봄", fit=PolicyFit.RELATED, reason="자녀 가구"),
            ChatPolicyNote(policy_id=2, title="폭력피해자 주거지원", fit=PolicyFit.EXCLUDE),
            ChatPolicyNote(policy_id=3, title="주거상향", fit=PolicyFit.BEST, reason="무주택", highlight="월 20만 원"),
        ],
    )
    request = ChatResponseRequest(
        message="주거 정책",
        grounding_policies=[_grounding(10), _grounding(20), _grounding(30)],
    )

    result = generate_chat_response(request, _FakeLlmClient(response))

    # 순번 1·2·3 → 실제 id 10·20·30, EXCLUDE(20)는 빠지고 카드는 빠른 선택 칩 앞에 들어간다.
    assert [block.type for block in result.blocks] == [
        ChatBlockType.TEXT,
        ChatBlockType.POLICY_GROUP,
        ChatBlockType.POLICY_GROUP,
        ChatBlockType.QUICK_REPLIES,
    ]
    best, related = result.blocks[1], result.blocks[2]
    assert best.title == "딱 맞는 정책"
    assert [(p.policy_id, p.reason, p.highlight) for p in best.policies] == [(30, "무주택", "월 20만 원")]
    assert related.title == "함께 보면 좋은 정책"
    assert [p.policy_id for p in related.policies] == [10]
    assert result.policy_notes == []


def test_policy_notes_take_priority_over_model_policy_group_blocks():
    response = ChatResponseResponse(
        reply="요약",
        response_type=ChatResponseType.RECOMMEND,
        blocks=[
            ChatBlock(type=ChatBlockType.TEXT, text="골랐어요."),
            ChatBlock(
                type=ChatBlockType.POLICY_GROUP,
                title="모델이 만든 그룹",
                policies=[ChatBlockPolicy(policy_id=10, reason="블록")],
            ),
        ],
        policy_notes=[ChatPolicyNote(policy_id=10, title="정책", fit=PolicyFit.BEST, reason="노트")],
    )
    request = ChatResponseRequest(message="질문", grounding_policies=[_grounding(10)])

    result = generate_chat_response(request, _FakeLlmClient(response))

    groups = [block for block in result.blocks if block.type == ChatBlockType.POLICY_GROUP]
    assert len(groups) == 1
    assert groups[0].title == "딱 맞는 정책"
    assert groups[0].policies[0].reason == "노트"


def test_user_content_marks_attached_application_guide():
    fake_client = _FakeLlmClient(_build_response())
    request = ChatResponseRequest(
        message="신청 방법 알려줘",
        policy_detail=PolicyDetailGrounding(
            title="월세 지원",
            summary="요약",
            eligibility="대상",
            application_period="상시",
            organization="기관",
            policy_id=1,
            application_guide_attached=True,
        ),
    )

    generate_chat_response(request, fake_client)

    assert "applicationGuideAttached=true" in fake_client.last_user_content
