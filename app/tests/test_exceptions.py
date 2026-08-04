import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.exceptions import AppException, register_exception_handlers
from app.core.logging import RequestLoggingMiddleware


class _Payload(BaseModel):
    name: str


class _SensitivePayload(BaseModel):
    api_key: int  # wrong type on purpose so a secret-looking value fails validation


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)

    @app.get("/app-exception")
    def raise_app_exception():
        raise AppException("정책을 찾을 수 없습니다.", code="POLICY_NOT_FOUND", status_code=404)

    @app.post("/validate")
    def validate(payload: _Payload):
        return payload

    @app.post("/validate-sensitive")
    def validate_sensitive(payload: _SensitivePayload):
        return payload

    @app.get("/boom")
    def boom():
        raise ValueError("internal secret detail")

    return app


client = TestClient(_build_test_app(), raise_server_exceptions=False)


def test_app_exception_returns_common_format():
    response = client.get("/app-exception")

    assert response.status_code == 404
    assert response.json() == {
        "code": "POLICY_NOT_FOUND",
        "message": "정책을 찾을 수 없습니다.",
        "detail": None,
    }


def test_validation_error_returns_422_with_detail():
    response = client.post("/validate", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["detail"]


def test_validation_error_detail_excludes_raw_input_and_context():
    secret_value = "sk-super-secret-value-123"

    response = client.post("/validate-sensitive", json={"api_key": secret_value})

    assert response.status_code == 422
    body = response.json()
    for error in body["detail"]:
        assert set(error.keys()) == {"loc", "msg", "type"}
    assert secret_value not in response.text


def test_method_not_allowed_preserves_allow_header():
    response = client.post("/app-exception")

    assert response.status_code == 405
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"
    assert "GET" in response.headers["Allow"]


def test_unhandled_exception_returns_generic_500_without_internal_detail():
    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {
        "code": "INTERNAL_ERROR",
        "message": "예상하지 못한 오류가 발생했습니다.",
        "detail": None,
    }
    assert "internal secret detail" not in response.text


def test_unhandled_exception_still_gets_request_id_and_is_logged_once(caplog):
    with caplog.at_level(logging.INFO, logger="mozip_ai.request"):
        response = client.get("/boom", headers={"X-Request-ID": "boom-request-id"})

    assert response.headers["X-Request-ID"] == "boom-request-id"

    records = [r for r in caplog.records if r.name == "mozip_ai.request"]
    assert len(records) == 1

    record = records[0]
    assert record.request_id == "boom-request-id"
    assert record.status_code == 500
    assert record.success is False
