from typing import Annotated

from fastapi import APIRouter, Depends
from rdflib import Graph

from app.clients.llm_client import LlmClient, get_llm_client
from app.ontology.loader import get_ontology_graph
from app.schemas.condition_extraction import (
    ConditionExtractionRequest,
    ConditionExtractionResponse,
)
from app.services.condition_extraction_service import extract_conditions

router = APIRouter()


@router.post("/conditions/extract", response_model=ConditionExtractionResponse)
def conditions_extract(
    request: ConditionExtractionRequest,
    llm_client: Annotated[LlmClient, Depends(get_llm_client)],
    graph: Annotated[Graph, Depends(get_ontology_graph)],
) -> ConditionExtractionResponse:
    return extract_conditions(request, llm_client, graph)
