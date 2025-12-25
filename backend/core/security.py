"""
Security utilities: JWT, password hashing, encryption, and refresh tokens.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets
import hashlib
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet, InvalidToken
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging
import pyotp

from backend.core.config import get_settings
from backend.core.database import get_db
from backend import models

logger = logging.getLogger(__name__)
settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")

# Fernet cipher for encryption
_fernet: Optional[Fernet] = None


def get_fernet() -> Fernet:
    """Get or create Fernet cipher instance."""
    global _fernet
    if _fernet is None:
        _fernet = Fernet(settings.get_encryption_key())
    return _fernet


# Password functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> bool:
    """Validate password meets minimum security requirements."""
    return len(password) >= settings.min_password_length


# JWT functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.get_jwt_secret(),
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.get_jwt_secret(),
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


# Encryption functions (for sensitive data at rest)
def encrypt_value(value: str) -> str:
    """Encrypt a string value using Fernet."""
    if not value:
        return value
    try:
        fernet = get_fernet()
        encrypted = fernet.encrypt(value.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        raise ValueError("Failed to encrypt value")


def decrypt_value(encrypted_value: str) -> str:
    """Decrypt a Fernet-encrypted string."""
    if not encrypted_value:
        return encrypted_value
    try:
        fernet = get_fernet()
        decrypted = fernet.decrypt(encrypted_value.encode())
        return decrypted.decode()
    except InvalidToken:
        logger.error("Invalid encryption token - data may be corrupted or key changed")
        raise ValueError("Failed to decrypt value - invalid token")
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        raise ValueError("Failed to decrypt value")


# Dependency functions
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_admin_user(
    current_user: models.User = Depends(get_current_active_user)
) -> models.User:
    """Get current user if they are an admin."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough privileges")
    return current_user


# ==================== TOTP/MFA FUNCTIONS ====================

def generate_totp_secret() -> str:
    """Generate a random TOTP secret key."""
    return pyotp.random_base32()


def get_totp_uri(username: str, secret: str, issuer: str = "NetOps-Flow") -> str:
    """
    Generate a TOTP provisioning URI for QR code generation.

    Args:
        username: User's username
        secret: TOTP secret key
        issuer: Application name (default: "NetOps-Flow")

    Returns:
        Provisioning URI string for QR code
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=username, issuer_name=issuer)


def verify_totp_code(secret: str, code: str) -> bool:
    """
    Verify a TOTP code against a secret.

    Args:
        secret: TOTP secret key
        code: 6-digit TOTP code to verify

    Returns:
        True if code is valid, False otherwise
    """
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)  # Allow 30s time drift
    except Exception as e:
        logger.error(f"TOTP verification error: {e}")
        return False


# ==================== REFRESH TOKEN FUNCTIONS ====================

def generate_refresh_token() -> str:
    """Generate a cryptographically secure refresh token."""
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_refresh_token_record(
    db: Session,
    user_id: int,
    token: str,
    device_info: Optional[str] = None,
    ip_address: Optional[str] = None
) -> "models.UserToken":
    """
    Create and store a new refresh token for a user.

    Args:
        db: Database session
        user_id: ID of the user
        token: The raw refresh token (will be hashed before storage)
        device_info: Optional device information (User-Agent)
        ip_address: Optional client IP address

    Returns:
        The created UserToken model instance
    """
    token_hash = hash_refresh_token(token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

    user_token = models.UserToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        device_info=device_info,
        ip_address=ip_address
    )
    db.add(user_token)
    db.commit()
    db.refresh(user_token)

    logger.info(f"Refresh token created for user_id={user_id}")
    return user_token


def validate_refresh_token(db: Session, token: str) -> Optional["models.UserToken"]:
    """
    Validate a refresh token and return the token record if valid.

    Args:
        db: Database session
        token: The raw refresh token to validate

    Returns:
        The UserToken record if valid, None otherwise
    """
    token_hash = hash_refresh_token(token)
    user_token = db.query(models.UserToken).filter(
        models.UserToken.token_hash == token_hash,
        models.UserToken.revoked == False,
        models.UserToken.expires_at > datetime.now(timezone.utc)
    ).first()

    return user_token


def revoke_refresh_token(db: Session, token: str) -> bool:
    """
    Revoke a refresh token.

    Args:
        db: Database session
        token: The raw refresh token to revoke

    Returns:
        True if token was found and revoked, False otherwise
    """
    token_hash = hash_refresh_token(token)
    user_token = db.query(models.UserToken).filter(
        models.UserToken.token_hash == token_hash
    ).first()

    if user_token:
        user_token.revoked = True
        db.commit()
        logger.info(f"Refresh token revoked for user_id={user_token.user_id}")
        return True
    return False


def revoke_all_user_tokens(db: Session, user_id: int) -> int:
    """
    Revoke all refresh tokens for a user (e.g., on password change or logout all).

    Args:
        db: Database session
        user_id: ID of the user

    Returns:
        Number of tokens revoked
    """
    result = db.query(models.UserToken).filter(
        models.UserToken.user_id == user_id,
        models.UserToken.revoked == False
    ).update({"revoked": True})
    db.commit()
    logger.info(f"Revoked {result} refresh tokens for user_id={user_id}")
    return result


def cleanup_expired_tokens(db: Session) -> int:
    """
    Remove expired and revoked tokens from the database.

    Args:
        db: Database session

    Returns:
        Number of tokens deleted
    """
    result = db.query(models.UserToken).filter(
        (models.UserToken.expires_at < datetime.now(timezone.utc)) |
        (models.UserToken.revoked == True)
    ).delete()
    db.commit()
    logger.info(f"Cleaned up {result} expired/revoked tokens")
    return result
