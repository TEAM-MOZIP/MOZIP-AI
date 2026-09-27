import pytest
from fastapi.testclient import TestClient

from app.clients.llm_client import get_llm_client
from app.core.exceptions import AppException
from app.main import app
from app.schemas.chat_response import ChatResponseResponse

ENDPOINT = "/api/v1/chat/respond"


class _FakeLlmClient:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error

    def generate_structured(
        self, system_instruction, user_content, response_schema, timeout_seconds=None
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
    payload = {"message": "서울 사는 취준생이 받을 정책 있어?"}
    payload.update(overrides)
    return payload


def _fake_response() -> ChatResponseResponse:
    return ChatResponseResponse(reply="답변입니다.")


def test_returns_200_with_camel_case_response():
    fake = _FakeLlmClient(response=_fake_response())
    app.dependency_overrides[get_llm_client] = lambda: fake

    response = client.post(ENDPOINT, json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "답변입니다."
    assert body["responseType"] == "GENERAL"
    # 블록이 없으면 reply를 텍스트 블록으로 내려준다
    assert [block["type"] for block in body["blocks"]] == ["TEXT"]
    assert body["blocks"][0]["text"] == "답변입니다."
    assert body["followUps"] == []


def test_grounding_payload_is_accepted():
    fake = _FakeLlmClient(response=_fake_response())
    app.dependency_overrides[get_llm_client] = lambda: fake

    response = client.post(
        ENDPOINT,
        json=_payload(
            groundingPolicies=[
                {
                    "policyId": 1,
                    "title": "국민취업지원제도",
                    "eligibilityStatus": "ELIGIBLE",
                    "applicationEndDate": "2026-12-31",
                }
            ],
            policyDetail={
                "title": "국민취업지원제도",
                "summary": "요약",
                "eligibility": "자격 요건",
                "applicationPeriod": "상시",
                "organization": "고용노동부",
            },
            unresolvedConditions=[{"axis": "employment_status", "rawText": "프리랜서"}],
        ),
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "답변입니다."


def test_history_payload_is_accepted():
    fake = _FakeLlmClient(response=_fake_response())
    app.dependency_overrides[get_llm_client] = lambda: fake

    response = client.post(
        ENDPOINT,
        json=_payload(
            message="그거 신청 기간은?",
            history=[
                {
                    "message": "국민취업지원제도 알려줘",
                    "reply": "국민취업지원제도는 구직자를 지원하는 제도입니다.",
                }
            ],
        ),
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "답변입니다."


def test_request_without_history_still_returns_200():
    fake = _FakeLlmClient(response=_fake_response())
    app.dependency_overrides[get_llm_client] = lambda: fake

    response = client.post(ENDPOINT, json=_payload())

    assert response.status_code == 200
    assert response.json()["reply"] == "답변입니다."


def test_missing_message_returns_422():
    app.dependency_overrides[get_llm_client] = lambda: _FakeLlmClient(response=_fake_response())
    payload = _payload()
    del payload["message"]

    response = client.post(ENDPOINT, json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("message", ["", "   "])
def test_blank_message_returns_422(message):
    app.dependency_overrides[get_llm_client] = lambda: _FakeLlmClient(response=_fake_response())

    response = client.post(ENDPOINT, json=_payload(message=message))

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
