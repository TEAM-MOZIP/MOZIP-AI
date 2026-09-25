from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from app.schemas.condition_extraction import ConditionAxis


class EligibilityStatus(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class GroundingPolicy(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    policy_id: int
    title: str
    eligibility_status: EligibilityStatus
    application_end_date: date | None = None
    # 정책 한 줄 요약. SERVER가 보내지 않으면 None — 제목만으로 안내한다.
    summary: str | None = None
    # 지원 대상·지원 내용 원문 앞부분. 추천 이유·비교표·핵심 정보(금액 등)를 쓸 때 근거로 쓴다. 없으면 None.
    target: str | None = None
    benefit: str | None = None


class GroundingUnresolvedCondition(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    axis: ConditionAxis
    raw_text: str


class GroundingConditionResult(BaseModel):
    """SERVER가 판정한 조건별 자격 결과. AI는 판정을 바꾸지 않고 설명에만 쓴다."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    type: str
    status: str
    reason: str | None = None


class PolicyDetailGrounding(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    title: str
    summary: str
    eligibility: str
    application_period: str
    organization: str
    # 아래는 SERVER가 보낼 때만 채워지는 선택 항목이다. 없으면 None — 해당 항목은 설명하지 않는다.
    benefit: str | None = None
    application_method: str | None = None
    required_documents: str | None = None
    contact: str | None = None
    application_url: str | None = None
    # 정책 카드·비교에 쓰는 id와, 사용자가 말한 조건으로 SERVER가 판정한 자격 결과(있을 때만).
    policy_id: int | None = None
    eligibility_status: EligibilityStatus | None = None
    condition_results: list[GroundingConditionResult] = Field(default_factory=list)
    # SERVER가 캐시된 신청 가이드로 신청 절차·준비 서류를 화면에 붙이면 True — 이때 AI는 단계·서류를 쓰지 않는다.
    application_guide_attached: bool = False


class ChatTurn(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    message: str
    reply: str


class ChatResponseRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    message: str
    grounding_policies: list[GroundingPolicy] = Field(default_factory=list)
    policy_detail: PolicyDetailGrounding | None = None
    unresolved_conditions: list[GroundingUnresolvedCondition] = Field(default_factory=list)
    history: list[ChatTurn] = Field(default_factory=list)

    @field_validator("message")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("빈 문자열은 허용되지 않습니다.")
        return value


class ChatResponseType(StrEnum):
    """질문 의도에 따른 답변 유형. 유형마다 쓰는 블록 조합이 다르다(프롬프트 참고)."""

    RECOMMEND = "RECOMMEND"  # 추천·탐색
    COMPARE = "COMPARE"  # 비교
    HOW_TO_APPLY = "HOW_TO_APPLY"  # 신청 방법
    ELIGIBILITY = "ELIGIBILITY"  # 자격 확인
    CLARIFY = "CLARIFY"  # 정보 부족 — 되묻기
    TERM = "TERM"  # 용어 설명
    NO_RESULT = "NO_RESULT"  # 맞는 정책 없음
    GENERAL = "GENERAL"  # 인사·일반 대화


class ChatBlockType(StrEnum):
    TEXT = "TEXT"  # text
    POLICY_GROUP = "POLICY_GROUP"  # title(그룹명) + policies
    COMPARISON = "COMPARISON"  # policyIds(열) + rows
    CONCLUSION = "CONCLUSION"  # text — MOZIP 아이콘과 함께 보이는 한 줄 결론
    STEPS = "STEPS"  # title + steps
    CHECKLIST = "CHECKLIST"  # title + items
    TERM = "TERM"  # title(용어) + text(정의) + example
    QUICK_REPLIES = "QUICK_REPLIES"  # text(질문, 선택) + items(누르면 그대로 전송되는 답)


class ChatBlockPolicy(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    policy_id: int
    # 정책 제목(주어진 title 그대로). 모델이 policyId를 잘못 옮겼을 때 제목으로 정책을 찾는다.
    title: str | None = None
    # 사용자 상황과 연결한 추천 이유 한 줄
    reason: str
    # 금액·기간처럼 카드에 칩으로 보여줄 핵심 정보 한 가지(원문에 있을 때만)
    highlight: str | None = None


class PolicyFit(StrEnum):
    BEST = "BEST"  # 질문 주제에 직접 맞는 정책 — '딱 맞는 정책'
    RELATED = "RELATED"  # 주제는 다르지만 사용자 상황에 도움이 되는 정책 — '함께 보면 좋은 정책'
    EXCLUDE = "EXCLUDE"  # 질문·상황과 맞지 않아 보여주지 않을 정책


class ChatPolicyNote(BaseModel):
    """주어진 정책 하나에 대한 모델의 판단. 정책 카드는 이 목록으로 만든다(블록 안에 id를 섞어 쓰게 하면 자주 틀린다)."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={"required": ["policyId", "title", "fit", "reason", "highlight"]},
    )

    policy_id: int
    title: str = ""
    fit: PolicyFit = PolicyFit.RELATED
    reason: str = ""
    highlight: str | None = None


class ChatComparisonRow(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    label: str
    # policyIds 순서대로 한 칸씩
    values: list[str] = Field(default_factory=list)


class ChatStep(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    title: str
    description: str | None = None


class ChatBlock(BaseModel):
    """블록 하나. 종류(type)에 따라 쓰는 필드만 채우고 나머지는 비운다."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    type: ChatBlockType
    text: str | None = None
    title: str | None = None
    example: str | None = None
    policies: list[ChatBlockPolicy] = Field(default_factory=list)
    policy_ids: list[int] = Field(default_factory=list)
    rows: list[ChatComparisonRow] = Field(default_factory=list)
    steps: list[ChatStep] = Field(default_factory=list)
    items: list[str] = Field(default_factory=list)


class ChatResponseResponse(BaseModel):
    # 모델이 reply만 채우고 blocks를 비우는 일이 없도록 structured output 스키마에서는 모든 필드를 필수로,
    # blocks는 1개 이상으로 요구한다. 파싱할 때는 기본값을 둬서 일부가 빠져도 실패하지 않게 한다.
    # 필드 순서도 생성 순서가 되므로 유형 → 블록 → 후속 질문 → 요약 순으로 둔다.
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra=lambda schema: schema.update(
            required=["responseType", "blocks", "policyNotes", "followUps", "reply"]
        )
        or schema["properties"]["blocks"].update(minItems=1),
    )

    response_type: ChatResponseType = ChatResponseType.GENERAL
    blocks: list[ChatBlock] = Field(default_factory=list)
    # 주어진 정책마다 하나씩: 딱 맞는지·함께 볼지·뺄지와 추천 이유. 정책 카드(POLICY_GROUP)는 이걸로 만든다.
    policy_notes: list[ChatPolicyNote] = Field(default_factory=list)
    # 답변 아래에 칩으로 보여줄 후속 질문(사용자 말투, 최대 3개)
    follow_ups: list[str] = Field(default_factory=list)
    # 답변 전체를 1~2문장으로 요약한 문장. 블록을 못 그리는 화면과 대화 기록(history)에 쓴다.
    reply: str
