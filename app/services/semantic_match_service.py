from datetime import date

from rdflib import Graph

from app.ontology.mapper import map_policy, map_user
from app.ontology.matcher import match_concepts
from app.schemas.mapping import PolicyMappingInput, UserMappingInput
from app.schemas.semantic_match import SemanticMatchResult
from app.schemas.semantic_match_api import (
    SemanticMatchBatchPolicyItem,
    SemanticMatchBatchResultItem,
)


def calculate_semantic_match(
    user_input: UserMappingInput,
    policy_input: PolicyMappingInput,
    graph: Graph,
    reference_date: date,
) -> SemanticMatchResult:
    user_mapping = map_user(user_input, graph, reference_date)
    policy_mapping = map_policy(policy_input, graph)
    return match_concepts(user_mapping, policy_mapping, graph)


def calculate_semantic_match_batch(
    user_input: UserMappingInput,
    policies: list[SemanticMatchBatchPolicyItem],
    graph: Graph,
    reference_date: date,
) -> list[SemanticMatchBatchResultItem]:
    results: list[SemanticMatchBatchResultItem] = []
    for policy in policies:
        result = calculate_semantic_match(user_input, policy, graph, reference_date)
        results.append(
            SemanticMatchBatchResultItem(
                policy_id=policy.policy_id,
                semantic_score=result.semantic_score,
                matched_concepts=result.matched_concepts,
                inference_paths=result.inference_paths,
            )
        )
    return results
