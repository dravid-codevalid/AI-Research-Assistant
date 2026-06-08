"""Middleware configuration for the FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings


def setup_middleware(app: FastAPI) -> None:
    """Configure all application middleware.

    Args:
        app: The FastAPI application instance.
    """
    from api.security import RateLimitMiddleware
    
    app.add_middleware(
        RateLimitMiddleware,
        limit_per_minute=120,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
