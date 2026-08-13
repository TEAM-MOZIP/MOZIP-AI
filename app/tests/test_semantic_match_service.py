from datetime import date, timedelta

import pytest

from app.core.exceptions import AppException
from app.ontology.loader import _load_graph
from app.ontology.mapper import map_policy, map_user
from app.ontology.matcher import match_concepts
from app.schemas.mapping import PolicyMappingInput, UserMappingInput
from app.schemas.semantic_match_api import SemanticMatchBatchPolicyItem
from app.services.semantic_match_service import (
    calculate_semantic_match,
    calculate_semantic_match_batch,
)

FIXTURE_PATH = "app/tests/fixtures/test_user_mapping_ontology.ttl"
REFERENCE_DATE = date(2026, 6, 15)


@pytest.fixture
def graph():
    return _load_graph(FIXTURE_PATH)


def test_service_result_matches_manual_pipeline(graph):
    user_input = UserMappingInput(
        gender="MALE",
        birth_date=date(2000, 6, 15),
        region_code="SEOUL",
        employment_status="JOB_SEEKER",
        household_type="SINGLE",
        income_type="ABSOLUTE",
    )
    policy_input = PolicyMappingInput(
        region_scope="REGIONAL",
        region_codes=["SEOUL"],
        minimum_age=20,
        maximum_age=32,
        gender_condition="MALE",
        income_type="MEDIAN_PERCENTAGE",
        allowed_employment_statuses=["JOB_SEEKER"],
        allowed_household_types=["ELDERLY"],
    )

    actual = calculate_semantic_match(user_input, policy_input, graph, REFERENCE_DATE)

    user_mapping = map_user(user_input, graph, REFERENCE_DATE)
    policy_mapping = map_policy(policy_input, graph)
    expected = match_concepts(user_mapping, policy_mapping, graph)

    assert actual == expected


def test_user_mapper_app_exception_propagates(graph):
    user_input = UserMappingInput(gender="MALE", birth_date=REFERENCE_DATE + timedelta(days=1))
    policy_input = PolicyMappingInput(region_scope="NATIONAL")

    with pytest.raises(AppException) as exc_info:
        calculate_semantic_match(user_input, policy_input, graph, REFERENCE_DATE)

    assert exc_info.value.code == "INVALID_BIRTH_DATE"
    assert exc_info.value.status_code == 400


def test_policy_mapper_app_exception_propagates(graph):
    user_input = UserMappingInput(gender="MALE")
    policy_input = PolicyMappingInput(region_scope="NATIONAL", minimum_age=40, maximum_age=30)

    with pytest.raises(AppException) as exc_info:
        calculate_semantic_match(user_input, policy_input, graph, REFERENCE_DATE)

    assert exc_info.value.code == "INVALID_AGE_RANGE"
    assert exc_info.value.status_code == 400


def test_batch_preserves_order_and_policy_id_correlation(graph):
    user_input = UserMappingInput(gender="MALE")
    policies = [
        SemanticMatchBatchPolicyItem(policy_id=3, region_scope="NATIONAL"),
        SemanticMatchBatchPolicyItem(policy_id=1, region_scope="NATIONAL", gender_condition="MALE"),
        SemanticMatchBatchPolicyItem(
            policy_id=2, region_scope="NATIONAL", gender_condition="FEMALE"
        ),
    ]

    results = calculate_semantic_match_batch(user_input, policies, graph, REFERENCE_DATE)

    assert [result.policy_id for result in results] == [3, 1, 2]


def test_batch_result_matches_single_item_calculation(graph):
    user_input = UserMappingInput(
        gender="MALE", region_code="SEOUL_GANGNAM", employment_status="JOB_SEEKER"
    )
    policy_item = SemanticMatchBatchPolicyItem(
        policy_id=42,
        region_scope="REGIONAL",
        region_codes=["SEOUL"],
        allowed_employment_statuses=["JOB_SEEKER"],
    )

    [batch_result] = calculate_semantic_match_batch(
        user_input, [policy_item], graph, REFERENCE_DATE
    )
    single_result = calculate_semantic_match(user_input, policy_item, graph, REFERENCE_DATE)

    assert batch_result.policy_id == 42
    assert batch_result.semantic_score == single_result.semantic_score
    assert batch_result.matched_concepts == single_result.matched_concepts
    assert batch_result.inference_paths == single_result.inference_paths


def test_batch_propagates_app_exception_from_underlying_mapper(graph):
    user_input = UserMappingInput(gender="MALE", birth_date=REFERENCE_DATE + timedelta(days=1))
    policies = [SemanticMatchBatchPolicyItem(policy_id=1, region_scope="NATIONAL")]

    with pytest.raises(AppException) as exc_info:
        calculate_semantic_match_batch(user_input, policies, graph, REFERENCE_DATE)

    assert exc_info.value.code == "INVALID_BIRTH_DATE"


def test_batch_with_empty_policies_returns_empty_list(graph):
    user_input = UserMappingInput(gender="MALE")

    results = calculate_semantic_match_batch(user_input, [], graph, REFERENCE_DATE)

    assert results == []
