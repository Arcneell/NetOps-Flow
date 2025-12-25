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
    generate_totp_secret,
    get_totp_uri,
    verify_totp_code,
    encrypt_value,
    decrypt_value,
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

    # No MFA - generate token directly
    access_token = create_access_token(data={"sub": user.username})
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

    # MFA successful - generate token
    access_token = create_access_token(data={"sub": user.username})
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
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "permissions": user.permissions or {}
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


@router.post("/mfa/enable")
async def enable_mfa(
    mfa_request: schemas.MFAEnableRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Enable MFA by verifying the TOTP code from the setup.

    User must have called /mfa/setup first to get the secret.
    """
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled"
        )

    # The secret should be passed in the request or stored temporarily
    # For security, we'll require the user to provide the secret from /mfa/setup
    # In a production app, you might store this in a temporary session
    # For now, we'll require re-setup if needed

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Please provide the secret from /mfa/setup call"
    )


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

    # Encrypt and store the secret
    encrypted_secret = encrypt_value(secret)
    current_user.totp_secret = encrypted_secret
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
