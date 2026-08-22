from app.schemas.chat_response import ChatResponseRequest

SYSTEM_INSTRUCTION = (
    "당신은 MOZIP 정책 챗봇의 답변 생성 도구입니다.\n"
    "다음 규칙을 반드시 지키세요.\n"
    "- groundingPolicies와 policyDetail로 주어진 정보만 사실로 사용합니다. 이 "
    "정보에 없는 금액, 기간, 기관, 자격 조건, 정책을 새로 만들어내지 않습니다.\n"
    "- groundingPolicies와 policyDetail이 모두 비어 있는데 특정 정책에 대한 "
    "질문이면, 정책 내용을 추측하지 않고 확인할 수 없다고 안내합니다.\n"
    "- groundingPolicies와 policyDetail이 모두 비어 있고 정책 문맥도 없는 "
    "일반적인 질문이면, 일반 지식으로 답하지 않고 정책을 특정해달라는 안내로 "
    "응답합니다.\n"
    "- groundingPolicies에 여러 정책이 있어도 사용자 질문과 관련 없는 정책을 "
    "임의로 골라 설명하지 않습니다.\n"
    "- eligibilityStatus는 이미 판정이 끝난 결과입니다. 자격 여부를 다시 "
    "판단하거나 새로운 기준으로 재해석하지 않습니다.\n"
    '- "이 정책이 왜 나한테 맞는지" 같은 질문에도 개인화된 추천 사유를 만들지 '
    "않고, 정책 자체의 자격 조건을 설명하는 것으로 대신합니다.\n"
    "- 여러 정책을 비교해달라는 요청에는 비교 결과를 만들지 않고, 정책 비교는 "
    "현재 지원하지 않는다고 안내합니다.\n"
    "- unresolvedConditions가 있으면, 확인하지 못한 조건이 있다는 사실을 "
    "자연스럽게 안내합니다.\n"
    "- history가 있으면 이전 사용자 질문과 AI 답변을 참고해 현재 질문의 문맥"
    "(지시대명사, 생략된 주어, 이전에 언급된 대상 등)을 해석합니다. history는 "
    "문맥을 이해하는 용도로만 사용하고, groundingPolicies와 policyDetail에 "
    "없는 새로운 정책 사실을 history만으로 만들어내지 않습니다. 이전 답변에 "
    "포함되지 않았던 정보를 물어보면, 확인할 수 없다고 안내합니다.\n"
    "- 쉬운 한국어로 명확하게 답합니다."
)


def build_user_content(request: ChatResponseRequest) -> str:
    lines = [f"사용자 질문: {request.message}"]

    if request.history:
        lines.append("대화 기록:")
        for turn in request.history:
            lines.append(f"- 이전 사용자 메시지: {turn.message}")
            lines.append(f"  이전 AI 답변: {turn.reply}")
    else:
        lines.append("대화 기록: 없음")

    if request.grounding_policies:
        lines.append("조건에 맞는 정책 목록:")
        for policy in request.grounding_policies:
            end_date = (
                policy.application_end_date.isoformat()
                if policy.application_end_date
                else "명시 없음"
            )
            lines.append(
                f"- policyId={policy.policy_id}, title={policy.title}, "
                f"eligibilityStatus={policy.eligibility_status}, "
                f"applicationEndDate={end_date}"
            )
    else:
        lines.append("조건에 맞는 정책 목록: 없음")

    if request.policy_detail:
        detail = request.policy_detail
        lines.append(
            "정책 상세 정보: "
            f"title={detail.title}, summary={detail.summary}, "
            f"eligibility={detail.eligibility}, "
            f"applicationPeriod={detail.application_period}, "
            f"organization={detail.organization}"
        )
    else:
        lines.append("정책 상세 정보: 없음")

    if request.unresolved_conditions:
        lines.append("확인하지 못한 조건:")
        for condition in request.unresolved_conditions:
            lines.append(f"- axis={condition.axis}, rawText={condition.raw_text}")
    else:
        lines.append("확인하지 못한 조건: 없음")

    return "\n".join(lines)
