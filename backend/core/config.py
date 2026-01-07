"""
Centralized Configuration using Pydantic Settings.
All environment variables are validated at startup.
Supports Docker secrets via *_FILE environment variables.
"""
from functools import lru_cache
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator
import os
import base64
import binascii


def _read_secret_file(file_path: str) -> str:
    """Read a secret from a Docker secrets file.

    Raises:
        FileNotFoundError: If the secret file doesn't exist
        PermissionError: If the file cannot be read
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Secret file not found: {file_path}")
    return path.read_text().strip()


def _decode_base64(value: str) -> bytes:
    """Decode a base64 string, raising ValueError on failure."""
    try:
        # Ensure proper padding
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)
    except (binascii.Error, ValueError) as e:
        raise ValueError(f"Invalid base64 encoding: {e}") from e


def _derive_fernet_key(raw_key: str) -> str:
    """Derive a valid Fernet key from any string using PBKDF2.

    Fernet requires exactly 32 bytes, base64 url-safe encoded.
    This function uses PBKDF2 to derive a valid key from arbitrary input.
    """
    import hashlib
    # Use PBKDF2 with a fixed salt (app-specific) to derive 32 bytes
    # The salt is fixed so the same input always produces the same key
    salt = b"inframate-encryption-v1"
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        raw_key.encode("utf-8"),
        salt,
        iterations=100000,
        dklen=32
    )
    return base64.urlsafe_b64encode(derived).decode("utf-8")


class Settings(BaseSettings):
    """Application settings with strict validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database - stored as string to support special characters in passwords
    # Format validation is done via field_validator
    database_url: str = Field(
        default="postgresql://inframate:inframatepassword@localhost:5432/inframate",
        description="PostgreSQL connection URL"
    )
    db_pool_size: int = Field(default=5, ge=1, le=20)
    db_max_overflow: int = Field(default=10, ge=0, le=50)

    # Redis - stored as string to support flexibility
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0",
        description="Celery result backend URL"
    )

    # Initial admin password (required for first setup)
    initial_admin_password: str | None = Field(
        default=None,
        description="Initial admin password for first setup"
    )

    # JWT & Security
    jwt_secret_key: str = Field(
        default="",
        description="JWT secret key (REQUIRED - must be set in environment or via JWT_SECRET_KEY_FILE)"
    )
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30, ge=5, le=1440)  # 30 minutes for access tokens
    refresh_token_expire_days: int = Field(default=7, ge=1, le=30)  # 7 days for refresh tokens
    min_password_length: int = Field(default=8, ge=6, le=128)

    # Encryption (Fernet key for encrypting sensitive data)
    encryption_key: str = Field(
        default="",
        description="Fernet encryption key for sensitive data (REQUIRED - must be set in environment or via ENCRYPTION_KEY_FILE)"
    )

    # Rate Limiting
    rate_limit_window: int = Field(default=60, ge=10, le=600)
    rate_limit_max_requests: int = Field(default=5, ge=1, le=100)

    # CORS
    allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Comma-separated list of allowed origins"
    )

    # File Storage
    upload_dir: str = Field(default="/uploads")
    scripts_dir: str = Field(default="/scripts_storage")
    max_script_name_length: int = Field(default=100, ge=10, le=255)
    max_filename_length: int = Field(default=255, ge=50, le=500)
    script_execution_timeout: int = Field(default=300, ge=30, le=3600)
    max_output_size: int = Field(default=1048576, ge=1024)  # 1MB

    # SSH/WinRM
    ssh_timeout: int = Field(default=30, ge=5, le=120)
    ssh_banner_timeout: int = Field(default=30, ge=5, le=120)
    winrm_timeout: int = Field(default=60, ge=10, le=300)

    # Docker Sandboxing
    docker_sandbox_enabled: bool = Field(default=True)
    docker_sandbox_image: str = Field(default="inframate-sandbox:latest")
    docker_sandbox_memory_limit: str = Field(default="256m")
    docker_sandbox_cpu_limit: float = Field(default=0.5, ge=0.1, le=4.0)
    docker_sandbox_timeout: int = Field(default=300, ge=30, le=3600)

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")  # json or text

    @model_validator(mode='before')
    @classmethod
    def load_secrets_from_files(cls, values: dict) -> dict:
        """
        Load secrets from Docker secrets files if *_FILE env vars are set.
        This allows secure secret management in production deployments.
        """
        secret_mappings = [
            ('jwt_secret_key', 'JWT_SECRET_KEY_FILE'),
            ('encryption_key', 'ENCRYPTION_KEY_FILE'),
            ('initial_admin_password', 'INITIAL_ADMIN_PASSWORD_FILE'),
        ]

        for field_name, env_file_var in secret_mappings:
            file_path = os.environ.get(env_file_var)
            if file_path and Path(file_path).exists():
                secret_value = _read_secret_file(file_path)
                if secret_value:
                    values[field_name] = secret_value

        return values

    @model_validator(mode='after')
    def validate_required_secrets(self) -> 'Settings':
        """
        Validate that required secrets are present.
        JWT_SECRET_KEY and ENCRYPTION_KEY are mandatory.
        """
        if not self.jwt_secret_key:
            raise ValueError(
                "JWT_SECRET_KEY is required. Set it via environment variable "
                "or JWT_SECRET_KEY_FILE for Docker secrets."
            )
        if not self.encryption_key:
            raise ValueError(
                "ENCRYPTION_KEY is required. Set it via environment variable "
                "or ENCRYPTION_KEY_FILE for Docker secrets."
            )
        return self

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_key(cls, v: str) -> str:
        """
        Validate JWT secret.
        Prefer base64 decoding to ensure entropy; fall back to accepting legacy
        raw strings of length >= 32 characters.
        """
        try:
            decoded = _decode_base64(v)
            if len(decoded) < 32:
                raise ValueError("JWT_SECRET_KEY must decode to at least 32 bytes")
            return v
        except ValueError:
            # Legacy tolerance: accept raw strings of reasonable length
            if len(v) >= 32:
                return v
            raise ValueError("JWT_SECRET_KEY must be base64 or at least 32 characters")

    @field_validator("encryption_key")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        """
        Validate or derive a valid Fernet key.

        Fernet requires exactly 32 bytes, base64 url-safe encoded.
        - If the key is already valid (base64, 32 bytes): use it directly
        - If not: derive a valid key using PBKDF2

        This ensures the application never crashes due to invalid key format.
        """
        try:
            decoded = _decode_base64(v)
            if len(decoded) == 32:
                # Valid Fernet key
                return v
        except ValueError:
            pass

        # Key is not valid Fernet format - derive one using PBKDF2
        if len(v) < 8:
            raise ValueError("ENCRYPTION_KEY must be at least 8 characters")

        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            "ENCRYPTION_KEY is not a valid Fernet key format. "
            "Deriving a key using PBKDF2. For production, generate a proper "
            "Fernet key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
        return _derive_fernet_key(v)

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format (basic check)."""
        if not v.startswith(("postgresql://", "postgres://")):
            raise ValueError("DATABASE_URL must start with postgresql:// or postgres://")
        return v

    @field_validator("redis_url", "celery_broker_url", "celery_result_backend")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL format (basic check)."""
        if not v.startswith("redis://"):
            raise ValueError("Redis URL must start with redis://")
        return v

    @field_validator("allowed_origins")
    @classmethod
    def parse_origins(cls, v: str) -> str:
        """Validate origins format."""
        origins = [o.strip() for o in v.split(",") if o.strip()]
        if not origins:
            raise ValueError("At least one origin must be specified")
        return v

    @property
    def origins_list(self) -> List[str]:
        """Get origins as a list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    # Compatibility aliases (URLs are already strings)
    @property
    def database_url_str(self) -> str:
        """Get database URL as string (alias for compatibility)."""
        return self.database_url

    @property
    def redis_url_str(self) -> str:
        """Get Redis URL as string (alias for compatibility)."""
        return self.redis_url

    @property
    def celery_broker_url_str(self) -> str:
        """Get Celery broker URL as string (alias for compatibility)."""
        return self.celery_broker_url

    @property
    def celery_result_backend_str(self) -> str:
        """Get Celery result backend URL as string (alias for compatibility)."""
        return self.celery_result_backend

    def get_jwt_secret(self) -> str:
        """Get JWT secret key (always available since it's required)."""
        return self.jwt_secret_key

    def get_encryption_key(self) -> bytes:
        """Get Fernet encryption key (always available since it's required)."""
        return self.encryption_key.encode()


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
