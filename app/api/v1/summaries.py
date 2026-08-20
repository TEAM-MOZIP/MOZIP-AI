from typing import Annotated

from fastapi import APIRouter, Depends

from app.clients.llm_client import LlmClient, get_llm_client
from app.schemas.policy_summary import PolicySummaryRequest, PolicySummaryResponse
from app.services.policy_summary_service import generate_policy_summary

router = APIRouter()


@router.post("/summaries/generate", response_model=PolicySummaryResponse)
def summaries_generate(
    request: PolicySummaryRequest,
    llm_client: Annotated[LlmClient, Depends(get_llm_client)],
) -> PolicySummaryResponse:
    return generate_policy_summary(request, llm_client)
