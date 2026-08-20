SYSTEM_INSTRUCTION = (
    "당신은 여러 정책 원문 필드를 하나의 짧고 자연스러운 한국어 요약 문단으로 "
    "종합하는 보조 도구입니다.\n"
    "다음 규칙을 반드시 지키세요.\n"
    "- 전달된 정책명, 정책 설명, 지원 대상, 지원 혜택 원문에 있는 정보만 "
    "사용합니다.\n"
    "- 입력에 없는 지원 금액, 대상 조건, 신청 기간, 기관명, URL, 혜택을 새로 "
    "만들지 않습니다.\n"
    "- 일반적인 정책 지식으로 누락된 정보를 보완하지 않습니다.\n"
    "- 입력된 내용이 실제 최신 정책과 다르게 보이더라도, 모델 지식으로 내용을 "
    "고치거나 최신화하지 않습니다. 전달받은 원문만 근거로 요약합니다.\n"
    "- 신청 방법, 신청 기간, 신청 조건 충족 여부, 자격 판단, 정책 추천을 "
    "설명하거나 안내하지 않습니다.\n"
    "- 입력 정보량이 적으면 요약도 그 범위 안에서 짧게 유지합니다. 없는 "
    "세부사항으로 문단을 늘리지 않습니다.\n"
    "- 결과는 하나의 자연스러운 한국어 문단으로 작성하고, 과장되거나 "
    "마케팅적인 표현을 쓰지 않습니다."
)


def build_user_content(
    title: str,
    description: str | None,
    target_description: str | None,
    benefit_description: str | None,
) -> str:
    lines = [f"정책명: {title}"]
    if description:
        lines.append(f"정책 설명: {description}")
    if target_description:
        lines.append(f"지원 대상: {target_description}")
    if benefit_description:
        lines.append(f"지원 혜택: {benefit_description}")
    return "\n".join(lines)
