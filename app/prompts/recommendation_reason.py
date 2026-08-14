from app.schemas.recommendation_reason import Condition, EligibilityStatus

SYSTEM_INSTRUCTION = (
    "당신은 정책 추천 서비스의 추천 이유 설명을 작성하는 보조 도구입니다.\n"
    "다음 규칙을 반드시 지키세요.\n"
    "- eligibility 판정 결과를 새로 판단하거나 바꾸지 않습니다. 주어진 값을 참고만 합니다.\n"
    "- condition의 MATCHED/NOT_MATCHED/NEEDS_REVIEW 의미를 바꾸지 않습니다. "
    "NEEDS_REVIEW를 충족했다고 표현하지 않고, NOT_MATCHED를 무시하지 않습니다.\n"
    "- 입력에 없는 정책 혜택, 금액, 기간, 자격, 서류를 새로 만들어내지 않습니다.\n"
    "- 짧고 자연스러운 한국어 한두 문장으로 설명합니다."
)


def build_user_content(
    policy_title: str,
    eligibility_status: EligibilityStatus,
    conditions: list[Condition],
) -> str:
    condition_lines = "\n".join(
        f"- {condition.type.value}: {condition.status.value} ({condition.reason})"
        for condition in conditions
    )
    return (
        f"정책명: {policy_title}\n"
        f"전체 적격 상태: {eligibility_status.value}\n"
        f"조건별 판정:\n{condition_lines}"
    )
