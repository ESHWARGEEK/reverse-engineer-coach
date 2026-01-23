#!/usr/bin/env python3
"""Debug import issues"""

import sys
import traceback

print("Testing individual imports...")

try:
    print("1. Testing basic imports...")
    import logging
    import asyncio
    import uuid
    from typing import Callable, Dict, Any, Optional
    from datetime import datetime
    print("   Basic imports OK")
    
    print("2. Testing FastAPI imports...")
    from fastapi import Request, Response, HTTPException
    from fastapi.responses import JSONResponse
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.exceptions import HTTPException as StarletteHTTPException
    from fastapi.exceptions import RequestValidationError
    print("   FastAPI imports OK")
    
    print("3. Testing app service imports...")
    from app.services.error_handling_service import (
        error_handling_service, 
        AuthenticationError, 
        AuthorizationError,
        ErrorContext,
        ErrorCategory,
        ErrorSeverity
    )
    print("   Error handling service imports OK")
    
    print("4. Testing error monitoring imports...")
    from app.services.error_monitoring_service import (
        error_monitoring_service,
        record_error_metric
    )
    print("   Error monitoring service imports OK")
    
    print("5. Testing error handlers imports...")
    from app.error_handlers import (
        APIError,
        ServiceUnavailableError,
        RateLimitError,
        ValidationError,
        create_error_response
    )
    print("   Error handlers imports OK")
    
    print("6. Testing full module import...")
    
    # Try to execute the module step by step
    with open('app/middleware/global_error_handler.py', 'r') as f:
        content = f.read()
    
    print(f"   Module content length: {len(content)} characters")
    
    # Try to compile the module
    try:
        compiled = compile(content, 'app/middleware/global_error_handler.py', 'exec')
        print("   Module compiles successfully")
        
        # Try to execute it
        namespace = {}
        exec(compiled, namespace)
        print("   Module executes successfully")
        
        print("   Available functions in namespace:")
        for name, obj in namespace.items():
            if callable(obj) and not name.startswith('_'):
                print(f"     - {name}")
        
        if 'setup_global_error_handling' in namespace:
            print("   ✅ setup_global_error_handling found in namespace!")
        else:
            print("   ❌ setup_global_error_handling NOT found in namespace")
            
    except Exception as compile_error:
        print(f"   Module compilation/execution failed: {compile_error}")
        traceback.print_exc()
    
except Exception as e:
    print(f"Import test failed: {e}")
    traceback.print_exc()