import pytest
from rdflib import Graph

from app.core.exceptions import AppException
from app.ontology.loader import _load_graph
from app.schemas.condition_extraction import ConditionExtractionRequest, _ConditionExpressions
from app.schemas.mapping import EmploymentStatus, Gender
from app.services.condition_extraction_service import extract_conditions

FIXTURE_PATH = "app/tests/fixtures/test_region_resolver_ontology.ttl"


class _FakeLlmClient:
    def __init__(self, expressions: _ConditionExpressions) -> None:
        self._expressions = expressions

    def generate_structured(self, system_instruction, user_content, response_schema):
        return self._expressions


@pytest.fixture
def graph() -> Graph:
    return _load_graph(FIXTURE_PATH)


def test_extract_conditions_resolves_single_axis(graph):
    request = ConditionExtractionRequest(free_text="여성입니다")
    fake = _FakeLlmClient(_ConditionExpressions(gender_expressions=["여성"]))

    result = extract_conditions(request, fake, graph)

    assert result.gender == Gender.FEMALE
    assert result.unresolved_conditions == []


def test_extract_conditions_resolves_multiple_axes(graph):
    request = ConditionExtractionRequest(free_text="강남 사는 25살 여자 취준생")
    fake = _FakeLlmClient(
        _ConditionExpressions(
            gender_expressions=["여자"],
            age_expressions=["25살"],
            region_expressions=["강남"],
            employment_status_expressions=["취준생"],
        )
    )

    result = extract_conditions(request, fake, graph)

    assert result.gender == Gender.FEMALE
    assert result.age == 25
    assert result.region_code == "SEOUL_GANGNAM"
    assert result.employment_status == EmploymentStatus.JOB_SEEKER
    assert result.household_type is None
    assert result.income_type is None
    assert result.income_value is None
    assert result.unresolved_conditions == []


def test_extract_conditions_merges_expressions_sharing_canonical_value(graph):
    request = ConditionExtractionRequest(free_text="여자이고 여성입니다")
    fake = _FakeLlmClient(_ConditionExpressions(gender_expressions=["여자", "여성"]))

    result = extract_conditions(request, fake, graph)

    assert result.gender == Gender.FEMALE
    assert result.unresolved_conditions == []


def test_extract_conditions_keeps_conflicting_expressions_unresolved(graph):
    request = ConditionExtractionRequest(free_text="직장인이었는데 지금은 취준생이에요")
    fake = _FakeLlmClient(_ConditionExpressions(employment_status_expressions=["직장인", "취준생"]))

    result = extract_conditions(request, fake, graph)

    assert result.employment_status is None
    assert [(c.axis, c.raw_text) for c in result.unresolved_conditions] == [
        ("employment_status", "직장인"),
        ("employment_status", "취준생"),
    ]


def test_extract_conditions_keeps_unresolvable_expression(graph):
    request = ConditionExtractionRequest(free_text="연봉 3000만원이에요")
    fake = _FakeLlmClient(_ConditionExpressions(income_expressions=["연봉 3000만원"]))

    result = extract_conditions(request, fake, graph)

    assert result.income_type is None
    assert result.income_value is None
    assert [(c.axis, c.raw_text) for c in result.unresolved_conditions] == [
        ("income", "연봉 3000만원")
    ]


def test_extract_conditions_raises_when_expression_not_in_free_text(graph):
    request = ConditionExtractionRequest(free_text="저는 프리랜서예요")
    fake = _FakeLlmClient(_ConditionExpressions(employment_status_expressions=["자유 계약 근로자"]))

    with pytest.raises(AppException) as exc_info:
        extract_conditions(request, fake, graph)

    assert exc_info.value.code == "INTERNAL_ERROR"
    assert exc_info.value.status_code == 500


def test_extract_conditions_fails_whole_request_even_when_other_axes_are_valid(graph):
    request = ConditionExtractionRequest(free_text="서울 사는 취준생이에요")
    fake = _FakeLlmClient(
        _ConditionExpressions(
            region_expressions=["서울"],
            employment_status_expressions=["취준생"],
            gender_expressions=["여성"],
        )
    )

    with pytest.raises(AppException) as exc_info:
        extract_conditions(request, fake, graph)

    assert exc_info.value.code == "INTERNAL_ERROR"
