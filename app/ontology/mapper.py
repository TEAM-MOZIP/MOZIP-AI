from datetime import date

from rdflib import Graph, Namespace

from app.core.exceptions import AppException
from app.ontology.graph import concept_exists
from app.schemas.mapping import (
    ConceptMapping,
    MappedConcept,
    MappingAxis,
    PolicyMappingInput,
    RegionScope,
    UnmappedField,
    UnmappedReason,
    UserMappingInput,
)

MZ = Namespace("http://mozip.ai/ontology#")

# SERVER policy.domain.AgeGroup과 동일한 구간. (이름, 최소 나이, 최대 나이) — 경계값 포함.
_AGE_GROUP_BANDS: list[tuple[str, int | None, int | None]] = [
    ("UNDER_19", None, 18),
    ("AGE_19_24", 19, 24),
    ("AGE_25_29", 25, 29),
    ("AGE_30_34", 30, 34),
    ("AGE_35_49", 35, 49),
    ("AGE_50_64", 50, 64),
    ("AGE_65_PLUS", 65, None),
]


def _calculate_age(birth_date: date, reference_date: date) -> int:
    if birth_date > reference_date:
        raise AppException(
            "생년월일이 기준 날짜보다 미래일 수 없습니다.",
            code="INVALID_BIRTH_DATE",
            status_code=400,
        )

    age = reference_date.year - birth_date.year
    if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def _age_group_name(age: int) -> str:
    for name, band_min, band_max in _AGE_GROUP_BANDS:
        if (band_min is None or age >= band_min) and (band_max is None or age <= band_max):
            return name
    raise AssertionError(f"AgeGroup 구간이 나이 {age}를 포함하지 않습니다.")  # pragma: no cover


def _age_group_names_for_range(minimum_age: int | None, maximum_age: int | None) -> list[str]:
    if minimum_age is None and maximum_age is None:
        return []

    if minimum_age is not None and minimum_age < 0:
        raise AppException(
            "minimum_age는 음수일 수 없습니다.",
            code="INVALID_AGE_RANGE",
            status_code=400,
        )
    if maximum_age is not None and maximum_age < 0:
        raise AppException(
            "maximum_age는 음수일 수 없습니다.",
            code="INVALID_AGE_RANGE",
            status_code=400,
        )
    if minimum_age is not None and maximum_age is not None and minimum_age > maximum_age:
        raise AppException(
            "minimum_age가 maximum_age보다 클 수 없습니다.",
            code="INVALID_AGE_RANGE",
            status_code=400,
        )

    names = []
    for name, band_min, band_max in _AGE_GROUP_BANDS:
        lower_ok = minimum_age is None or band_max is None or band_max >= minimum_age
        upper_ok = maximum_age is None or band_min is None or band_min <= maximum_age
        if lower_ok and upper_ok:
            names.append(name)
    return names


def _deduplicate_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique_values.append(value)
    return unique_values


def _map_field(
    graph: Graph,
    field: MappingAxis,
    value: str | None,
    concepts: list[MappedConcept],
    unmapped: list[UnmappedField],
) -> None:
    if value is None:
        unmapped.append(UnmappedField(field=field, reason=UnmappedReason.MISSING_VALUE))
        return

    uri = MZ[value]
    if not concept_exists(graph, uri):
        unmapped.append(UnmappedField(field=field, reason=UnmappedReason.UNKNOWN_VALUE))
        return

    concepts.append(MappedConcept(field=field, concept_uri=str(uri), concept_code=value))


def _map_list_field(
    graph: Graph,
    field: MappingAxis,
    values: list[str],
    concepts: list[MappedConcept],
    unmapped: list[UnmappedField],
) -> None:
    if not values:
        unmapped.append(UnmappedField(field=field, reason=UnmappedReason.MISSING_VALUE))
        return

    for value in _deduplicate_preserving_order(values):
        _map_field(graph, field, value, concepts, unmapped)


def map_user(input_data: UserMappingInput, graph: Graph, reference_date: date) -> ConceptMapping:
    concepts: list[MappedConcept] = []
    unmapped: list[UnmappedField] = []

    _map_field(graph, MappingAxis.GENDER, input_data.gender.value, concepts, unmapped)
    _map_field(
        graph,
        MappingAxis.EMPLOYMENT_STATUS,
        input_data.employment_status.value if input_data.employment_status else None,
        concepts,
        unmapped,
    )
    _map_field(
        graph,
        MappingAxis.HOUSEHOLD_TYPE,
        input_data.household_type.value if input_data.household_type else None,
        concepts,
        unmapped,
    )
    _map_field(
        graph,
        MappingAxis.INCOME_TYPE,
        input_data.income_type.value if input_data.income_type else None,
        concepts,
        unmapped,
    )
    _map_field(graph, MappingAxis.REGION, input_data.region_code, concepts, unmapped)

    if input_data.birth_date is None:
        unmapped.append(
            UnmappedField(field=MappingAxis.AGE_GROUP, reason=UnmappedReason.MISSING_VALUE)
        )
    else:
        age = _calculate_age(input_data.birth_date, reference_date)
        _map_field(graph, MappingAxis.AGE_GROUP, _age_group_name(age), concepts, unmapped)

    return ConceptMapping(concepts=concepts, unmapped=unmapped)


def _map_policy_region(
    input_data: PolicyMappingInput,
    graph: Graph,
    concepts: list[MappedConcept],
    unmapped: list[UnmappedField],
) -> None:
    if input_data.region_scope == RegionScope.NATIONAL:
        return

    if not input_data.region_codes:
        unmapped.append(
            UnmappedField(field=MappingAxis.REGION, reason=UnmappedReason.MISSING_VALUE)
        )
        return

    for region_code in _deduplicate_preserving_order(input_data.region_codes):
        _map_field(graph, MappingAxis.REGION, region_code, concepts, unmapped)


def _map_policy_age_group(
    input_data: PolicyMappingInput,
    graph: Graph,
    concepts: list[MappedConcept],
    unmapped: list[UnmappedField],
) -> None:
    age_group_names = _age_group_names_for_range(input_data.minimum_age, input_data.maximum_age)

    if not age_group_names:
        unmapped.append(
            UnmappedField(field=MappingAxis.AGE_GROUP, reason=UnmappedReason.MISSING_VALUE)
        )
        return

    for name in age_group_names:
        _map_field(graph, MappingAxis.AGE_GROUP, name, concepts, unmapped)


def map_policy(input_data: PolicyMappingInput, graph: Graph) -> ConceptMapping:
    concepts: list[MappedConcept] = []
    unmapped: list[UnmappedField] = []

    _map_field(
        graph,
        MappingAxis.GENDER,
        input_data.gender_condition.value if input_data.gender_condition else None,
        concepts,
        unmapped,
    )
    _map_field(
        graph,
        MappingAxis.INCOME_TYPE,
        input_data.income_type.value if input_data.income_type else None,
        concepts,
        unmapped,
    )
    _map_list_field(
        graph,
        MappingAxis.EMPLOYMENT_STATUS,
        input_data.allowed_employment_statuses,
        concepts,
        unmapped,
    )
    _map_list_field(
        graph,
        MappingAxis.HOUSEHOLD_TYPE,
        input_data.allowed_household_types,
        concepts,
        unmapped,
    )
    _map_policy_region(input_data, graph, concepts, unmapped)
    _map_policy_age_group(input_data, graph, concepts, unmapped)

    return ConceptMapping(concepts=concepts, unmapped=unmapped)
