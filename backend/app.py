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
from backend import models
from backend.routers import (
    auth_router,
    users_router,
    ipam_router,
    topology_router,
    scripts_router,
    inventory_router,
    dashboard_router,
)
from backend.routers.scripts import executions_router

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


def create_default_admin():
    """Create default admin user if not exists."""
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.username == "admin").first()
        if not user:
            logger.info("Creating default admin user...")
            hashed_pwd = get_password_hash("admin")
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
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
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

    # Legacy routes (for backwards compatibility)
    # These can be removed after frontend migration
    app.include_router(auth_router, prefix="", tags=["Legacy Auth"])
    app.include_router(users_router, prefix="", tags=["Legacy Users"])
    app.include_router(ipam_router, prefix="", tags=["Legacy IPAM"])
    app.include_router(topology_router, prefix="", tags=["Legacy Topology"])
    app.include_router(scripts_router, prefix="", tags=["Legacy Scripts"])
    app.include_router(executions_router, prefix="", tags=["Legacy Executions"])
    app.include_router(inventory_router, prefix="", tags=["Legacy Inventory"])
    app.include_router(dashboard_router, prefix="", tags=["Legacy Dashboard"])

    @app.on_event("startup")
    async def startup_event():
        """Application startup tasks."""
        logger.info("Starting NetOps-Flow API...")
        init_db()
        create_default_admin()
        logger.info("NetOps-Flow API started successfully.")

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": "2.0.0"}

    return app


# Create application instance
app = create_app()
