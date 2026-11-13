from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.errors import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)
from app.api.v1.router import api_router

setup_logging()

app = FastAPI(
    title="Mahadev Jyotish AI Backend",
    description="Secure Production Backend API for Mahadev Jyotish AI",
    version="1.0.0",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers for canonical error formatting
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Top-level health endpoints (for loadbalancer / health checkers)
from app.api.v1.endpoints.health import router as health_router
app.include_router(health_router, tags=["Health"])

# Include v1 API router
app.include_router(api_router, prefix=settings.api_v1_prefix)
