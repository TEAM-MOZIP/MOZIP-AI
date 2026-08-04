import logging

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_response_includes_generated_request_id_when_absent():
    response = client.get("/api/v1/health")

    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"]


def test_reuses_client_provided_request_id():
    response = client.get("/api/v1/health", headers={"X-Request-ID": "client-provided-id"})

    assert response.headers["X-Request-ID"] == "client-provided-id"


def test_generated_request_ids_differ_between_requests():
    first = client.get("/api/v1/health")
    second = client.get("/api/v1/health")

    assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]


def test_request_completion_is_logged_with_structured_fields(caplog):
    with caplog.at_level(logging.INFO, logger="mozip_ai.request"):
        client.get("/api/v1/health", headers={"X-Request-ID": "log-test-id"})

    records = [r for r in caplog.records if r.name == "mozip_ai.request"]
    assert len(records) == 1

    record = records[0]
    assert record.request_id == "log-test-id"
    assert record.method == "GET"
    assert record.path == "/api/v1/health"
    assert record.status_code == 200
    assert record.success is True
    assert isinstance(record.duration_ms, float)
