from app.clients.llm_client import LlmClient
from app.core.config import get_settings
from app.prompts.policy_summary import SYSTEM_INSTRUCTION, build_user_content
from app.schemas.policy_summary import PolicySummaryRequest, PolicySummaryResponse


def generate_policy_summary(
    request: PolicySummaryRequest, llm_client: LlmClient
) -> PolicySummaryResponse:
    user_content = build_user_content(
        request.title,
        request.description,
        request.target_description,
        request.benefit_description,
    )
    return llm_client.generate_structured(
        SYSTEM_INSTRUCTION,
        user_content,
        PolicySummaryResponse,
        timeout_seconds=get_settings().gemini_summary_timeout_seconds,
        thinking_level=get_settings().gemini_fast_thinking_level,
    )
