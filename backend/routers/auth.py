"""
Authentication Router - Login, token management, and refresh tokens.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
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
    generate_totp_secret,
    get_totp_uri,
    verify_totp_code,
    decrypt_value,
    generate_refresh_token,
    create_refresh_token_record,
    validate_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens,
)
from backend.core.rate_limiter import get_rate_limiter
from backend.core.config import get_settings
from backend import models, schemas

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(tags=["Authentication"])


class PasswordChange(BaseModel):
    password: str


@router.post("/token")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT token or MFA challenge.

    Returns Token if MFA is disabled, or MFAResponse if MFA is enabled.
    """
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

        # Log failed login attempt
        audit_log = models.AuditLog(
            username=form_data.username,
            action="LOGIN_FAILED",
            resource_type="auth",
            ip_address=client_ip,
            extra_data={"reason": "incorrect_credentials"}
        )
        db.add(audit_log)
        db.commit()

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

    # Check if MFA is enabled for this user
    if user.mfa_enabled:
        logger.info(f"MFA challenge initiated for user: {user.username} from IP: {client_ip}")

        # Log MFA challenge
        audit_log = models.AuditLog(
            user_id=user.id,
            username=user.username,
            action="MFA_CHALLENGE",
            resource_type="auth",
            ip_address=client_ip
        )
        db.add(audit_log)
        db.commit()

        return {
            "mfa_required": True,
            "user_id": user.id,
            "message": "MFA verification required"
        }

    # No MFA - generate tokens directly
    # Include user_id and role in JWT for audit middleware optimization (avoids DB lookup)
    access_token = create_access_token(data={
        "sub": user.username,
        "user_id": user.id,
        "role": user.role
    })
    refresh_token = generate_refresh_token()
    user_agent = request.headers.get("User-Agent", "Unknown")

    # Store refresh token
    create_refresh_token_record(
        db=db,
        user_id=user.id,
        token=refresh_token,
        device_info=user_agent[:255] if user_agent else None,
        ip_address=client_ip
    )

    logger.info(f"Successful login for user: {user.username} from IP: {client_ip}")

    # Log successful login
    audit_log = models.AuditLog(
        user_id=user.id,
        username=user.username,
        action="LOGIN_SUCCESS",
        resource_type="auth",
        ip_address=client_ip
    )
    db.add(audit_log)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "permissions": user.permissions or [],
            "avatar": user.avatar,
            "mfa_enabled": user.mfa_enabled,
            "is_active": user.is_active,
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
    is_valid, error_message = validate_password_strength(password_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=error_message
        )

    hashed_password = get_password_hash(password_data.password)
    current_user.hashed_password = hashed_password
    db.commit()

    logger.info(f"Password updated for user: {current_user.username}")
    return {"message": "Password updated successfully"}


