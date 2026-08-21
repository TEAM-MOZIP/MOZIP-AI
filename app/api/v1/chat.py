from typing import Annotated

from fastapi import APIRouter, Depends

from app.clients.llm_client import LlmClient, get_llm_client
from app.schemas.chat_response import ChatResponseRequest, ChatResponseResponse
from app.services.chat_response_service import generate_chat_response

router = APIRouter()


@router.post("/chat/respond", response_model=ChatResponseResponse)
def chat_respond(
    request: ChatResponseRequest,
    llm_client: Annotated[LlmClient, Depends(get_llm_client)],
) -> ChatResponseResponse:
    return generate_chat_response(request, llm_client)
