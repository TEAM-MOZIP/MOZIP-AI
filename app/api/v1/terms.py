from typing import Annotated

from fastapi import APIRouter, Depends

from app.clients.llm_client import LlmClient, get_llm_client
from app.schemas.term_explanation import TermExplainRequest, TermExplainResponse
from app.services.term_explanation_service import generate_term_explanation

router = APIRouter()


@router.post("/terms/explain", response_model=TermExplainResponse)
def terms_explain(
    request: TermExplainRequest,
    llm_client: Annotated[LlmClient, Depends(get_llm_client)],
) -> TermExplainResponse:
    return generate_term_explanation(request, llm_client)
