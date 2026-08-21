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


class ChatResponseRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    message: str
    grounding_policies: list[GroundingPolicy] = Field(default_factory=list)
    policy_detail: PolicyDetailGrounding | None = None
    unresolved_conditions: list[GroundingUnresolvedCondition] = Field(default_factory=list)

    @field_validator("message")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("빈 문자열은 허용되지 않습니다.")
        return value


class ChatResponseResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    reply: str
