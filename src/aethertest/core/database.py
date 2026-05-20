"""
Database setup and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from aethertest.core.config import settings
from aethertest.core.models import Base

# Create engine
engine = create_engine(settings.DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()