"""
Centralized Configuration using Pydantic Settings.
All environment variables are validated at startup.
"""
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
import secrets


class Settings(BaseSettings):
    """Application settings with strict validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database
    database_url: str = Field(
        default="postgresql://netops:netopspassword@localhost:5432/netops_flow",
        description="PostgreSQL connection URL"
    )
    db_pool_size: int = Field(default=5, ge=1, le=20)
    db_max_overflow: int = Field(default=10, ge=0, le=50)

    # Redis
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

    # JWT & Security
    jwt_secret_key: Optional[str] = Field(
        default=None,
        description="JWT secret key (generated if not provided)"
    )
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=480, ge=5, le=1440)
    min_password_length: int = Field(default=8, ge=6, le=128)

    # Encryption (Fernet key for encrypting sensitive data)
    encryption_key: Optional[str] = Field(
        default=None,
        description="Fernet encryption key for sensitive data"
    )

    # Rate Limiting
    rate_limit_window: int = Field(default=60, ge=10, le=600)
    rate_limit_max_requests: int = Field(default=5, ge=1, le=100)

    # CORS
    allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Comma-separated list of allowed origins"
    )

    # Scripts
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

    def get_jwt_secret(self) -> str:
        """Get or generate JWT secret key."""
        if self.jwt_secret_key:
            return self.jwt_secret_key
        import logging
        logging.warning("JWT_SECRET_KEY not set! Using generated key. Set JWT_SECRET_KEY in production.")
        return secrets.token_urlsafe(32)

    def get_encryption_key(self) -> bytes:
        """Get or generate Fernet encryption key."""
        from cryptography.fernet import Fernet
        if self.encryption_key:
            return self.encryption_key.encode()
        import logging
        logging.warning("ENCRYPTION_KEY not set! Using generated key. Set ENCRYPTION_KEY in production.")
        return Fernet.generate_key()


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
