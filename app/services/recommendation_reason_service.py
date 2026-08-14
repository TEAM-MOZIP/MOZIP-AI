from app.clients.llm_client import LlmClient
from app.prompts.recommendation_reason import SYSTEM_INSTRUCTION, build_user_content
from app.schemas.recommendation_reason import (
    RecommendationExplainRequest,
    RecommendationExplainResponse,
)


def generate_recommendation_explanation(
    request: RecommendationExplainRequest, llm_client: LlmClient
) -> RecommendationExplainResponse:
    user_content = build_user_content(
        request.policy_title, request.eligibility_status, request.conditions
    )
    return llm_client.generate_structured(
        SYSTEM_INSTRUCTION, user_content, RecommendationExplainResponse
    )
