"""
Retail Intelligence API — Application Factory.

Wires together middleware, routers, and lifecycle events into a single
FastAPI application instance. Run with:

    cd api && uvicorn app.main:app --reload
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings, setup_logging
from app.routers import analytics, sales

settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

# ── Application Instance ─────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    description=(
        "Enterprise REST API powering the Retail Intelligence "
        "Business Analytics platform.  Backed by a Databricks "
        "Gold-layer Star Schema."
    ),
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Router Registration ──────────────────────────────────────────────

app.include_router(sales.router)
app.include_router(analytics.router)

# ── System Endpoints ─────────────────────────────────────────────────


@app.get("/health", tags=["System"], summary="Health Check")
async def health_check():
    """Liveness probe for load balancers and monitoring."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@app.on_event("startup")
async def on_startup():
    logger.info(
        "%s v%s is starting …", settings.app_name, settings.app_version
    )


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Shutting down %s …", settings.app_name)
