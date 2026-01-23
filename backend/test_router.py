#!/usr/bin/env python3

# Test script to check router import

try:
    print("Testing router imports...")
    
    from fastapi import APIRouter
    print("✓ FastAPI imported")
    
    router = APIRouter(prefix="/api/coach", tags=["coach"])
    print("✓ Router created")
    
    print("Testing coach router file...")
    exec(open('app/routers/coach.py').read())
    print("✓ Coach router file executed")
    
    print("Testing import...")
    from app.routers.coach import router
    print("✓ Router imported successfully")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()