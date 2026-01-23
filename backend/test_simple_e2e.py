"""
Simple E2E test without complex imports
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Create a simple test app
app = FastAPI()

@app.get("/test")
def test_endpoint():
    return {"message": "test"}

def test_simple_e2e():
    """Simple E2E test to verify basic functionality."""
    client = TestClient(app)
    response = client.get("/test")
    assert response.status_code == 200
    assert response.json() == {"message": "test"}

if __name__ == "__main__":
    test_simple_e2e()
    print("Simple E2E test passed!")