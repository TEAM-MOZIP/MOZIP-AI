from datetime import date, timedelta

import pytest

from app.core.exceptions import AppException
from app.ontology.loader import _load_graph
from app.ontology.mapper import map_user
from app.schemas.mapping import UnmappedReason, UserMappingInput

FIXTURE_PATH = "app/tests/fixtures/test_user_mapping_ontology.ttl"
REFERENCE_DATE = date(2026, 6, 15)


@pytest.fixture
def graph():
    return _load_graph(FIXTURE_PATH)


def test_maps_all_axes_when_all_present(graph):
    input_data = UserMappingInput(
        gender="MALE",
        birth_date=date(2000, 6, 15),
        region_code="SEOUL",
        employment_status="JOB_SEEKER",
        household_type="SINGLE",
        income_type="ABSOLUTE",
    )

    result = map_user(input_data, graph, REFERENCE_DATE)

    assert result.unmapped == []
    mapped_by_field = {concept.field: concept for concept in result.concepts}
    assert set(mapped_by_field) == {
        "gender",
        "employment_status",
        "household_type",
        "income_type",
        "region",
        "age_group",
    }

    gender_concept = mapped_by_field["gender"]
    assert gender_concept.concept_code == "MALE"
    assert gender_concept.concept_uri == "http://mozip.ai/ontology#MALE"

    age_group_concept = mapped_by_field["age_group"]
    assert age_group_concept.concept_code == "AGE_25_29"
    assert age_group_concept.concept_uri == "http://mozip.ai/ontology#AGE_25_29"


def test_missing_optional_fields_marked_missing_value(graph):
    input_data = UserMappingInput(gender="FEMALE")

    result = map_user(input_data, graph, REFERENCE_DATE)

    assert [c.field for c in result.concepts] == ["gender"]
    unmapped_by_field = {u.field: u.reason for u in result.unmapped}
    assert unmapped_by_field == {
        "employment_status": UnmappedReason.MISSING_VALUE,
        "household_type": UnmappedReason.MISSING_VALUE,
        "income_type": UnmappedReason.MISSING_VALUE,
        "region": UnmappedReason.MISSING_VALUE,
        "age_group": UnmappedReason.MISSING_VALUE,
    }


def test_unknown_region_code_marked_unknown_value(graph):
    input_data = UserMappingInput(gender="MALE", region_code="ATLANTIS")

    result = map_user(input_data, graph, REFERENCE_DATE)

    unmapped_by_field = {u.field: u.reason for u in result.unmapped}
    assert unmapped_by_field["region"] == UnmappedReason.UNKNOWN_VALUE
    assert "region" not in {c.field for c in result.concepts}


def test_seoul_district_region_code_maps_without_mapper_changes(graph):
    # 서울 자치구 code(mozip.owl에 SEOUL의 하위로 추가된 개념)도 코드 변경 없이
    # 기존 URI 조회 로직만으로 매핑되는지 확인하는 회귀 테스트.
    input_data = UserMappingInput(gender="MALE", region_code="SEOUL_GANGNAM")

    result = map_user(input_data, graph, REFERENCE_DATE)

    region_concept = next(c for c in result.concepts if c.field == "region")
    assert region_concept.concept_code == "SEOUL_GANGNAM"
    assert region_concept.concept_uri == "http://mozip.ai/ontology#SEOUL_GANGNAM"


@pytest.mark.parametrize(
    ("age", "expected_age_group"),
    [
        (18, "UNDER_19"),
        (19, "AGE_19_24"),
        (24, "AGE_19_24"),
        (25, "AGE_25_29"),
        (29, "AGE_25_29"),
        (30, "AGE_30_34"),
        (34, "AGE_30_34"),
        (35, "AGE_35_49"),
        (49, "AGE_35_49"),
        (50, "AGE_50_64"),
        (64, "AGE_50_64"),
        (65, "AGE_65_PLUS"),
    ],
)
def test_age_group_boundaries(graph, age, expected_age_group):
    birth_date = date(REFERENCE_DATE.year - age, REFERENCE_DATE.month, REFERENCE_DATE.day)
    input_data = UserMappingInput(gender="MALE", birth_date=birth_date)

    result = map_user(input_data, graph, REFERENCE_DATE)

    age_group_concepts = [c for c in result.concepts if c.field == "age_group"]
    assert len(age_group_concepts) == 1
    assert age_group_concepts[0].concept_code == expected_age_group


def test_age_calculation_respects_birthday_not_yet_reached(graph):
    # 기준일(2026-06-15) 기준, 2001년생: 생일(6/14)이 하루 지났으면 만 25세(AGE_25_29),
    # 생일(6/16)이 하루 안 지났으면 만 24세(AGE_19_24) — 구간 경계를 실제로 넘나든다.
    birthday_already_passed = UserMappingInput(gender="MALE", birth_date=date(2001, 6, 14))
    birthday_not_yet_reached = UserMappingInput(gender="MALE", birth_date=date(2001, 6, 16))

    passed_result = map_user(birthday_already_passed, graph, REFERENCE_DATE)
    not_yet_result = map_user(birthday_not_yet_reached, graph, REFERENCE_DATE)

    passed_age_group = next(c for c in passed_result.concepts if c.field == "age_group")
    not_yet_age_group = next(c for c in not_yet_result.concepts if c.field == "age_group")

    assert passed_age_group.concept_code == "AGE_25_29"
    assert not_yet_age_group.concept_code == "AGE_19_24"


def test_future_birth_date_raises_app_exception(graph):
    input_data = UserMappingInput(gender="MALE", birth_date=REFERENCE_DATE + timedelta(days=1))

    with pytest.raises(AppException) as exc_info:
        map_user(input_data, graph, REFERENCE_DATE)

    assert exc_info.value.code == "INVALID_BIRTH_DATE"


def test_map_user_result_is_deterministic(graph):
    input_data = UserMappingInput(
        gender="MALE",
        birth_date=date(1995, 3, 1),
        region_code="SEOUL",
        employment_status="EMPLOYED",
        household_type="SINGLE",
        income_type="ABSOLUTE",
    )

    first = map_user(input_data, graph, REFERENCE_DATE)
    second = map_user(input_data, graph, REFERENCE_DATE)

    assert first == second


def test_map_user_does_not_mutate_graph(graph):
    triple_count_before = len(graph)
    input_data = UserMappingInput(
        gender="MALE",
        birth_date=date(1995, 3, 1),
        region_code="SEOUL",
        employment_status="EMPLOYED",
        household_type="SINGLE",
        income_type="ABSOLUTE",
    )

    map_user(input_data, graph, REFERENCE_DATE)

    assert len(graph) == triple_count_before
