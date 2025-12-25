"""
FastAPI Application Factory.
Main application entry point with modular router registration.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from backend.core.config import get_settings
from backend.core.logging import setup_logging
from backend.core.database import init_db, SessionLocal
from backend.core.security import get_password_hash
from backend.core.middleware import add_audit_middleware
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

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


def create_default_admin():
    """
    Create default admin user if not exists.
    Password must be set via INITIAL_ADMIN_PASSWORD environment variable.
    """
    import os

    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.username == "admin").first()
        if not user:
            initial_password = os.getenv("INITIAL_ADMIN_PASSWORD")
            if not initial_password:
                logger.error(
                    "INITIAL_ADMIN_PASSWORD environment variable not set! "
                    "Default admin account will NOT be created. "
                    "Set INITIAL_ADMIN_PASSWORD to create the initial admin user."
                )
                return

            logger.info("Creating default admin user...")
            hashed_pwd = get_password_hash(initial_password)
            perms = {
                "ipam": True,
                "topology": True,
                "scripts": True,
                "settings": True,
                "inventory": True
            }
            admin = models.User(
                username="admin",
                hashed_password=hashed_pwd,
                role="admin",
                permissions=perms
            )
            db.add(admin)
            db.commit()
            logger.info("Default user 'admin' created successfully.")
            logger.warning("IMPORTANT: Change the admin password immediately after first login!")
    except Exception as e:
        logger.error(f"Error creating default admin: {e}")
    finally:
        db.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="NetOps-Flow API",
        description="Enterprise Network Automation Platform",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Audit Logging Middleware for POST/PUT/DELETE actions
    add_audit_middleware(app)

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

    @app.on_event("startup")
    async def startup_event():
        """Application startup tasks."""
        logger.info("Starting NetOps-Flow API...")
        logger.info("NetOps-Flow API started successfully.")
        logger.info("Note: Database initialization is handled by entrypoint.sh")

    @app.get("/health")
    async def health_check():
        """
        Comprehensive health check endpoint.
        Checks FastAPI, Database, Redis, and Celery worker status.
        """
        import redis
        from celery.app.control import Inspect
        from sqlalchemy import text
        from backend.core.database import SessionLocal

        health_status = {
            "status": "healthy",
            "version": "2.0.0",
            "services": {}
        }
        overall_healthy = True

        # Check Database
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            health_status["services"]["database"] = {"status": "healthy"}
        except Exception as e:
            health_status["services"]["database"] = {"status": "unhealthy", "error": str(e)}
            overall_healthy = False

        # Check Redis
        try:
            redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            redis_client.ping()
            health_status["services"]["redis"] = {"status": "healthy"}
        except Exception as e:
            health_status["services"]["redis"] = {"status": "unhealthy", "error": str(e)}
            overall_healthy = False

        # Check Celery Workers
        try:
            from worker.tasks import celery_app
            inspector = Inspect(app=celery_app)
            active_workers = inspector.active()

            if active_workers:
                health_status["services"]["celery"] = {
                    "status": "healthy",
                    "workers": len(active_workers)
                }
            else:
                health_status["services"]["celery"] = {
                    "status": "degraded",
                    "message": "No active workers found"
                }
                overall_healthy = False
        except Exception as e:
            health_status["services"]["celery"] = {"status": "unhealthy", "error": str(e)}
            overall_healthy = False

        health_status["status"] = "healthy" if overall_healthy else "degraded"

        # Return 503 if any critical service is down
        from fastapi.responses import JSONResponse
        status_code = 200 if overall_healthy else 503
        return JSONResponse(content=health_status, status_code=status_code)

    return app


# Create application instance
app = create_app()
