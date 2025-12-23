"""
Security utilities: JWT, password hashing, and encryption.
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet, InvalidToken
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

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
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
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
