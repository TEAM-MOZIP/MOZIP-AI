from datetime import date

from rdflib import Graph

from app.ontology.mapper import map_policy, map_user
from app.ontology.matcher import match_concepts
from app.schemas.mapping import PolicyMappingInput, UserMappingInput
from app.schemas.semantic_match import SemanticMatchResult


def calculate_semantic_match(
    user_input: UserMappingInput,
    policy_input: PolicyMappingInput,
    graph: Graph,
    reference_date: date,
) -> SemanticMatchResult:
    user_mapping = map_user(user_input, graph, reference_date)
    policy_mapping = map_policy(policy_input, graph)
    return match_concepts(user_mapping, policy_mapping, graph)
