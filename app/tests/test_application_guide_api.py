import pytest
from fastapi.testclient import TestClient

from app.clients.llm_client import get_llm_client
from app.core.exceptions import AppException
from app.main import app
from app.schemas.application_guide import ApplicationGuideResponse, ApplicationGuideStep

ENDPOINT = "/api/v1/guides/generate"


class _FakeLlmClient:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error

    def generate_structured(
        self,
        system_instruction,
        user_content,
        response_schema,
        timeout_seconds=None,
        thinking_level=None,
    ):
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
        "applicationInstructions": "고용센터 방문하거나 온라인으로 신청합니다.",
        "requiredDocumentsSource": "취업지원신청서",
    }
    payload.update(overrides)
    return payload


def _fake_response() -> ApplicationGuideResponse:
    return ApplicationGuideResponse(
        steps=[
            ApplicationGuideStep(
                order=1, title="신청", description="고용센터를 방문하거나 온라인으로 신청합니다."
            )
        ],
        required_documents=["취업지원신청서"],
    )


def test_returns_200_with_camel_case_response():
    fake = _FakeLlmClient(response=_fake_response())
    app.dependency_overrides[get_llm_client] = lambda: fake

    response = client.post(ENDPOINT, json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["steps"] == [
        {
            "order": 1,
            "title": "신청",
            "description": "고용센터를 방문하거나 온라인으로 신청합니다.",
        }
    ]
    assert body["requiredDocuments"] == ["취업지원신청서"]
    assert "notes" not in body


def test_missing_application_instructions_returns_422():
    app.dependency_overrides[get_llm_client] = lambda: _FakeLlmClient(response=_fake_response())
    payload = _payload()
    del payload["applicationInstructions"]

    response = client.post(ENDPOINT, json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("value", ["", "   "])
def test_blank_application_instructions_returns_422(value):
    app.dependency_overrides[get_llm_client] = lambda: _FakeLlmClient(response=_fake_response())

    response = client.post(ENDPOINT, json=_payload(applicationInstructions=value))

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_optional_required_documents_source_omitted_is_valid():
    fake = _FakeLlmClient(response=_fake_response())
    app.dependency_overrides[get_llm_client] = lambda: fake

    response = client.post(ENDPOINT, json={"applicationInstructions": "K-Startup 온라인 신청"})

    assert response.status_code == 200


def test_llm_failure_returns_common_internal_error_response():
    app.dependency_overrides[get_llm_client] = lambda: _FakeLlmClient(
        error=AppException("LLM 호출에 실패했습니다.", code="INTERNAL_ERROR", status_code=500)
    )

    response = client.post(ENDPOINT, json=_payload())

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "INTERNAL_ERROR"
    assert body["detail"] is None
