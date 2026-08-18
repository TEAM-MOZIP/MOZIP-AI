from app.clients.llm_client import LlmClient
from app.prompts.term_explanation import SYSTEM_INSTRUCTION, build_user_content
from app.schemas.term_explanation import TermExplainRequest, TermExplainResponse


def generate_term_explanation(
    request: TermExplainRequest, llm_client: LlmClient
) -> TermExplainResponse:
    user_content = build_user_content(request.term, request.context)
    return llm_client.generate_structured(SYSTEM_INSTRUCTION, user_content, TermExplainResponse)
