from datetime import date

from rdflib import Graph, Namespace

from app.core.exceptions import AppException
from app.ontology.graph import concept_exists
from app.schemas.mapping import (
    MappedConcept,
    UnmappedField,
    UnmappedReason,
    UserConceptMapping,
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


def _map_field(
    graph: Graph,
    field: str,
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


def map_user(
    input_data: UserMappingInput, graph: Graph, reference_date: date
) -> UserConceptMapping:
    concepts: list[MappedConcept] = []
    unmapped: list[UnmappedField] = []

    _map_field(graph, "gender", input_data.gender.value, concepts, unmapped)
    _map_field(
        graph,
        "employment_status",
        input_data.employment_status.value if input_data.employment_status else None,
        concepts,
        unmapped,
    )
    _map_field(
        graph,
        "household_type",
        input_data.household_type.value if input_data.household_type else None,
        concepts,
        unmapped,
    )
    _map_field(
        graph,
        "income_type",
        input_data.income_type.value if input_data.income_type else None,
        concepts,
        unmapped,
    )
    _map_field(graph, "region_code", input_data.region_code, concepts, unmapped)

    if input_data.birth_date is None:
        unmapped.append(UnmappedField(field="birth_date", reason=UnmappedReason.MISSING_VALUE))
    else:
        age = _calculate_age(input_data.birth_date, reference_date)
        _map_field(graph, "birth_date", _age_group_name(age), concepts, unmapped)

    return UserConceptMapping(concepts=concepts, unmapped=unmapped)
