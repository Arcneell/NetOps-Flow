"""
FastAPI Middleware for automatic audit logging of modification actions.
"""
import logging
from typing import Callable
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that automatically logs all POST, PUT, DELETE requests
    to the AuditLog table for compliance and security tracking.
    """

    # Methods that modify data
    AUDIT_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

    # Paths to exclude from audit logging (auth endpoints log separately)
    EXCLUDE_PATHS = {
        "/api/v1/auth/token",
        "/api/v1/auth/refresh",
        "/api/v1/auth/verify-mfa",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process each request and log modification actions."""
        # Skip non-modifying methods
        if request.method not in self.AUDIT_METHODS:
            return await call_next(request)

        # Skip excluded paths
        if request.url.path in self.EXCLUDE_PATHS:
            return await call_next(request)

        # Skip paths that start with excluded prefixes
        for excluded in self.EXCLUDE_PATHS:
            if request.url.path.startswith(excluded):
                return await call_next(request)

        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")[:255]

        # Process the request
        response = await call_next(request)

        # Only log successful modifications (2xx status codes)
        if 200 <= response.status_code < 300:
            await self._log_action(request, response, client_ip, user_agent)

        return response

    async def _log_action(
        self,
        request: Request,
        response: Response,
        client_ip: str,
        user_agent: str
    ):
        """Log the action to the database."""
        try:
            # Import here to avoid circular imports
            from backend.core.database import SessionLocal
            from backend import models

            # Determine action type from HTTP method
            action_map = {
                "POST": "CREATE",
                "PUT": "UPDATE",
                "PATCH": "UPDATE",
                "DELETE": "DELETE"
            }
            action = action_map.get(request.method, request.method)

            # Extract resource type from path
            # Example: /api/v1/inventory/equipment/5 -> inventory/equipment
            path_parts = request.url.path.split("/")
            # Remove /api/v1 prefix if present
            if len(path_parts) > 3 and path_parts[1] == "api" and path_parts[2] == "v1":
                path_parts = path_parts[3:]
            else:
                path_parts = path_parts[1:]

            # Get resource type (first significant part)
            resource_type = path_parts[0] if path_parts else "unknown"

            # Get resource ID if present (numeric part at the end)
            resource_id = None
            for part in reversed(path_parts):
                if part.isdigit():
                    resource_id = part
                    break

            # Get username from JWT token if available
            username = None
            user_id = None
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                try:
                    from backend.core.security import decode_token
                    from jose import JWTError, jwt
                    from backend.core.config import get_settings

                    settings = get_settings()
                    token = auth_header.split(" ")[1]
                    payload = jwt.decode(
                        token,
                        settings.jwt_secret_key,
                        algorithms=[settings.jwt_algorithm]
                    )
                    username = payload.get("sub")

                    # Look up user ID
                    if username:
                        db = SessionLocal()
                        try:
                            user = db.query(models.User).filter(
                                models.User.username == username
                            ).first()
                            if user:
                                user_id = user.id
                        finally:
                            db.close()
                except Exception:
                    pass  # Token invalid or expired, log without user info

            # Create audit log entry
            db = SessionLocal()
            try:
                audit_log = models.AuditLog(
                    user_id=user_id,
                    username=username or "anonymous",
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    ip_address=client_ip,
                    extra_data={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "user_agent": user_agent[:100] if user_agent else None
                    }
                )
                db.add(audit_log)
                db.commit()

                logger.debug(
                    f"Audit: {action} {resource_type}/{resource_id or 'N/A'} "
                    f"by {username or 'anonymous'} from {client_ip}"
                )
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")
                db.rollback()
            finally:
                db.close()

        except Exception as e:
            # Don't let audit logging failures affect the request
            logger.error(f"Audit middleware error: {e}")


def add_audit_middleware(app):
    """Add audit logging middleware to the FastAPI app."""
    app.add_middleware(AuditLoggingMiddleware)
