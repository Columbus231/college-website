import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import admin, applications, auth, public
from app.api.rate_limit import limiter
from app.core.config import settings
from app.core.request_limits import RequestBodyLimitMiddleware
import app.models  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

is_production = settings.environment == "production"
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Versioned college website API",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(RequestBodyLimitMiddleware)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(public.router, prefix=settings.api_prefix)
app.include_router(applications.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
