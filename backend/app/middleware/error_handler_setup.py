"""
Global error handler setup for the application.
"""

import logging
from typing import Dict, Any
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class GlobalErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware that provides comprehensive error management.
    """
    
    def __init__(self, app, enable_monitoring: bool = True):
        super().__init__(app)
        self.enable_monitoring = enable_monitoring
    
    async def dispatch(self, request, call_next):
        """Process request with error handling."""
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Unhandled error: {e}")
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error"}
            )


def setup_global_error_handling(app: FastAPI, enable_monitoring: bool = True) -> None:
    """
    Set up global error handling middleware.
    
    Args:
        app: FastAPI application instance
        enable_monitoring: Whether to enable error monitoring
    """
    
    # Add global error handling middleware
    app.add_middleware(GlobalErrorHandlerMiddleware, enable_monitoring=enable_monitoring)
    
    logger.info("Global error handling middleware configured successfully")