import sys

sys.path.insert(0, ".")

from contextlib import asynccontextmanager
from datetime import datetime

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.cache import init_cache
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.database import init_database
from app.websocket.websocket_manager import websocket_endpoint

# Initialize logger
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    setup_logging()
    logger.info("Starting PaperTrail API", version=settings.VERSION)

    # Initialize cache
    await init_cache()

    await init_database()

    logger.info("PaperTrail API startup complete")

    yield

    # Shutdown
    logger.info("Shutting down PaperTrail API")


app = FastAPI(
    title="PaperTrail API",
    description="GraphRAG + Multi-Agent System for research synthesis",
    version=settings.VERSION,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# WebSocket endpoint
app.add_api_websocket_route("/ws", websocket_endpoint)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "PaperTrail API",
        "version": settings.VERSION,
        "docs": "/docs" if settings.ENVIRONMENT != "production" else None,
        "redoc": "/redoc" if settings.ENVIRONMENT != "production" else None,
    }


@app.get("/health/detailed")
async def detailed_health():
    """Detailed health check including service status"""
    from app.database import HYDRADB_CONNECTED

    health_status = {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "services": {
            "hydradb": "connected" if HYDRADB_CONNECTED else "disconnected",
            "redis": "connected",  # Simplified - would need actual check
        },
        "timestamp": datetime.utcnow().isoformat(),
    }

    if health_status["services"]["hydradb"] != "connected":
        health_status["status"] = "degraded"

    return health_status


# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Global HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global exception handler"""
    logger.error("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
        },
    )
