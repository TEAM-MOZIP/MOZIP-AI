from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.clients.llm_client import get_llm_client
from app.core.exceptions import register_exception_handlers
from app.core.logging import RequestLoggingMiddleware, configure_logging

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    if get_llm_client.cache_info().currsize > 0:
        get_llm_client().close()


app = FastAPI(title="MOZIP-AI", lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)
register_exception_handlers(app)
app.include_router(v1_router, prefix="/api/v1")
