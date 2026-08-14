from typing import Annotated

from fastapi import APIRouter, Depends

from app.clients.llm_client import LlmClient, get_llm_client
from app.schemas.recommendation_reason import (
    RecommendationExplainRequest,
    RecommendationExplainResponse,
)
from app.services.recommendation_reason_service import generate_recommendation_explanation

router = APIRouter()


@router.post("/recommendations/explain", response_model=RecommendationExplainResponse)
def recommendations_explain(
    request: RecommendationExplainRequest,
    llm_client: Annotated[LlmClient, Depends(get_llm_client)],
) -> RecommendationExplainResponse:
    return generate_recommendation_explanation(request, llm_client)
