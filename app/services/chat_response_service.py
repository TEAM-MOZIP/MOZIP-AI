from app.clients.llm_client import LlmClient
from app.core.config import get_settings
from app.prompts.chat_response import SYSTEM_INSTRUCTION, build_user_content
from app.schemas.chat_response import ChatResponseRequest, ChatResponseResponse


def generate_chat_response(
    request: ChatResponseRequest, llm_client: LlmClient
) -> ChatResponseResponse:
    user_content = build_user_content(request)
    return llm_client.generate_structured(
        SYSTEM_INSTRUCTION,
        user_content,
        ChatResponseResponse,
        timeout_seconds=get_settings().gemini_chat_timeout_seconds,
    )
