from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class ApplicationGuideRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    application_instructions: str
    required_documents_source: str | None = None

    @field_validator("application_instructions")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("빈 문자열은 허용되지 않습니다.")
        return value


class ApplicationGuideStep(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    order: int = Field(ge=1)
    title: str
    description: str


class ApplicationGuideResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    steps: list[ApplicationGuideStep] = Field(min_length=1)
    required_documents: list[str] = Field(default_factory=list)
