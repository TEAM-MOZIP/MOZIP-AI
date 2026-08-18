import pytest
from fastapi.testclient import TestClient

from app.clients.llm_client import get_llm_client
from app.core.exceptions import AppException
from app.main import app
from app.schemas.term_explanation import TermExplainResponse

ENDPOINT = "/api/v1/terms/explain"


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
        "term": "기준 중위소득 120%",
        "context": "본 사업은 기준 중위소득 120% 이하의 청년을 대상으로 합니다.",
    }
    payload.update(overrides)
    return payload


def test_returns_200_with_explanation():
    fake = _FakeLlmClient(response=TermExplainResponse(explanation="설명 문장"))
    app.dependency_overrides[get_llm_client] = lambda: fake

    response = client.post(ENDPOINT, json=_payload())

    assert response.status_code == 200
    assert response.json() == {"explanation": "설명 문장"}


def test_missing_term_returns_422():
    app.dependency_overrides[get_llm_client] = lambda: _FakeLlmClient(
        response=TermExplainResponse(explanation="x")
    )
    payload = _payload()
    del payload["term"]

    response = client.post(ENDPOINT, json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_missing_context_returns_422():
    app.dependency_overrides[get_llm_client] = lambda: _FakeLlmClient(
        response=TermExplainResponse(explanation="x")
    )
    payload = _payload()
    del payload["context"]

    response = client.post(ENDPOINT, json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("term", ["", "   "])
def test_blank_term_returns_422(term):
    app.dependency_overrides[get_llm_client] = lambda: _FakeLlmClient(
        response=TermExplainResponse(explanation="x")
    )

    response = client.post(ENDPOINT, json=_payload(term=term))

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("context", ["", "   "])
def test_blank_context_returns_422(context):
    app.dependency_overrides[get_llm_client] = lambda: _FakeLlmClient(
        response=TermExplainResponse(explanation="x")
    )

    response = client.post(ENDPOINT, json=_payload(context=context))

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
