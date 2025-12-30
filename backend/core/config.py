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


def _read_secret_file(file_path: str) -> str:
    """Read a secret from a Docker secrets file."""
    try:
        return Path(file_path).read_text().strip()
    except Exception:
        return ""


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
        default="postgresql://netops:netopspassword@localhost:5432/netops_flow",
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
    docker_sandbox_image: str = Field(default="netops-sandbox:latest")
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
