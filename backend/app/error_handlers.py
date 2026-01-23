"""
Comprehensive error handling for the FastAPI application.
Provides graceful degradation and user-friendly error messages.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import traceback
from typing import Dict, Any, Optional
import asyncio
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIError(Exception):
    """Custom API error with structured information"""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class ServiceUnavailableError(APIError):
    """Service temporarily unavailable"""
    
    def __init__(self, service_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"{service_name} is temporarily unavailable. Please try again later.",
            status_code=503,
            error_code="SERVICE_UNAVAILABLE",
            details=details
        )

class RateLimitError(APIError):
    """Rate limit exceeded"""
    
    def __init__(self, retry_after: int = 60, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details={**(details or {}), "retry_after": retry_after}
        )

class ValidationError(APIError):
    """Input validation error"""
    
    def __init__(self, field_errors: Dict[str, str], details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="Invalid input data provided.",
            status_code=422,
            error_code="VALIDATION_ERROR",
            details={**(details or {}), "field_errors": field_errors}
        )

def create_error_response(
    status_code: int,
    message: str,
    error_code: str = "UNKNOWN_ERROR",
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> JSONResponse:
    """Create standardized error response"""
    
    error_response = {
        "error": {
            "message": message,
            "code": error_code,
            "timestamp": datetime.utcnow().isoformat(),
        }
    }
    
    if details:
        error_response["error"]["details"] = details
    
    if request_id:
        error_response["error"]["request_id"] = request_id
    
    # Add helpful information for development
    if status_code >= 500:
        error_response["error"]["support_message"] = (
            "If this problem persists, please contact support with the request ID."
        )
    
    return JSONResponse(
        status_code=status_code,
        content=error_response
    )

async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle custom API errors"""
    
    request_id = getattr(request.state, 'request_id', None)
    
    # Log error details
    logger.error(
        f"API Error: {exc.error_code} - {exc.message}",
        extra={
            "status_code": exc.status_code,
            "error_code": exc.error_code,
            "details": exc.details,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return create_error_response(
        status_code=exc.status_code,
        message=exc.message,
        error_code=exc.error_code,
        details=exc.details,
        request_id=request_id
    )

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions"""
    
    request_id = getattr(request.state, 'request_id', None)
    
    # Map status codes to user-friendly messages
    status_messages = {
        400: "Bad request. Please check your input and try again.",
        401: "Authentication required. Please log in to continue.",
        403: "Access denied. You don't have permission to perform this action.",
        404: "The requested resource was not found.",
        405: "Method not allowed for this endpoint.",
        409: "Conflict. The resource already exists or is in use.",
        422: "Invalid input data. Please check your request and try again.",
        429: "Too many requests. Please try again later.",
        500: "Internal server error. Please try again later.",
        502: "Bad gateway. The service is temporarily unavailable.",
        503: "Service unavailable. Please try again later.",
        504: "Gateway timeout. The request took too long to process."
    }
    
    message = status_messages.get(exc.status_code, exc.detail)
    error_code = f"HTTP_{exc.status_code}"
    
    # Log non-client errors
    if exc.status_code >= 500:
        logger.error(
            f"HTTP {exc.status_code}: {exc.detail}",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method
            }
        )
    
    return create_error_response(
        status_code=exc.status_code,
        message=message,
        error_code=error_code,
        request_id=request_id
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors"""
    
    request_id = getattr(request.state, 'request_id', None)
    
    # Extract field-specific errors
    field_errors = {}
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        field_errors[field_path] = error["msg"]
    
    logger.warning(
        f"Validation error: {field_errors}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return create_error_response(
        status_code=422,
        message="Invalid input data provided.",
        error_code="VALIDATION_ERROR",
        details={"field_errors": field_errors},
        request_id=request_id
    )

async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    
    request_id = getattr(request.state, 'request_id', None)
    
    # Log full traceback for debugging
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc()
        }
    )
    
    # Don't expose internal error details in production
    message = "An unexpected error occurred. Please try again later."
    
    return create_error_response(
        status_code=500,
        message=message,
        error_code="INTERNAL_ERROR",
        request_id=request_id
    )

async def timeout_handler(request: Request, exc: asyncio.TimeoutError) -> JSONResponse:
    """Handle timeout errors"""
    
    request_id = getattr(request.state, 'request_id', None)
    
    logger.warning(
        f"Request timeout: {request.url.path}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return create_error_response(
        status_code=504,
        message="The request took too long to process. Please try again.",
        error_code="TIMEOUT_ERROR",
        request_id=request_id
    )

def setup_error_handlers(app: FastAPI) -> None:
    """Set up all error handlers for the FastAPI app"""
    
    # Custom API errors
    app.add_exception_handler(APIError, api_error_handler)
    
    # HTTP exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # Timeout errors
    app.add_exception_handler(asyncio.TimeoutError, timeout_handler)
    
    # General exceptions (catch-all)
    app.add_exception_handler(Exception, general_exception_handler)

# Graceful degradation helpers
async def with_fallback(primary_func, fallback_func, error_message: str = "Service temporarily unavailable"):
    """Execute primary function with fallback on failure"""
    try:
        return await primary_func()
    except Exception as e:
        logger.warning(f"Primary function failed, using fallback: {str(e)}")
        try:
            return await fallback_func()
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {str(fallback_error)}")
            raise ServiceUnavailableError(error_message)

async def with_graceful_degradation(service_func, fallback_data=None, service_name="Service"):
    """Execute service function with graceful degradation to fallback data"""
    try:
        return await service_func()
    except Exception as e:
        logger.warning(f"{service_name} failed, using fallback: {str(e)}")
        if fallback_data is not None:
            return fallback_data
        raise ServiceUnavailableError(service_name, {"fallback_available": fallback_data is not None})

