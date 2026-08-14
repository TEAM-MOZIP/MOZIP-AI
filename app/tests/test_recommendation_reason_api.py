import pytest
from fastapi.testclient import TestClient

from app.clients.llm_client import get_llm_client
from app.core.exceptions import AppException
from app.main import app
from app.schemas.recommendation_reason import RecommendationExplainResponse

ENDPOINT = "/api/v1/recommendations/explain"


class _FakeLlmClient:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error

    def generate_structured(self, system_instruction, user_content, response_schema):
        if self._error is not None:
            raise self._error
        return self._response


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_llm_client, None)


client = TestClient(app)


def _payload(**overrides):
    payload = {
        "policyTitle": "청년내일채움공제",
        "eligibilityStatus": "ELIGIBLE",
        "conditions": [
            {"type": "AGE", "status": "MATCHED", "reason": "만 25세는 조건을 충족합니다"},
            {"type": "INCOME", "status": "NEEDS_REVIEW", "reason": "소득 정보가 없습니다"},
        ],
    }
    payload.update(overrides)
    return payload


def test_returns_200_with_camel_case_response():
    fake = _FakeLlmClient(response=RecommendationExplainResponse(reason="추천 이유 문장"))
    app.dependency_overrides[get_llm_client] = lambda: fake

    response = client.post(ENDPOINT, json=_payload())

    assert response.status_code == 200
    assert response.json() == {"reason": "추천 이유 문장"}


def test_invalid_eligibility_status_enum_returns_422():
    app.dependency_overrides[get_llm_client] = lambda: _FakeLlmClient(
        response=RecommendationExplainResponse(reason="x")
    )

    response = client.post(ENDPOINT, json=_payload(eligibilityStatus="UNKNOWN"))

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_missing_required_field_returns_422():
    app.dependency_overrides[get_llm_client] = lambda: _FakeLlmClient(
        response=RecommendationExplainResponse(reason="x")
    )
    payload = _payload()
    del payload["policyTitle"]

    response = client.post(ENDPOINT, json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_llm_failure_returns_common_internal_error_response():
    app.dependency_overrides[get_llm_client] = lambda: _FakeLlmClient(
        error=AppException("LLM 호출에 실패했습니다.", code="INTERNAL_ERROR", status_code=500)
    )

    response = client.post(ENDPOINT, json=_payload())

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "INTERNAL_ERROR"
    assert body["detail"] is None


def test_empty_conditions_list_is_valid():
    fake = _FakeLlmClient(response=RecommendationExplainResponse(reason="이유"))
    app.dependency_overrides[get_llm_client] = lambda: fake

    response = client.post(ENDPOINT, json=_payload(conditions=[]))

    assert response.status_code == 200
