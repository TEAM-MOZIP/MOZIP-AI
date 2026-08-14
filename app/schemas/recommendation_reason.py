from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class EligibilityStatus(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ConditionType(StrEnum):
    AGE = "AGE"
    REGION = "REGION"
    INCOME = "INCOME"
    EMPLOYMENT_STATUS = "EMPLOYMENT_STATUS"
    HOUSEHOLD_TYPE = "HOUSEHOLD_TYPE"
    GENDER = "GENDER"
    ADDITIONAL_CONDITIONS = "ADDITIONAL_CONDITIONS"


class ConditionStatus(StrEnum):
    MATCHED = "MATCHED"
    NOT_MATCHED = "NOT_MATCHED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class Condition(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    type: ConditionType
    status: ConditionStatus
    reason: str


class RecommendationExplainRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    policy_title: str
    eligibility_status: EligibilityStatus
    conditions: list[Condition] = Field(default_factory=list)


class RecommendationExplainResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    reason: str
