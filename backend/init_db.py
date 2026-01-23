#!/usr/bin/env python3
"""Initialize the database with all tables"""

from app.database import engine, Base
from app import models  # Import all models

def init_database():
    """Create all database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_database()