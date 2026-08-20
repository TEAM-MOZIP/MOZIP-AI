import pytest
from fastapi.testclient import TestClient

from app.clients.llm_client import get_llm_client
from app.core.exceptions import AppException
from app.main import app
from app.schemas.policy_summary import PolicySummaryResponse

ENDPOINT = "/api/v1/summaries/generate"


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
        "title": "국민취업지원제도",
        "description": "취업지원서비스와 소득지원을 결합한 한국형 실업부조 제도입니다.",
        "targetDescription": "만 15세 이상 69세 이하 구직자 중 소득·재산 요건을 충족하는 자",
        "benefitDescription": "구직촉진수당 월 50만원씩 최대 6개월 지급",
    }
    payload.update(overrides)
    return payload


def _fake_response() -> PolicySummaryResponse:
    return PolicySummaryResponse(summary="요약 문단")


def test_returns_200_with_camel_case_response():
    fake = _FakeLlmClient(response=_fake_response())
    app.dependency_overrides[get_llm_client] = lambda: fake

    response = client.post(ENDPOINT, json=_payload())

    assert response.status_code == 200
    assert response.json() == {"summary": "요약 문단"}


def test_missing_title_returns_422():
    app.dependency_overrides[get_llm_client] = lambda: _FakeLlmClient(response=_fake_response())
    payload = _payload()
    del payload["title"]

    response = client.post(ENDPOINT, json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("value", ["", "   "])
def test_blank_title_returns_422(value):
    app.dependency_overrides[get_llm_client] = lambda: _FakeLlmClient(response=_fake_response())

    response = client.post(ENDPOINT, json=_payload(title=value))

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_description_null_with_other_sources_is_valid():
    fake = _FakeLlmClient(response=_fake_response())
    app.dependency_overrides[get_llm_client] = lambda: fake

    response = client.post(ENDPOINT, json=_payload(description=None))

    assert response.status_code == 200


def test_all_sources_none_returns_422():
    app.dependency_overrides[get_llm_client] = lambda: _FakeLlmClient(response=_fake_response())

    response = client.post(
        ENDPOINT,
        json={
            "title": "국민취업지원제도",
            "description": None,
            "targetDescription": None,
            "benefitDescription": None,
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_all_sources_blank_returns_422():
    app.dependency_overrides[get_llm_client] = lambda: _FakeLlmClient(response=_fake_response())

    response = client.post(
        ENDPOINT,
        json={
            "title": "국민취업지원제도",
            "description": "   ",
            "targetDescription": "",
            "benefitDescription": "   ",
        },
    )

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
