from datetime import date, timedelta

import pytest

from app.core.exceptions import AppException
from app.ontology.loader import _load_graph
from app.ontology.mapper import map_policy, map_user
from app.ontology.matcher import match_concepts
from app.schemas.mapping import PolicyMappingInput, UserMappingInput
from app.services.semantic_match_service import calculate_semantic_match

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
