from fastapi import APIRouter

from app.api.v1.guides import router as guides_router
from app.api.v1.health import router as health_router
from app.api.v1.recommendations import router as recommendations_router
from app.api.v1.semantic_match import router as semantic_match_router
from app.api.v1.summaries import router as summaries_router
from app.api.v1.terms import router as terms_router

router = APIRouter()
router.include_router(health_router)
router.include_router(semantic_match_router)
router.include_router(recommendations_router)
router.include_router(terms_router)
router.include_router(guides_router)
router.include_router(summaries_router)