@router.put("/me/profile", response_model=schemas.User)
async def update_profile(
    profile_data: schemas.UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Update current user's profile (email)."""
    if profile_data.email is not None:
        current_user.email = profile_data.email

    db.commit()
    db.refresh(current_user)

    logger.info(f"Profile updated for user: {current_user.username}")
    return current_user


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Upload user avatar/profile picture."""
    import os
    import uuid

    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only JPEG, PNG, GIF, and WebP are allowed."
        )

    # Validate file size (max 2MB)
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 2MB."
        )

    # Generate unique filename
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"

    # Ensure avatars directory exists
    avatars_dir = os.path.join(settings.upload_dir, "avatars")
    os.makedirs(avatars_dir, exist_ok=True)

    # Delete old avatar if exists
    if current_user.avatar:
        old_path = os.path.join(avatars_dir, current_user.avatar)
        if os.path.exists(old_path):
            os.remove(old_path)

    # Save new avatar
    avatar_path = os.path.join(avatars_dir, filename)
    with open(avatar_path, "wb") as f:
        f.write(content)

    # Update user record
    current_user.avatar = filename
    db.commit()

    logger.info(f"Avatar uploaded for user: {current_user.username}")
    return {"message": "Avatar uploaded successfully", "avatar": filename}


@router.delete("/me/avatar")
async def delete_avatar(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Delete user avatar."""
    import os

    if not current_user.avatar:
        raise HTTPException(status_code=404, detail="No avatar to delete")

    # Delete file
    avatars_dir = os.path.join(settings.upload_dir, "avatars")
    avatar_path = os.path.join(avatars_dir, current_user.avatar)
    if os.path.exists(avatar_path):
        os.remove(avatar_path)

    # Clear avatar from user record
    current_user.avatar = None
    db.commit()

    logger.info(f"Avatar deleted for user: {current_user.username}")
    return {"message": "Avatar deleted successfully"}


@router.get("/avatars/{filename}")
async def get_avatar(filename: str):
    """Serve user avatar files."""
    import os
    import re
    from fastapi.responses import FileResponse

    # Sanitize filename to prevent path traversal
    # Only allow alphanumeric characters, underscores, hyphens, and dots
    if not re.match(r'^[\w\-\.]+$', filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Prevent directory traversal
    if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
        raise HTTPException(status_code=400, detail="Invalid filename")

    avatars_dir = os.path.join(settings.upload_dir, "avatars")
    file_path = os.path.join(avatars_dir, filename)

    # Verify the resolved path is within the avatars directory
    real_path = os.path.realpath(file_path)
    real_avatars_dir = os.path.realpath(avatars_dir)
    if not real_path.startswith(real_avatars_dir):
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Avatar not found")

    return FileResponse(file_path)


# ==================== MFA ENDPOINTS ====================

@router.post("/verify-mfa", response_model=schemas.Token)
async def verify_mfa(
    request: Request,
    mfa_data: schemas.MFAVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Verify MFA code and issue JWT token.

    This endpoint is called after the user passes password authentication
    and MFA is enabled on their account.
    """
    client_ip = request.client.host if request.client else "unknown"

    # Rate limiting for MFA verification (prevent brute force on TOTP codes)
    rate_limiter = get_rate_limiter()
    mfa_rate_key = f"mfa:{mfa_data.user_id}"
    if not rate_limiter.is_allowed(client_ip, mfa_rate_key):
        remaining_time = rate_limiter.get_reset_time(client_ip, mfa_rate_key)
        logger.warning(f"MFA rate limit exceeded for user_id: {mfa_data.user_id} from IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many MFA attempts. Please try again in {remaining_time} seconds.",
            headers={"Retry-After": str(remaining_time)},
        )

    # Fetch user
    user = db.query(models.User).filter(models.User.id == mfa_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user"
        )

    if not user.mfa_enabled or not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled for this user"
        )

    # Decrypt TOTP secret
    try:
        decrypted_secret = decrypt_value(user.totp_secret)
    except Exception as e:
        logger.error(f"Failed to decrypt TOTP secret for user {user.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA configuration error"
        )

    # Verify TOTP code
    if not verify_totp_code(decrypted_secret, mfa_data.code):
        logger.warning(f"Failed MFA verification for user: {user.username} from IP: {client_ip}")

        # Log failed MFA attempt
        audit_log = models.AuditLog(
            user_id=user.id,
            username=user.username,
            action="MFA_FAILED",
            resource_type="auth",
            ip_address=client_ip,
            extra_data={"reason": "invalid_code"}
        )
        db.add(audit_log)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code"
        )

    # MFA successful - generate tokens
    # Include user_id and role in JWT for audit middleware optimization (avoids DB lookup)
    access_token = create_access_token(data={
        "sub": user.username,
        "user_id": user.id,
        "role": user.role
    })
    refresh_token = generate_refresh_token()
    user_agent = request.headers.get("User-Agent", "Unknown")

    # Store refresh token
    create_refresh_token_record(
        db=db,
        user_id=user.id,
        token=refresh_token,
        device_info=user_agent[:255] if user_agent else None,
        ip_address=client_ip
    )

    logger.info(f"Successful MFA login for user: {user.username} from IP: {client_ip}")

    # Log successful MFA login
    audit_log = models.AuditLog(
        user_id=user.id,
        username=user.username,
        action="MFA_SUCCESS",
        resource_type="auth",
        ip_address=client_ip
    )
    db.add(audit_log)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "permissions": user.permissions or [],
            "avatar": user.avatar,
            "mfa_enabled": user.mfa_enabled,
            "is_active": user.is_active,
        }
    }


@router.post("/mfa/setup", response_model=schemas.MFASetupResponse)
async def setup_mfa(
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Generate a new TOTP secret and QR code URI for MFA setup.

    This does NOT enable MFA - user must call /mfa/enable with a valid code.
    """
    # Generate new TOTP secret
    secret = generate_totp_secret()
    qr_uri = get_totp_uri(current_user.username, secret)

    logger.info(f"MFA setup initiated for user: {current_user.username}")

    return {
        "secret": secret,
        "qr_uri": qr_uri,
        "message": "Scan QR code with authenticator app"
    }


@router.post("/mfa/enable-with-secret")
async def enable_mfa_with_secret(
    secret: str,
    code: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Enable MFA by verifying the TOTP code against provided secret.

    Frontend should call /mfa/setup, display QR code, then call this endpoint
    with the secret and the code scanned from the authenticator app.
    """
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled"
        )

    # Verify the code against the secret
    if not verify_totp_code(secret, code):
        logger.warning(f"Failed MFA enable attempt for user: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code. Please verify the code from your authenticator app."
        )

    # Store the secret (auto-encrypted by SQLAlchemy hook)
    current_user.totp_secret = secret
    current_user.mfa_enabled = True
    db.commit()

    logger.info(f"MFA enabled for user: {current_user.username}")

    # Log MFA enablement
    audit_log = models.AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="MFA_ENABLED",
        resource_type="user",
        resource_id=str(current_user.id)
    )
    db.add(audit_log)
    db.commit()

    return {"message": "MFA enabled successfully"}


@router.post("/mfa/disable")
async def disable_mfa(
    mfa_request: schemas.MFADisableRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Disable MFA after verifying the user's password.

    Requires current password for security.
    """
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled"
        )

    # Verify password
    if not verify_password(mfa_request.password, current_user.hashed_password):
        logger.warning(f"Failed MFA disable attempt for user: {current_user.username} (wrong password)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )

    # Disable MFA
    current_user.mfa_enabled = False
    current_user.totp_secret = None
    db.commit()

    logger.info(f"MFA disabled for user: {current_user.username}")

    # Log MFA disablement
    audit_log = models.AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="MFA_DISABLED",
        resource_type="user",
        resource_id=str(current_user.id)
    )
    db.add(audit_log)
    db.commit()

    return {"message": "MFA disabled successfully"}


# ==================== REFRESH TOKEN ENDPOINTS ====================

@router.post("/refresh", response_model=schemas.TokenWithRefresh)
async def refresh_access_token(
    request: Request,
    token_request: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh an access token using a valid refresh token.

    This endpoint allows clients to obtain a new access token without
    requiring the user to re-authenticate. The old refresh token is
    revoked and a new one is issued (token rotation).
    """
    client_ip = request.client.host if request.client else "unknown"

    # Validate the refresh token
    user_token = validate_refresh_token(db, token_request.refresh_token)
    if not user_token:
        logger.warning(f"Invalid refresh token attempt from IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Get the user
    user = db.query(models.User).filter(models.User.id == user_token.user_id).first()
    if not user or not user.is_active:
        # Revoke the token if user is inactive or doesn't exist
        revoke_refresh_token(db, token_request.refresh_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is not available"
        )

    # Revoke the old refresh token (token rotation)
    revoke_refresh_token(db, token_request.refresh_token)

    # Generate new tokens
    # Include user_id and role in JWT for audit middleware optimization (avoids DB lookup)
    access_token = create_access_token(data={
        "sub": user.username,
        "user_id": user.id,
        "role": user.role
    })
    new_refresh_token = generate_refresh_token()
    user_agent = request.headers.get("User-Agent", "Unknown")

    # Store new refresh token
    create_refresh_token_record(
        db=db,
        user_id=user.id,
        token=new_refresh_token,
        device_info=user_agent[:255] if user_agent else None,
        ip_address=client_ip
    )

    logger.info(f"Token refreshed for user: {user.username} from IP: {client_ip}")

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "permissions": user.permissions or [],
            "avatar": user.avatar,
            "mfa_enabled": user.mfa_enabled,
            "is_active": user.is_active,
        }
    }


@router.post("/logout")
async def logout(
    request: Request,
    token_request: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Logout by revoking the refresh token.

    The client should also discard the access token on their side.
    """
    client_ip = request.client.host if request.client else "unknown"

    # Revoke the refresh token
    revoked = revoke_refresh_token(db, token_request.refresh_token)

    # Log logout
    audit_log = models.AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="LOGOUT",
        resource_type="auth",
        ip_address=client_ip
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"User logged out: {current_user.username} from IP: {client_ip}")

    return {"message": "Logged out successfully"}


@router.post("/logout-all")
async def logout_all_devices(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Logout from all devices by revoking all refresh tokens for the user.
    """
    client_ip = request.client.host if request.client else "unknown"

    # Revoke all refresh tokens
    count = revoke_all_user_tokens(db, current_user.id)

    # Log logout all
    audit_log = models.AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="LOGOUT_ALL",
        resource_type="auth",
        ip_address=client_ip,
        extra_data={"tokens_revoked": count}
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"User logged out from all devices: {current_user.username}, {count} tokens revoked")

    return {"message": f"Logged out from all devices. {count} sessions terminated."}
