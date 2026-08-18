from app.clients.llm_client import LlmClient
from app.prompts.application_guide import SYSTEM_INSTRUCTION, build_user_content
from app.schemas.application_guide import ApplicationGuideRequest, ApplicationGuideResponse


def generate_application_guide(
    request: ApplicationGuideRequest, llm_client: LlmClient
) -> ApplicationGuideResponse:
    user_content = build_user_content(
        request.application_instructions,
        request.required_documents_source,
    )
    return llm_client.generate_structured(
        SYSTEM_INSTRUCTION, user_content, ApplicationGuideResponse
    )
