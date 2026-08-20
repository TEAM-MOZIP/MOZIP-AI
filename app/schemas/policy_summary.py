from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from pydantic.alias_generators import to_camel


class PolicySummaryRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    title: str
    description: str | None = None
    target_description: str | None = None
    benefit_description: str | None = None

    @field_validator("title")
    @classmethod
    def _reject_blank_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("빈 문자열은 허용되지 않습니다.")
        return value

    @model_validator(mode="after")
    def _require_at_least_one_source(self) -> "PolicySummaryRequest":
        sources = (self.description, self.target_description, self.benefit_description)
        if not any(source and source.strip() for source in sources):
            raise ValueError(
                "description, targetDescription, benefitDescription 중 하나는 값이 있어야 합니다."
            )
        return self


class PolicySummaryResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    summary: str

    @field_validator("summary")
    @classmethod
    def _reject_blank_summary(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("빈 문자열은 허용되지 않습니다.")
        return value
