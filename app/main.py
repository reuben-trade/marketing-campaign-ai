"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ads, competitors, recommendations, strategy
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    yield
    # Shutdown


settings = get_settings()

app = FastAPI(
    title="Marketing AI",
    description="AI-Powered Competitor Ad Analysis & Content Recommendation System",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(strategy.router, prefix="/api/strategy", tags=["Strategy"])
app.include_router(competitors.router, prefix="/api/competitors", tags=["Competitors"])
app.include_router(ads.router, prefix="/api/ads", tags=["Ads"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["Recommendations"])


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Marketing AI API",
        "docs": "/docs",
        "health": "/health",
    }
