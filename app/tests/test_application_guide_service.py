from app.schemas.application_guide import (
    ApplicationGuideRequest,
    ApplicationGuideResponse,
    ApplicationGuideStep,
)
from app.services.application_guide_service import generate_application_guide


class _FakeLlmClient:
    def __init__(self, response: ApplicationGuideResponse) -> None:
        self._response = response
        self.last_system_instruction: str | None = None
        self.last_user_content: str | None = None
        self.last_response_schema: type | None = None

    def generate_structured(self, system_instruction, user_content, response_schema):
        self.last_system_instruction = system_instruction
        self.last_user_content = user_content
        self.last_response_schema = response_schema
        return self._response


def _build_response() -> ApplicationGuideResponse:
    return ApplicationGuideResponse(
        steps=[ApplicationGuideStep(order=1, title="신청", description="온라인으로 신청합니다.")],
        required_documents=["신청서"],
    )


def test_generate_application_guide_returns_llm_result():
    expected = _build_response()
    fake_client = _FakeLlmClient(expected)
    request = ApplicationGuideRequest(
        application_instructions="고용센터 방문하거나 온라인으로 신청합니다.",
        required_documents_source="취업지원신청서",
    )

    result = generate_application_guide(request, fake_client)

    assert result == expected


def test_generate_application_guide_uses_application_guide_response_schema():
    fake_client = _FakeLlmClient(_build_response())
    request = ApplicationGuideRequest(
        application_instructions="온라인으로 신청합니다.",
    )

    generate_application_guide(request, fake_client)

    assert fake_client.last_response_schema is ApplicationGuideResponse


def test_generate_application_guide_includes_sources_when_present():
    fake_client = _FakeLlmClient(_build_response())
    request = ApplicationGuideRequest(
        application_instructions="고용센터 방문하거나 온라인으로 신청합니다.",
        required_documents_source="취업지원신청서, 위임장(대리인 신청 시)",
    )

    generate_application_guide(request, fake_client)

    assert "고용센터 방문하거나 온라인으로 신청합니다." in fake_client.last_user_content
    assert "취업지원신청서, 위임장(대리인 신청 시)" in fake_client.last_user_content


def test_generate_application_guide_omits_missing_optional_source():
    fake_client = _FakeLlmClient(_build_response())
    request = ApplicationGuideRequest(
        application_instructions="K-Startup 온라인 신청",
        required_documents_source=None,
    )

    generate_application_guide(request, fake_client)

    assert "필요 서류 원문" not in fake_client.last_user_content
