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


class GroundingUnresolvedCondition(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    axis: ConditionAxis
    raw_text: str


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


class ChatResponseResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    reply: str
