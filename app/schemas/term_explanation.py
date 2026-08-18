from pydantic import BaseModel, ConfigDict, field_validator
from pydantic.alias_generators import to_camel


class TermExplainRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    term: str
    context: str

    @field_validator("term", "context")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("빈 문자열은 허용되지 않습니다.")
        return value


class TermExplainResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    explanation: str
