from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from rdflib import Graph

from app.ontology.loader import get_ontology_graph
from app.schemas.semantic_match_api import SemanticMatchBatchRequest, SemanticMatchBatchResponse
from app.services.semantic_match_service import calculate_semantic_match_batch

router = APIRouter()


@router.post("/semantic-match/batch", response_model=SemanticMatchBatchResponse)
def semantic_match_batch(
    request: SemanticMatchBatchRequest,
    graph: Annotated[Graph, Depends(get_ontology_graph)],
) -> SemanticMatchBatchResponse:
    results = calculate_semantic_match_batch(request.user, request.policies, graph, date.today())
    return SemanticMatchBatchResponse(results=results)
