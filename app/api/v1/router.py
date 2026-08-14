from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.recommendations import router as recommendations_router
from app.api.v1.semantic_match import router as semantic_match_router

router = APIRouter()
router.include_router(health_router)
router.include_router(semantic_match_router)
router.include_router(recommendations_router)
