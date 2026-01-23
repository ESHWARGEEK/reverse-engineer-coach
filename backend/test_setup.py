#!/usr/bin/env python3
"""
Simple test to verify the backend setup is working correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.main import app
from app.config import settings

def test_app_creation():
    """Test that the FastAPI app can be created successfully"""
    assert app is not None
    assert app.title == "Reverse Engineer Coach API"
    print("✓ FastAPI app created successfully")

def test_config_loading():
    """Test that configuration is loaded correctly"""
    assert settings is not None
    assert settings.environment == "development"
    print("✓ Configuration loaded successfully")

def test_routes():
    """Test that basic routes are defined"""
    routes = [route.path for route in app.routes]
    assert "/" in routes
    assert "/health" in routes
    print("✓ Basic routes defined successfully")

if __name__ == "__main__":
    print("Testing Reverse Engineer Coach Backend Setup...")
    print("=" * 50)
    
    try:
        test_app_creation()
        test_config_loading()
        test_routes()
        
        print("=" * 50)
        print("✅ All backend setup tests passed!")
        print(f"Backend is ready to run on {settings.api_host}:{settings.api_port}")
        
    except Exception as e:
        print(f"❌ Setup test failed: {e}")
        sys.exit(1)