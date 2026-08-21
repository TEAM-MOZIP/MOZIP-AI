import pytest
from fastapi.testclient import TestClient

from app.clients.llm_client import get_llm_client
from app.core.exceptions import AppException
from app.main import app
from app.ontology.loader import _load_graph, get_ontology_graph
from app.schemas.condition_extraction import _ConditionExpressions

FIXTURE_PATH = "app/tests/fixtures/test_region_resolver_ontology.ttl"
ENDPOINT = "/api/v1/conditions/extract"


class _FakeLlmClient:
    def __init__(self, expressions=None, error: Exception | None = None) -> None:
        self._expressions = expressions
        self._error = error

    def generate_structured(self, system_instruction, user_content, response_schema):
        if self._error is not None:
            raise self._error
        return self._expressions


@pytest.fixture(autouse=True)
def _override_ontology_graph():
    graph = _load_graph(FIXTURE_PATH)
    app.dependency_overrides[get_ontology_graph] = lambda: graph
    yield
    app.dependency_overrides.pop(get_ontology_graph, None)


@pytest.fixture(autouse=True)
def _clear_llm_override():
    yield
    app.dependency_overrides.pop(get_llm_client, None)


client = TestClient(app)


def test_returns_200_with_camel_case_response():
    fake = _FakeLlmClient(expressions=_ConditionExpressions(gender_expressions=["여성"]))
    app.dependency_overrides[get_llm_client] = lambda: fake

    response = client.post(ENDPOINT, json={"freeText": "여성입니다"})

    assert response.status_code == 200
    body = response.json()
    assert body["gender"] == "FEMALE"
    assert body["age"] is None
    assert body["regionCode"] is None
    assert body["employmentStatus"] is None
    assert body["householdType"] is None
    assert body["incomeType"] is None
    assert body["incomeValue"] is None
    assert body["unresolvedConditions"] == []


def test_response_preserves_unresolved_conditions_shape():
    fake = _FakeLlmClient(
        expressions=_ConditionExpressions(employment_status_expressions=["직장인", "취준생"])
    )
    app.dependency_overrides[get_llm_client] = lambda: fake

    response = client.post(ENDPOINT, json={"freeText": "직장인이었는데 지금은 취준생이에요"})

    assert response.status_code == 200
    body = response.json()
    assert body["employmentStatus"] is None
    assert body["unresolvedConditions"] == [
        {"axis": "employment_status", "rawText": "직장인"},
        {"axis": "employment_status", "rawText": "취준생"},
    ]


def test_missing_free_text_returns_422():
    app.dependency_overrides[get_llm_client] = lambda: _FakeLlmClient(
        expressions=_ConditionExpressions()
    )

    response = client.post(ENDPOINT, json={})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("free_text", ["", "   "])
def test_blank_free_text_returns_422(free_text):
    app.dependency_overrides[get_llm_client] = lambda: _FakeLlmClient(
        expressions=_ConditionExpressions()
    )

    response = client.post(ENDPOINT, json={"freeText": free_text})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_llm_failure_returns_common_internal_error_response():
    app.dependency_overrides[get_llm_client] = lambda: _FakeLlmClient(
        error=AppException("LLM 호출에 실패했습니다.", code="INTERNAL_ERROR", status_code=500)
    )

    response = client.post(ENDPOINT, json={"freeText": "서울 사는 취준생"})

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "INTERNAL_ERROR"
    assert body["detail"] is None


def test_expression_not_in_free_text_returns_internal_error():
    fake = _FakeLlmClient(
        expressions=_ConditionExpressions(employment_status_expressions=["자유 계약 근로자"])
    )
    app.dependency_overrides[get_llm_client] = lambda: fake

    response = client.post(ENDPOINT, json={"freeText": "저는 프리랜서예요"})

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
