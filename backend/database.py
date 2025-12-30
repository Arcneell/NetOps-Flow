from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import time
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://inframate:inframatepassword@localhost:5432/inframate")

def get_engine(url):
    """Retry connection to database until successful."""
    while True:
        try:
            engine = create_engine(url)
            # Try to connect
            with engine.connect() as connection:
                logger.info("Successfully connected to the database!")
                return engine
        except Exception as e:
            logger.warning(f"Database not ready yet, retrying in 2 seconds... Error: {e}")
            time.sleep(2)

engine = get_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()