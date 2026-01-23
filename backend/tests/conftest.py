import pytest
import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tests.test_models import Base


@pytest.fixture(scope="function")
def test_db():
    """Create a temporary in-memory SQLite database for testing"""
    # Use SQLite for testing to avoid PostgreSQL dependency
    engine = create_engine("sqlite:///:memory:", echo=False)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def test_client(test_db):
    """Create a test client with database dependency override"""
    # Skip FastAPI client for now since we're testing models directly
    return None