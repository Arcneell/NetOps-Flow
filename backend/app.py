"""
FastAPI Application Factory.
Main application entry point with modular router registration.
Uses modern lifespan context manager for lifecycle management.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import redis
import secrets
from sqlalchemy import text

from backend.core.config import get_settings
from backend.core.logging import setup_logging
from backend.core.database import init_db, SessionLocal
from backend.core.security import get_current_superadmin_user
from backend.core.middleware import add_audit_middleware
from backend.core import setup as setup_services
from backend import models
from backend.routers import (
    auth_router,
    users_router,
    ipam_router,
    topology_router,
    scripts_router,
    inventory_router,
    dashboard_router,
    dcim_router,
    contracts_router,
    software_router,
    network_ports_router,
    attachments_router,
    entities_router,
)
from backend.routers.audit import router as audit_router
from backend.routers.scripts import executions_router
from backend.routers.tickets import router as tickets_router
from backend.routers.notifications import router as notifications_router
from backend.routers.knowledge import router as knowledge_router
from backend.routers.export import router as export_router
from backend.routers.search import router as search_router
from backend.routers.webhooks import router as webhooks_router
from backend.routers.settings import router as settings_router

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


# ==================== LIFESPAN CONTEXT MANAGER ====================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Modern lifespan context manager for FastAPI.
    Handles startup and shutdown events with proper resource management.
    """
    # ===== STARTUP =====
    logger.info("Starting Inframate API...")

    # Initialize Redis client and Celery reference for health checks
    app.state.redis_client = setup_services.init_redis_client()
    app.state.celery_app = setup_services.get_celery_app()

    # ===== CONNECTION WARMUP =====
    # Warm up database connection pool to avoid cold start latency
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        logger.info("Database connection pool warmed up")
    except Exception as e:
        logger.error(f"Database warmup failed: {e}")
        # Don't fail startup - the health check will detect this

    # Warm up Redis connection
    try:
        if app.state.redis_client:
            app.state.redis_client.ping()
            logger.info("Redis connection warmed up")
    except Exception as e:
        logger.error(f"Redis warmup failed: {e}")
        # Don't fail startup - the health check will detect this

    logger.info("Inframate API started successfully.")

    # Create default admin user if not exists (idempotent)
    try:
        await setup_services.create_default_admin_async()
    except Exception as e:
        logger.warning(f"Could not create default admin: {e}")

    yield  # Application runs here

    # ===== SHUTDOWN =====
    logger.info("Shutting down Inframate API...")

    # Close Redis connection
    if hasattr(app.state, 'redis_client') and app.state.redis_client:
        try:
            app.state.redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.warning(f"Error closing Redis connection: {e}")

    logger.info("Inframate API shutdown complete.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Inframate API",
        description="Enterprise Network Automation Platform",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan  # Modern lifecycle management
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
        expose_headers=["X-CSRF-Token"],
    )

    # Audit Logging Middleware for POST/PUT/DELETE actions
    add_audit_middleware(app)

    # Global Exception Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        import traceback
        error_id = secrets.token_hex(4)
        logger.error(f"Global error {error_id}: {exc}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal Server Error",
                "error_id": error_id,
                "message": str(exc) if settings.debug else "An unexpected error occurred."
            }
        )

    # Register routers with API prefix
    api_prefix = "/api/v1"

    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(users_router, prefix=api_prefix)
    app.include_router(ipam_router, prefix=api_prefix)
    app.include_router(topology_router, prefix=api_prefix)
    app.include_router(scripts_router, prefix=api_prefix)
    app.include_router(executions_router, prefix=api_prefix)
    app.include_router(inventory_router, prefix=api_prefix)
    app.include_router(dashboard_router, prefix=api_prefix)
    app.include_router(dcim_router, prefix=api_prefix)
    app.include_router(contracts_router, prefix=api_prefix)
    app.include_router(software_router, prefix=api_prefix)
    app.include_router(network_ports_router, prefix=api_prefix)
    app.include_router(attachments_router, prefix=api_prefix)
    app.include_router(entities_router, prefix=api_prefix)
    app.include_router(audit_router, prefix=api_prefix)
    app.include_router(tickets_router, prefix=api_prefix)
    app.include_router(notifications_router, prefix=api_prefix)
    app.include_router(knowledge_router, prefix=api_prefix)
    app.include_router(export_router, prefix=api_prefix)
    app.include_router(search_router, prefix=api_prefix)
    app.include_router(webhooks_router, prefix=api_prefix)
    app.include_router(settings_router, prefix=api_prefix)

    @app.get("/health")
    async def health_check():
        """
        Public health check endpoint for orchestrators (Kubernetes, Docker, ALB).
        Returns basic status without requiring authentication.
        """
        health_status = {
            "status": "healthy",
            "version": "2.0.0"
        }
        overall_healthy = True

        # Check Database (critical)
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
        except Exception:
            overall_healthy = False

        # Check Redis (critical)
        try:
            redis_client = getattr(app.state, 'redis_client', None)
            if redis_client:
                redis_client.ping()
            else:
                redis_client = redis.from_url(settings.redis_url, decode_responses=True)
                redis_client.ping()
        except Exception:
            overall_healthy = False

        health_status["status"] = "healthy" if overall_healthy else "unhealthy"
        status_code = 200 if overall_healthy else 503
        return JSONResponse(content=health_status, status_code=status_code)

    @app.get("/health/detailed")
    async def health_check_detailed(
        current_user: models.User = Depends(get_current_superadmin_user)
    ):
        """
        Detailed health check endpoint (superadmin only).
        Shows comprehensive status of all services with error details.
        """
        health_status = {
            "status": "healthy",
            "version": "2.0.0",
            "services": {}
        }
        overall_healthy = True

        # Check Database
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
            health_status["services"]["database"] = {"status": "healthy"}
        except Exception as e:
            health_status["services"]["database"] = {"status": "unhealthy", "error": str(e)}
            overall_healthy = False

        # Check Redis (use pre-initialized client from app.state)
        try:
            redis_client = getattr(app.state, 'redis_client', None)
            if redis_client:
                redis_client.ping()
                health_status["services"]["redis"] = {"status": "healthy"}
            else:
                # Fallback: try to connect
                redis_client = redis.from_url(settings.redis_url, decode_responses=True)
                redis_client.ping()
                health_status["services"]["redis"] = {"status": "healthy"}
        except Exception as e:
            health_status["services"]["redis"] = {"status": "unhealthy", "error": str(e)}
            overall_healthy = False

        # Check Celery Workers via Redis heartbeat
        try:
            redis_client = getattr(app.state, 'redis_client', None)
            heartbeat_ts: Optional[str] = None
            if redis_client:
                heartbeat_ts = redis_client.get("celery:heartbeat")

            if heartbeat_ts:
                import time
                age = time.time() - float(heartbeat_ts)
                if age <= 90:
                    health_status["services"]["celery"] = {
                        "status": "healthy",
                        "age_seconds": int(age)
                    }
                else:
                    health_status["services"]["celery"] = {
                        "status": "warning",
                        "message": "Worker heartbeat stale",
                        "age_seconds": int(age)
                    }
            else:
                health_status["services"]["celery"] = {
                    "status": "warning",
                    "message": "No heartbeat detected"
                }
        except Exception as e:
            health_status["services"]["celery"] = {"status": "unhealthy", "error": str(e)}
            overall_healthy = False

        health_status["status"] = "healthy" if overall_healthy else "degraded"

        # Return 503 if any critical service is down
        status_code = 200 if overall_healthy else 503
        return JSONResponse(content=health_status, status_code=status_code)

    return app


# Create application instance
app = create_app()
