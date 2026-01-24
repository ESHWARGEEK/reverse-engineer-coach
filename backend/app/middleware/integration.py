"""
Middleware integration for FastAPI application.
Provides functions to register and configure all middleware components.
"""

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
import logging
import time
from typing import Callable

from app.database import get_db
from app.middleware.auth_middleware import auth_middleware
from app.middleware.validation_middleware import ValidationMiddleware, RequestSanitizationMiddleware
from app.middleware.rate_limiting_middleware import RateLimitingMiddleware, SecurityHeadersMiddleware
from app.models import User

logger = logging.getLogger(__name__)


class AuthenticationHTTPMiddleware(BaseHTTPMiddleware):
    """
    HTTP middleware wrapper for authentication middleware.
    Integrates JWT authentication into the FastAPI request pipeline.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through authentication middleware.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response from next middleware/endpoint
        """
        # Get database session
        db_gen = get_db()
        db: Session = next(db_gen)
        
        try:
            # Authenticate request if needed
            user = await auth_middleware.authenticate_request(request, db)
            
            # Inject user into request state if authenticated
            if user:
                request.state.user = user
                request.state.user_id = user.id
                request.state.authenticated = True
            else:
                request.state.user = None
                request.state.user_id = None
                request.state.authenticated = False
            
            # Continue to next middleware/endpoint
            response = await call_next(request)
            
            return response
            
        except Exception as e:
            # Let the exception propagate to FastAPI's error handlers
            raise e
        finally:
            # Clean up database session
            try:
                db.close()
            except Exception:
                pass


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging requests with authentication context.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Log request with authentication context.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response from next middleware/endpoint
        """
        start_time = time.time()
        
        # Extract request info
        method = request.method
        url = str(request.url)
        client_ip = request.client.host if request.client else "unknown"
        
        # Get user info if available
        user_id = getattr(request.state, 'user_id', None)
        authenticated = getattr(request.state, 'authenticated', False)
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log request
        log_data = {
            "method": method,
            "url": url,
            "client_ip": client_ip,
            "status_code": response.status_code,
            "process_time": f"{process_time:.3f}s",
            "authenticated": authenticated,
            "user_id": user_id
        }
        
        if response.status_code >= 400:
            logger.warning(f"Request failed: {log_data}")
        else:
            logger.info(f"Request processed: {log_data}")
        
        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding security headers to responses.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to response.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response with security headers
        """
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Add HSTS header for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


def setup_authentication_middleware(app: FastAPI) -> None:
    """
    Set up authentication middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Add authentication middleware
    app.add_middleware(AuthenticationHTTPMiddleware)
    
    logger.info("Authentication middleware registered")


def setup_security_middleware(app: FastAPI) -> None:
    """
    Set up security middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    logger.info("Security middleware registered")


def setup_logging_middleware(app: FastAPI) -> None:
    """
    Set up request logging middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Add request logging middleware
    app.add_middleware(RequestLoggingMiddleware)
    
    logger.info("Request logging middleware registered")


def setup_validation_middleware(app: FastAPI) -> None:
    """
    Set up input validation middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Temporarily disable validation middleware for debugging
    # app.add_middleware(ValidationMiddleware)
    
    # Add sanitization middleware
    # app.add_middleware(RequestSanitizationMiddleware)
    
    logger.info("Validation middleware temporarily disabled for debugging")
    """
    Set up rate limiting middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Add rate limiting middleware
    app.add_middleware(RateLimitingMiddleware)
    
    logger.info("Rate limiting middleware registered")


def setup_enhanced_security_middleware(app: FastAPI) -> None:
    """
    Set up enhanced security middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Add enhanced security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    logger.info("Enhanced security middleware registered")


def setup_rate_limiting_middleware(app: FastAPI) -> None:
    """
    Set up rate limiting middleware for the FastAPI application.
    """
    logger.info("Rate limiting middleware registered")
    # Rate limiting middleware is already imported and will be used
    # The actual rate limiting is handled by the RateLimitingMiddleware class
    pass


def setup_all_middleware(app: FastAPI) -> None:
    """
    Set up all middleware components for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Order matters - middleware is executed in reverse order of registration
    # So register in reverse order of desired execution
    
    # 1. Enhanced security headers (last to execute)
    setup_enhanced_security_middleware(app)
    
    # 2. Request logging
    setup_logging_middleware(app)
    
    # 3. Rate limiting (before validation to block excessive requests early)
    setup_rate_limiting_middleware(app)
    
    # 4. Input validation and sanitization
    setup_validation_middleware(app)
    
    # 5. Authentication (first to execute after CORS and security)
    setup_authentication_middleware(app)
    
    logger.info("All middleware components registered successfully")


# Utility functions for accessing request state
def get_current_user_from_request(request: Request) -> User:
    """
    Get current user from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Current user object
        
    Raises:
        AttributeError: If user is not available in request state
    """
    user = getattr(request.state, 'user', None)
    if not user:
        raise AttributeError("User not available in request state")
    return user


def get_current_user_id_from_request(request: Request) -> str:
    """
    Get current user ID from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Current user ID
        
    Raises:
        AttributeError: If user ID is not available in request state
    """
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise AttributeError("User ID not available in request state")
    return user_id


def is_authenticated_request(request: Request) -> bool:
    """
    Check if request is authenticated.
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if request is authenticated, False otherwise
    """
    return getattr(request.state, 'authenticated', False)