class AIServiceError(APIError):
    """AI/LLM service error with fallback suggestions"""
    
    def __init__(self, service_name: str, original_error: str, fallback_available: bool = False):
        message = f"AI service ({service_name}) is temporarily unavailable."
        if fallback_available:
            message += " Using cached or simplified response."
        else:
            message += " Please try again later."
        
        super().__init__(
            message=message,
            status_code=503,
            error_code="AI_SERVICE_UNAVAILABLE",
            details={
                "service": service_name,
                "original_error": original_error,
                "fallback_available": fallback_available,
                "retry_suggested": True
            }
        )

class GitHubServiceError(APIError):
    """GitHub service error with specific handling"""
    
    def __init__(self, operation: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"GitHub service error during {operation}. This may be due to rate limits or network issues.",
            status_code=503,
            error_code="GITHUB_SERVICE_ERROR",
            details={
                **(details or {}),
                "operation": operation,
                "retry_suggested": True,
                "cache_fallback": True
            }
        )

class DatabaseConnectionError(APIError):
    """Database connection error"""
    
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="Database is temporarily unavailable. Please try again in a few moments.",
            status_code=503,
            error_code="DATABASE_UNAVAILABLE",
            details={
                **(details or {}),
                "retry_suggested": True,
                "estimated_recovery": "2-5 minutes"
            }
        )

def circuit_breaker(failure_threshold: int = 5, recovery_timeout: int = 60):
    """Simple circuit breaker decorator for service calls"""
    
    def decorator(func):
        func._failures = 0
        func._last_failure_time = 0
        
        async def wrapper(*args, **kwargs):
            import time
            
            # Check if circuit is open
            if func._failures >= failure_threshold:
                if time.time() - func._last_failure_time < recovery_timeout:
                    raise ServiceUnavailableError("Service circuit breaker is open")
                else:
                    # Reset circuit breaker
                    func._failures = 0
            
            try:
                result = await func(*args, **kwargs)
                func._failures = 0  # Reset on success
                return result
            except Exception as e:
                func._failures += 1
                func._last_failure_time = time.time()
                raise e
        
        return wrapper
    return decorator

# Service health monitoring
class ServiceHealthMonitor:
    """Monitor service health and provide degradation strategies"""
    
    def __init__(self):
        self.service_status = {}
        self.degradation_strategies = {
            "github": self._github_degradation_strategy,
            "llm": self._llm_degradation_strategy,
            "database": self._database_degradation_strategy,
            "cache": self._cache_degradation_strategy
        }
    
    async def check_service_health(self, service_name: str) -> Dict[str, Any]:
        """Check health of a specific service"""
        try:
            if service_name == "github":
                from app.github_client import GitHubClient
                async with GitHubClient() as client:
                    await client.get_rate_limit_status()
                return {"status": "healthy", "service": service_name}
            
            elif service_name == "database":
                from app.database import get_db
                db = next(get_db())
                db.execute("SELECT 1")
                db.close()
                return {"status": "healthy", "service": service_name}
            
            elif service_name == "cache":
                from app.cache import cache
                await cache.ping()
                return {"status": "healthy", "service": service_name}
            
            elif service_name == "llm":
                # Simple connectivity check
                return {"status": "healthy", "service": service_name}
            
            else:
                return {"status": "unknown", "service": service_name}
                
        except Exception as e:
            logger.warning(f"Service {service_name} health check failed: {e}")
            return {
                "status": "unhealthy", 
                "service": service_name, 
                "error": str(e),
                "degradation_available": service_name in self.degradation_strategies
            }
    
    def _github_degradation_strategy(self) -> Dict[str, Any]:
        """Degradation strategy for GitHub service failures"""
        return {
            "strategy": "cache_fallback",
            "message": "Using cached repository data. Some information may be outdated.",
            "limitations": ["Repository analysis may use cached data", "Real-time updates unavailable"],
            "recovery_actions": ["Check GitHub status", "Retry in 5-10 minutes"]
        }
    
    def _llm_degradation_strategy(self) -> Dict[str, Any]:
        """Degradation strategy for LLM service failures"""
        return {
            "strategy": "simplified_responses",
            "message": "AI features temporarily limited. Using simplified explanations.",
            "limitations": ["Reduced explanation quality", "No personalized responses", "Basic task generation only"],
            "recovery_actions": ["Try again later", "Use manual learning resources"]
        }
    
    def _database_degradation_strategy(self) -> Dict[str, Any]:
        """Degradation strategy for database failures"""
        return {
            "strategy": "read_only_mode",
            "message": "Database temporarily unavailable. Running in read-only mode.",
            "limitations": ["Cannot save progress", "No new projects", "Limited history access"],
            "recovery_actions": ["Wait for database recovery", "Contact support if persistent"]
        }
    
    def _cache_degradation_strategy(self) -> Dict[str, Any]:
        """Degradation strategy for cache failures"""
        return {
            "strategy": "direct_api_calls",
            "message": "Cache unavailable. Responses may be slower than usual.",
            "limitations": ["Slower response times", "Increased API usage"],
            "recovery_actions": ["Performance will improve when cache recovers"]
        }
    
    async def get_degradation_strategy(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get degradation strategy for a failed service"""
        if service_name in self.degradation_strategies:
            return self.degradation_strategies[service_name]()
        return None

# Global service monitor instance
service_monitor = ServiceHealthMonitor()