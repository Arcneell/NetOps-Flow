"""
Authentication Router - Login, token management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging

from backend.core.database import get_db
from backend.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    validate_password_strength,
    get_current_active_user,
)
from backend.core.rate_limiter import get_rate_limiter
from backend.core.config import get_settings
from backend import models, schemas

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication"])


class PasswordChange(BaseModel):
    password: str


@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT token."""
    client_ip = request.client.host if request.client else "unknown"

    # Check rate limit
    rate_limiter = get_rate_limiter()
    if not rate_limiter.is_allowed(client_ip, "login"):
        remaining_time = rate_limiter.get_reset_time(client_ip, "login")
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Please try again in {remaining_time} seconds.",
            headers={"Retry-After": str(remaining_time)},
        )

    user = db.query(models.User).filter(
        models.User.username == form_data.username.lower()
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for username: {form_data.username} from IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    access_token = create_access_token(data={"sub": user.username})
    logger.info(f"Successful login for user: {user.username} from IP: {client_ip}")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "permissions": user.permissions or {}
        }
    }


@router.get("/me", response_model=schemas.User)
async def read_users_me(
    current_user: models.User = Depends(get_current_active_user)
):
    """Get current authenticated user."""
    return current_user


@router.put("/me/password")
async def update_password(
    password_data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Update current user's password."""
    if not validate_password_strength(password_data.password):
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {settings.min_password_length} characters"
        )

    hashed_password = get_password_hash(password_data.password)
    current_user.hashed_password = hashed_password
    db.commit()

    logger.info(f"Password updated for user: {current_user.username}")
    return {"message": "Password updated successfully"}
