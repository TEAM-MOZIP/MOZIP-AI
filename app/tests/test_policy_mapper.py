import pytest

from app.core.exceptions import AppException
from app.ontology.loader import _load_graph
from app.ontology.mapper import map_policy
from app.schemas.mapping import PolicyMappingInput, UnmappedReason

FIXTURE_PATH = "app/tests/fixtures/test_user_mapping_ontology.ttl"


@pytest.fixture
def graph():
    return _load_graph(FIXTURE_PATH)


def test_maps_all_axes_when_all_present(graph):
    input_data = PolicyMappingInput(
        region_scope="REGIONAL",
        region_codes=["SEOUL"],
        minimum_age=25,
        maximum_age=25,
        gender_condition="MALE",
        income_type="ABSOLUTE",
        allowed_employment_statuses=["JOB_SEEKER"],
        allowed_household_types=["SINGLE"],
    )

    result = map_policy(input_data, graph)

    assert result.unmapped == []
    fields = {c.field for c in result.concepts}
    assert fields == {
        "gender",
        "income_type",
        "employment_status",
        "household_type",
        "region",
        "age_group",
    }


def test_missing_scalar_and_list_axes_marked_missing_value(graph):
    input_data = PolicyMappingInput(region_scope="NATIONAL")

    result = map_policy(input_data, graph)

    assert result.concepts == []
    unmapped_by_field = {u.field: u.reason for u in result.unmapped}
    assert unmapped_by_field == {
        "gender": UnmappedReason.MISSING_VALUE,
        "income_type": UnmappedReason.MISSING_VALUE,
        "employment_status": UnmappedReason.MISSING_VALUE,
        "household_type": UnmappedReason.MISSING_VALUE,
        "age_group": UnmappedReason.MISSING_VALUE,
    }
    assert "region" not in unmapped_by_field


def test_unknown_region_code_marked_unknown_value(graph):
    input_data = PolicyMappingInput(region_scope="REGIONAL", region_codes=["ATLANTIS"])

    result = map_policy(input_data, graph)

    unmapped_by_field = {u.field: u.reason for u in result.unmapped}
    assert unmapped_by_field["region"] == UnmappedReason.UNKNOWN_VALUE
    assert "region" not in {c.field for c in result.concepts}


def test_seoul_district_region_code_maps_without_mapper_changes(graph):
    # 서울 자치구 code(mozip.owl에 SEOUL의 하위로 추가된 개념)도 코드 변경 없이
    # 기존 URI 조회 로직만으로 매핑되는지 확인하는 회귀 테스트.
    input_data = PolicyMappingInput(region_scope="REGIONAL", region_codes=["SEOUL_GANGNAM"])

    result = map_policy(input_data, graph)

    region_concept = next(c for c in result.concepts if c.field == "region")
    assert region_concept.concept_code == "SEOUL_GANGNAM"
    assert region_concept.concept_uri == "http://mozip.ai/ontology#SEOUL_GANGNAM"


def test_unknown_employment_status_string_marked_unknown_value(graph):
    input_data = PolicyMappingInput(
        region_scope="NATIONAL", allowed_employment_statuses=["STUDENT"]
    )

    result = map_policy(input_data, graph)

    unmapped_by_field = {u.field: u.reason for u in result.unmapped}
    assert unmapped_by_field["employment_status"] == UnmappedReason.UNKNOWN_VALUE


def test_multiple_allowed_employment_statuses_mapped_individually(graph):
    input_data = PolicyMappingInput(
        region_scope="NATIONAL",
        allowed_employment_statuses=["EMPLOYED", "JOB_SEEKER"],
    )

    result = map_policy(input_data, graph)

    employment_concepts = [c for c in result.concepts if c.field == "employment_status"]
    assert {c.concept_code for c in employment_concepts} == {"EMPLOYED", "JOB_SEEKER"}


def test_duplicate_list_values_are_mapped_once_preserving_order(graph):
    input_data = PolicyMappingInput(
        region_scope="NATIONAL",
        allowed_employment_statuses=["EMPLOYED", "EMPLOYED"],
    )

    result = map_policy(input_data, graph)

    employment_concepts = [c for c in result.concepts if c.field == "employment_status"]
    assert [c.concept_code for c in employment_concepts] == ["EMPLOYED"]


def test_duplicate_and_unmapped_values_mixed_in_one_list(graph):
    input_data = PolicyMappingInput(
        region_scope="NATIONAL",
        allowed_employment_statuses=["EMPLOYED", "STUDENT", "EMPLOYED"],
    )

    result = map_policy(input_data, graph)

    employment_concepts = [c for c in result.concepts if c.field == "employment_status"]
    assert [c.concept_code for c in employment_concepts] == ["EMPLOYED"]

    employment_unmapped = [u for u in result.unmapped if u.field == "employment_status"]
    assert len(employment_unmapped) == 1
    assert employment_unmapped[0].reason == UnmappedReason.UNKNOWN_VALUE


