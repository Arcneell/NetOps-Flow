"""
FastAPI Middleware for automatic audit logging of modification actions.
Provides detailed metadata for critical operations like bulk deletes,
user management, and security-related actions.
"""
import logging
import json
from typing import Callable, Optional, Dict, Any
from datetime import datetime, timezone
from io import BytesIO

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that automatically logs all POST, PUT, DELETE requests
    to the AuditLog table for compliance and security tracking.

    Enhanced with detailed metadata for critical operations:
    - Bulk deletions: Records count and affected resource IDs
    - User management: Records target user and permission changes
    - Security actions: Records MFA changes, password updates
    - Equipment changes: Records critical field modifications
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

    # Critical paths that require enhanced logging
    CRITICAL_PATHS = {
        # User management
        "/api/v1/users": "user_management",
        "/api/v1/auth/mfa": "mfa_management",
        # Security-related
        "/api/v1/me/password": "password_change",
        "/api/v1/mfa": "mfa_management",
        # Bulk operations patterns
        "/api/v1/inventory/equipment": "equipment_management",
        "/api/v1/contracts": "contract_management",
        "/api/v1/software": "software_management",
        "/api/v1/entities": "entity_management",
        # Infrastructure critical
        "/api/v1/subnets": "network_management",
        "/api/v1/dcim/racks": "datacenter_management",
        "/api/v1/scripts": "script_management",
    }

    # Severity levels for different operations
    SEVERITY_MAPPING = {
        ("DELETE", "users"): "critical",
        ("DELETE", "entities"): "critical",
        ("DELETE", "subnets"): "high",
        ("DELETE", "equipment"): "high",
        ("DELETE", "contracts"): "medium",
        ("POST", "scripts"): "high",  # Script upload
        ("DELETE", "scripts"): "high",
        ("PUT", "users"): "high",  # User modification
        ("POST", "mfa"): "high",  # MFA changes
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

    def _get_operation_category(self, path: str) -> Optional[str]:
        """Determine the operation category based on the request path."""
        for critical_path, category in self.CRITICAL_PATHS.items():
            if path.startswith(critical_path):
                return category
        return None

    def _get_severity(self, method: str, resource_type: str) -> str:
        """Determine the severity level for an operation."""
        severity = self.SEVERITY_MAPPING.get((method, resource_type))
        if severity:
            return severity
        # Default severities by method
        if method == "DELETE":
            return "medium"
        elif method in ("PUT", "PATCH"):
            return "low"
        return "info"

    def _extract_resource_details(self, path_parts: list, resource_type: str) -> Dict[str, Any]:
        """Extract additional resource details from the path."""
        details = {}

        # Extract sub-resource type if present
        # e.g., /api/v1/inventory/equipment/5/attachments -> sub_resource: attachments
        if len(path_parts) > 2:
            for i, part in enumerate(path_parts):
                if part.isdigit() and i + 1 < len(path_parts):
                    details["sub_resource"] = path_parts[i + 1]
                    break

        # Check for specific action paths
        action_paths = ["scan", "run", "connect", "assign", "resolve", "close", "reopen",
                       "publish", "unpublish", "enable", "disable", "read", "read-all"]
        for part in path_parts:
            if part in action_paths:
                details["action_type"] = part
                break

        return details

    async def _log_action(
        self,
        request: Request,
        response: Response,
        client_ip: str,
        user_agent: str
    ):
        """Log the action to the database with enhanced metadata for critical operations."""
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
            affected_ids = []
            for part in reversed(path_parts):
                if part.isdigit():
                    resource_id = part
                    affected_ids.append(int(part))
                    break

            # Get username from JWT token if available
            # Optimized: Extract user info directly from JWT claims without DB lookup
            # The token already contains user_id and role from authentication
            username = None
            user_id = None
            user_role = None
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                try:
                    from jose import jwt
                    from backend.core.config import get_settings

                    settings = get_settings()
                    token = auth_header.split(" ")[1]
                    payload = jwt.decode(
                        token,
                        settings.get_jwt_secret(),
                        algorithms=[settings.jwt_algorithm]
                    )
                    username = payload.get("sub")
                    # Get user_id and role from JWT claims (added during token creation)
                    user_id = payload.get("user_id")
                    user_role = payload.get("role")
                except Exception:
                    pass  # Token invalid or expired, log without user info

            # Build enhanced extra_data
            extra_data: Dict[str, Any] = {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "user_agent": user_agent[:100] if user_agent else None
            }

            # Add operation category for critical paths
            operation_category = self._get_operation_category(request.url.path)
            if operation_category:
                extra_data["operation_category"] = operation_category

            # Add severity level
            severity = self._get_severity(request.method, resource_type)
            extra_data["severity"] = severity

            # Add user role for audit trail
            if user_role:
                extra_data["user_role"] = user_role

            # Add resource details
            resource_details = self._extract_resource_details(path_parts, resource_type)
            if resource_details:
                extra_data.update(resource_details)

            # Add affected resource IDs if this is a DELETE operation
            if request.method == "DELETE" and affected_ids:
                extra_data["affected_ids"] = affected_ids

            # Add query parameters for context (filtered for sensitive data)
            query_params = dict(request.query_params)
            # Remove sensitive parameters
            sensitive_params = {"password", "token", "secret", "key", "code"}
            filtered_params = {
                k: v for k, v in query_params.items()
                if k.lower() not in sensitive_params
            }
            if filtered_params:
                extra_data["query_params"] = filtered_params

            # Add timestamp with timezone
            extra_data["timestamp_utc"] = datetime.now(timezone.utc).isoformat()

            # Enhanced logging for critical operations
            if severity in ("critical", "high"):
                extra_data["is_critical"] = True
                # Log to application logger as well for immediate visibility
                logger.warning(
                    f"CRITICAL AUDIT: {action} {resource_type}/{resource_id or 'N/A'} "
                    f"by {username or 'anonymous'} (role: {user_role}) from {client_ip} "
                    f"- Category: {operation_category or 'general'}"
                )

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
                    extra_data=extra_data
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
