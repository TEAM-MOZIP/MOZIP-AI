from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.core.exceptions import register_exception_handlers
from app.core.logging import RequestLoggingMiddleware, configure_logging

configure_logging()

app = FastAPI(title="MOZIP-AI")
app.add_middleware(RequestLoggingMiddleware)
register_exception_handlers(app)
app.include_router(v1_router, prefix="/api/v1")