def test_duplicate_region_codes_mapped_once(graph):
    input_data = PolicyMappingInput(region_scope="REGIONAL", region_codes=["SEOUL", "SEOUL"])

    result = map_policy(input_data, graph)

    region_concepts = [c for c in result.concepts if c.field == "region"]
    assert [c.concept_code for c in region_concepts] == ["SEOUL"]


@pytest.mark.parametrize(
    ("minimum_age", "maximum_age", "expected_age_groups"),
    [
        (20, 32, ["AGE_19_24", "AGE_25_29", "AGE_30_34"]),
        (60, None, ["AGE_50_64", "AGE_65_PLUS"]),
        (None, 20, ["UNDER_19", "AGE_19_24"]),
        (None, None, []),
    ],
)
def test_age_group_range_overlap(graph, minimum_age, maximum_age, expected_age_groups):
    input_data = PolicyMappingInput(
        region_scope="NATIONAL", minimum_age=minimum_age, maximum_age=maximum_age
    )

    result = map_policy(input_data, graph)

    age_group_codes = {c.concept_code for c in result.concepts if c.field == "age_group"}
    assert age_group_codes == set(expected_age_groups)

    if not expected_age_groups:
        unmapped_by_field = {u.field: u.reason for u in result.unmapped}
        assert unmapped_by_field["age_group"] == UnmappedReason.MISSING_VALUE


def test_minimum_age_greater_than_maximum_age_raises_app_exception(graph):
    input_data = PolicyMappingInput(region_scope="NATIONAL", minimum_age=40, maximum_age=30)

    with pytest.raises(AppException) as exc_info:
        map_policy(input_data, graph)

    assert exc_info.value.code == "INVALID_AGE_RANGE"


def test_negative_minimum_age_raises_app_exception(graph):
    input_data = PolicyMappingInput(region_scope="NATIONAL", minimum_age=-1)

    with pytest.raises(AppException) as exc_info:
        map_policy(input_data, graph)

    assert exc_info.value.code == "INVALID_AGE_RANGE"


def test_negative_maximum_age_raises_app_exception(graph):
    input_data = PolicyMappingInput(region_scope="NATIONAL", maximum_age=-1)

    with pytest.raises(AppException) as exc_info:
        map_policy(input_data, graph)

    assert exc_info.value.code == "INVALID_AGE_RANGE"


def test_large_maximum_age_overlaps_open_ended_band(graph):
    input_data = PolicyMappingInput(region_scope="NATIONAL", minimum_age=200, maximum_age=250)

    result = map_policy(input_data, graph)

    age_group_codes = {c.concept_code for c in result.concepts if c.field == "age_group"}
    assert age_group_codes == {"AGE_65_PLUS"}


def test_national_scope_does_not_map_region_even_without_codes(graph):
    input_data = PolicyMappingInput(region_scope="NATIONAL")

    result = map_policy(input_data, graph)

    assert "region" not in {c.field for c in result.concepts}
    assert "region" not in {u.field for u in result.unmapped}


def test_national_scope_ignores_region_codes_if_present(graph):
    input_data = PolicyMappingInput(region_scope="NATIONAL", region_codes=["SEOUL"])

    result = map_policy(input_data, graph)

    assert "region" not in {c.field for c in result.concepts}
    assert "region" not in {u.field for u in result.unmapped}


def test_regional_scope_with_codes_maps_region(graph):
    input_data = PolicyMappingInput(region_scope="REGIONAL", region_codes=["SEOUL"])

    result = map_policy(input_data, graph)

    region_concepts = [c for c in result.concepts if c.field == "region"]
    assert len(region_concepts) == 1
    assert region_concepts[0].concept_code == "SEOUL"


def test_regional_scope_without_codes_marks_region_missing(graph):
    input_data = PolicyMappingInput(region_scope="REGIONAL", region_codes=[])

    result = map_policy(input_data, graph)

    unmapped_by_field = {u.field: u.reason for u in result.unmapped}
    assert unmapped_by_field["region"] == UnmappedReason.MISSING_VALUE


def test_map_policy_result_is_deterministic(graph):
    input_data = PolicyMappingInput(
        region_scope="REGIONAL",
        region_codes=["SEOUL"],
        minimum_age=20,
        maximum_age=32,
        gender_condition="MALE",
        income_type="ABSOLUTE",
        allowed_employment_statuses=["EMPLOYED", "JOB_SEEKER"],
        allowed_household_types=["SINGLE"],
    )

    first = map_policy(input_data, graph)
    second = map_policy(input_data, graph)

    assert first == second
    assert [c.field for c in first.concepts] == [c.field for c in second.concepts]


def test_map_policy_does_not_mutate_graph(graph):
    triple_count_before = len(graph)
    input_data = PolicyMappingInput(
        region_scope="REGIONAL",
        region_codes=["SEOUL"],
        minimum_age=20,
        maximum_age=32,
        gender_condition="MALE",
        income_type="ABSOLUTE",
        allowed_employment_statuses=["EMPLOYED"],
        allowed_household_types=["SINGLE"],
    )

    map_policy(input_data, graph)

    assert len(graph) == triple_count_before
