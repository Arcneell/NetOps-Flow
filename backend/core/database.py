"""
Database configuration and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import time
import logging

from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

Base = declarative_base()


def create_db_engine(url: str, retry: bool = True):
    """Create database engine with optional retry logic."""
    engine_kwargs = {
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "pool_pre_ping": True,  # Verify connections before checkout
    }

    if retry:
        max_retries = 30
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                engine = create_engine(url, **engine_kwargs)
                with engine.connect() as connection:
                    logger.info("Successfully connected to the database!")
                    return engine
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Database not ready (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {retry_delay}s... Error: {e}"
                    )
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to connect to database after {max_retries} attempts")
                    raise
    else:
        return create_engine(url, **engine_kwargs)


# Create engine and session factory
engine = create_db_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    from backend import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
