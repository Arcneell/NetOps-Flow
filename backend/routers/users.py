"""
User Management Router - Admin operations for users.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import re
import logging

from backend.core.database import get_db
from backend.core.security import (
    get_password_hash,
    validate_password_strength,
    get_current_admin_user,
)
from backend.core.config import get_settings
from backend import models, schemas

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=schemas.User)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Create a new user (admin only)."""
    # Validate username
    if not user.username or len(user.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if not re.match(r'^[a-zA-Z0-9_]+$', user.username):
        raise HTTPException(
            status_code=400,
            detail="Username can only contain letters, numbers, and underscores"
        )

    # Validate password strength
    if not validate_password_strength(user.password):
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {settings.min_password_length} characters"
        )

    # Check for existing user
    db_user = db.query(models.User).filter(
        models.User.username == user.username.lower()
    ).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Validate role
    if user.role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin' or 'user'")

    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username.lower(),
        email=user.email,
        hashed_password=hashed_password,
        role=user.role,
        is_active=user.is_active
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    logger.info(f"User '{user.username}' created by admin '{current_user.username}'")
    return db_user


@router.get("/", response_model=List[schemas.User])
def read_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """List all users (admin only)."""
    return db.query(models.User).all()


@router.put("/{user_id}", response_model=schemas.User)
def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Update a user (admin only)."""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent deactivating the last admin
    if user_update.is_active is False and db_user.role == "admin":
        active_admins = db.query(models.User).filter(
            models.User.role == "admin",
            models.User.is_active == True,
            models.User.id != user_id
        ).count()
        if active_admins == 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot deactivate the last active admin"
            )

    # Update fields
    if user_update.role is not None:
        if user_update.role not in ["admin", "user"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        db_user.role = user_update.role

    if user_update.is_active is not None:
        db_user.is_active = user_update.is_active

    if user_update.email is not None:
        db_user.email = user_update.email

    if user_update.password:
        if not validate_password_strength(user_update.password):
            raise HTTPException(
                status_code=400,
                detail=f"Password must be at least {settings.min_password_length} characters"
            )
        db_user.hashed_password = get_password_hash(user_update.password)

    db.commit()
    db.refresh(db_user)

    logger.info(f"User '{db_user.username}' updated by admin '{current_user.username}'")
    return db_user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Delete a user (admin only)."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent deleting the last admin
    if db_user.role == "admin":
        admin_count = db.query(models.User).filter(models.User.role == "admin").count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last admin")

    db.delete(db_user)
    db.commit()

    logger.info(f"User '{db_user.username}' deleted by admin '{current_user.username}'")
    return {"ok": True}
