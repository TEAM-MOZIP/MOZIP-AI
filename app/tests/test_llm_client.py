import pytest
from pydantic import BaseModel

import app.clients.llm_client as llm_client_module
from app.clients.llm_client import LlmClient, get_llm_client
from app.core.config import Settings
from app.core.exceptions import AppException


class _SampleSchema(BaseModel):
    value: str


class _FakeInteraction:
    def __init__(self, output_text: str | None) -> None:
        self.output_text = output_text


class _FakeInteractionsResource:
    def __init__(self, output_text: str | None = None, error: Exception | None = None) -> None:
        self._output_text = output_text
        self._error = error
        self.last_call_kwargs: dict | None = None

    def create(self, **kwargs):
        self.last_call_kwargs = kwargs
        if self._error is not None:
            raise self._error
        return _FakeInteraction(self._output_text)


class _FakeGenaiClient:
    def __init__(self, interactions: _FakeInteractionsResource) -> None:
        self.interactions = interactions
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _build_client(interactions: _FakeInteractionsResource) -> LlmClient:
    fake_client = _FakeGenaiClient(interactions)
    return LlmClient(fake_client, model="gemini-3.5-flash-lite", timeout_seconds=2.5)


def test_generate_structured_returns_validated_model():
    interactions = _FakeInteractionsResource(output_text='{"value": "hello"}')
    client = _build_client(interactions)

    result = client.generate_structured("system", "user", _SampleSchema)

    assert result == _SampleSchema(value="hello")


def test_generate_structured_passes_store_false_and_schema():
    interactions = _FakeInteractionsResource(output_text='{"value": "hello"}')
    client = _build_client(interactions)

    client.generate_structured("system-instruction", "user-content", _SampleSchema)

    kwargs = interactions.last_call_kwargs
    assert kwargs["store"] is False
    assert kwargs["system_instruction"] == "system-instruction"
    assert kwargs["input"] == "user-content"
    # top-level response_mime_type을 response_format과 함께 보내면 실제 Gemini API가
    # 400을 반환함을 실측 확인했다 — 절대 다시 추가하지 않는다.
    assert "response_mime_type" not in kwargs
    assert kwargs["response_format"]["type"] == "text"
    assert kwargs["response_format"]["mime_type"] == "application/json"
    assert kwargs["response_format"]["schema"] == _SampleSchema.model_json_schema()


def test_generate_structured_raises_app_exception_on_sdk_error():
    interactions = _FakeInteractionsResource(error=RuntimeError("provider unavailable"))
    client = _build_client(interactions)

    with pytest.raises(AppException) as exc_info:
        client.generate_structured("system", "user", _SampleSchema)

    assert exc_info.value.code == "INTERNAL_ERROR"
    assert exc_info.value.status_code == 500


def test_generate_structured_raises_app_exception_on_missing_output_text():
    interactions = _FakeInteractionsResource(output_text=None)
    client = _build_client(interactions)

    with pytest.raises(AppException) as exc_info:
        client.generate_structured("system", "user", _SampleSchema)

    assert exc_info.value.code == "INTERNAL_ERROR"


def test_generate_structured_raises_app_exception_on_malformed_json():
    interactions = _FakeInteractionsResource(output_text="not json")
    client = _build_client(interactions)

    with pytest.raises(AppException) as exc_info:
        client.generate_structured("system", "user", _SampleSchema)

    assert exc_info.value.code == "INTERNAL_ERROR"


def test_generate_structured_raises_app_exception_when_schema_fields_missing():
    interactions = _FakeInteractionsResource(output_text="{}")
    client = _build_client(interactions)

    with pytest.raises(AppException) as exc_info:
        client.generate_structured("system", "user", _SampleSchema)

    assert exc_info.value.code == "INTERNAL_ERROR"


def test_close_delegates_to_underlying_client():
    interactions = _FakeInteractionsResource(output_text='{"value": "x"}')
    fake_client = _FakeGenaiClient(interactions)
    client = LlmClient(fake_client, model="gemini-3.5-flash-lite", timeout_seconds=2.5)

    client.close()

    assert fake_client.closed is True


def test_get_llm_client_raises_when_api_key_missing(monkeypatch):
    get_llm_client.cache_clear()
    monkeypatch.setattr(
        llm_client_module,
        "get_settings",
        lambda: Settings(_env_file=None, gemini_api_key=None),
    )

    try:
        with pytest.raises(AppException) as exc_info:
            get_llm_client()
        assert exc_info.value.code == "LLM_NOT_CONFIGURED"
    finally:
        get_llm_client.cache_clear()


def test_get_llm_client_constructs_client_when_api_key_present(monkeypatch):
    get_llm_client.cache_clear()
    monkeypatch.setattr(
        llm_client_module,
        "get_settings",
        lambda: Settings(_env_file=None, gemini_api_key="dummy-key"),
    )

    try:
        client = get_llm_client()
        assert isinstance(client, LlmClient)
    finally:
        get_llm_client.cache_clear()


def test_generate_structured_uses_default_timeout():
    interactions = _FakeInteractionsResource(output_text='{"value": "hello"}')
    client = _build_client(interactions)

    client.generate_structured("system", "user", _SampleSchema)

    assert interactions.last_call_kwargs["timeout"] == 2.5


def test_generate_structured_overrides_timeout_when_given():
    interactions = _FakeInteractionsResource(output_text='{"value": "hello"}')
    client = _build_client(interactions)

    client.generate_structured("system", "user", _SampleSchema, timeout_seconds=15.0)

    assert interactions.last_call_kwargs["timeout"] == 15.0
