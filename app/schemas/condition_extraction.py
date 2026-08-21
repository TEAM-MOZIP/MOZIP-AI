from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from app.schemas.mapping import EmploymentStatus, Gender, HouseholdType, IncomeType


class ConditionAxis(StrEnum):
    GENDER = "gender"
    AGE = "age"
    REGION = "region"
    EMPLOYMENT_STATUS = "employment_status"
    HOUSEHOLD_TYPE = "household_type"
    INCOME = "income"


# Gemini structured output 전용 내부 스키마. API 응답으로 노출하지 않는다.
class _ConditionExpressions(BaseModel):
    gender_expressions: list[str] = Field(default_factory=list)
    age_expressions: list[str] = Field(default_factory=list)
    region_expressions: list[str] = Field(default_factory=list)
    employment_status_expressions: list[str] = Field(default_factory=list)
    household_type_expressions: list[str] = Field(default_factory=list)
    income_expressions: list[str] = Field(default_factory=list)


class ConditionExtractionRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    free_text: str

    @field_validator("free_text")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("빈 문자열은 허용되지 않습니다.")
        return value


class UnresolvedCondition(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    axis: ConditionAxis
    raw_text: str


class ConditionExtractionResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    gender: Gender | None = None
    age: int | None = None
    region_code: str | None = None
    employment_status: EmploymentStatus | None = None
    household_type: HouseholdType | None = None
    income_type: IncomeType | None = None
    income_value: int | None = None
    unresolved_conditions: list[UnresolvedCondition] = Field(default_factory=list)
