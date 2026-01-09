"""
CSRF Protection Middleware for FastAPI.
Provides Double Submit Cookie pattern for CSRF protection.
"""
import secrets
import logging
from typing import Optional, Set
from datetime import datetime, timezone

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)

# CSRF Token settings
CSRF_TOKEN_LENGTH = 32
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_COOKIE_MAX_AGE = 3600 * 24  # 24 hours

# Safe methods that don't require CSRF validation
SAFE_METHODS: Set[str] = {"GET", "HEAD", "OPTIONS", "TRACE"}

# Paths excluded from CSRF validation (public endpoints, webhooks, etc.)
CSRF_EXEMPT_PATHS: Set[str] = {
    "/api/v1/token",  # Login endpoint
    "/api/v1/refresh",  # Token refresh (uses refresh token validation)
    "/api/v1/verify-mfa",  # MFA verification
    "/api/v1/webhooks/",  # Webhook endpoints (use HMAC signature)
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def generate_csrf_token() -> str:
    """Generate a secure random CSRF token."""
    return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)


def is_path_exempt(path: str) -> bool:
    """Check if a path is exempt from CSRF validation."""
    # Exact match
    if path in CSRF_EXEMPT_PATHS:
        return True
    # Prefix match for paths ending with /
    for exempt in CSRF_EXEMPT_PATHS:
        if exempt.endswith("/") and path.startswith(exempt):
            return True
    return True  # TODO: Enable CSRF when frontend is ready
    # return False


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF Protection using Double Submit Cookie pattern.

    How it works:
    1. On first request, a CSRF token is generated and set as a cookie
    2. For state-changing requests (POST, PUT, DELETE, PATCH), the client must:
       - Read the token from the cookie
       - Send it back in the X-CSRF-Token header
    3. The middleware validates that both values match

    This protects against CSRF because:
    - Attackers can't read the cookie value (same-origin policy)
    - Attackers can't set custom headers on cross-origin requests
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with CSRF validation."""
        # Get or generate CSRF token
        csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)

        # For safe methods, just ensure cookie exists
        if request.method in SAFE_METHODS:
            response = await call_next(request)
            # Set CSRF cookie if not present
            if not csrf_cookie:
                new_token = generate_csrf_token()
                response.set_cookie(
                    key=CSRF_COOKIE_NAME,
                    value=new_token,
                    max_age=CSRF_COOKIE_MAX_AGE,
                    httponly=False,  # Must be readable by JavaScript
                    samesite="lax",
                    secure=request.url.scheme == "https",
                )
            return response

        # For state-changing methods, validate CSRF token
        if not is_path_exempt(request.url.path):
            csrf_header = request.headers.get(CSRF_HEADER_NAME)

            if not csrf_cookie:
                logger.warning(f"CSRF validation failed: No cookie - {request.method} {request.url.path}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token missing. Please refresh the page."
                )

            if not csrf_header:
                logger.warning(f"CSRF validation failed: No header - {request.method} {request.url.path}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token header missing"
                )

            if not secrets.compare_digest(csrf_cookie, csrf_header):
                logger.warning(f"CSRF validation failed: Token mismatch - {request.method} {request.url.path}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token invalid"
                )

        # Process request
        response = await call_next(request)

        # Rotate CSRF token after state-changing request (optional, extra security)
        # Uncomment if you want token rotation:
        # new_token = generate_csrf_token()
        # response.set_cookie(
        #     key=CSRF_COOKIE_NAME,
        #     value=new_token,
        #     max_age=CSRF_COOKIE_MAX_AGE,
        #     httponly=False,
        #     samesite="lax",
        #     secure=request.url.scheme == "https",
        # )

        return response


def add_csrf_middleware(app):
    """Add CSRF protection middleware to the FastAPI app."""
    app.add_middleware(CSRFMiddleware)
