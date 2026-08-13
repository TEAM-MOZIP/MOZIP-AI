from pydantic import BaseModel

from app.schemas.mapping import PolicyMappingInput, UserMappingInput
from app.schemas.semantic_match import SemanticMatchResult


class SemanticMatchBatchPolicyItem(PolicyMappingInput):
    policy_id: int


class SemanticMatchBatchRequest(BaseModel):
    user: UserMappingInput
    policies: list[SemanticMatchBatchPolicyItem]


class SemanticMatchBatchResultItem(SemanticMatchResult):
    policy_id: int


class SemanticMatchBatchResponse(BaseModel):
    results: list[SemanticMatchBatchResultItem]
