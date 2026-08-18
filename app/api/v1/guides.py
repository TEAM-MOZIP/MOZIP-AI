from typing import Annotated

from fastapi import APIRouter, Depends

from app.clients.llm_client import LlmClient, get_llm_client
from app.schemas.application_guide import ApplicationGuideRequest, ApplicationGuideResponse
from app.services.application_guide_service import generate_application_guide

router = APIRouter()


@router.post("/guides/generate", response_model=ApplicationGuideResponse)
def guides_generate(
    request: ApplicationGuideRequest,
    llm_client: Annotated[LlmClient, Depends(get_llm_client)],
) -> ApplicationGuideResponse:
    return generate_application_guide(request, llm_client)
