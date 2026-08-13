from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.schemas.mapping import MappingAxis


class MatchedConcept(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    axis: MappingAxis
    user_concept_uri: str
    user_concept_code: str
    policy_concept_uri: str
    policy_concept_code: str


class InferencePath(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    axis: MappingAxis
    from_concept_uri: str
    relations: list[str] = Field(default_factory=list)
    to_concept_uri: str


class SemanticMatchResult(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    semantic_score: float | None
    matched_concepts: list[MatchedConcept] = Field(default_factory=list)
    inference_paths: list[InferencePath] = Field(default_factory=list)
