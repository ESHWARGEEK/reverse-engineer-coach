"""
Comprehensive Input Validation Middleware
Applies validation to all API endpoints with SQL injection prevention and input sanitization.
"""

import json
import logging
from typing import Dict, Any, Optional, Callable
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.services.validation_service import ValidationService, ValidationResult
from app.schemas.validation_schemas import ValidationRules, ValidationPatterns, SecurityValidationRules

logger = logging.getLogger(__name__)


class ValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive input validation and security checks.
    """
    
    def __init__(self, app, validation_service: Optional[ValidationService] = None):
        """
        Initialize validation middleware.
        
        Args:
            app: FastAPI application instance
            validation_service: Optional validation service instance
        """
        super().__init__(app)
        self.validation_service = validation_service or ValidationService()
        
        # Routes that require validation
        self.validation_routes = {
            # Authentication endpoints
            '/auth/register': ValidationRules.USER_REGISTRATION,
            '/auth/login': ValidationRules.USER_LOGIN,
            '/auth/refresh': ValidationRules.TOKEN_REFRESH,
            
            # Profile endpoints
            '/profile': ValidationRules.PROFILE_UPDATE,
            '/profile/password': ValidationRules.PASSWORD_UPDATE,
            '/profile/credentials': ValidationRules.CREDENTIAL_UPDATE,
            
            # Discovery endpoints
            '/discover/repositories': ValidationRules.REPOSITORY_DISCOVERY,
            
            # Project endpoints
            '/projects': ValidationRules.PROJECT_CREATE,
            
            # File endpoints
            '/files': ValidationRules.FILE_CONTENT,
            
            # Coach endpoints
            '/coach/message': ValidationRules.COACH_MESSAGE,
            
            # GitHub endpoints
            '/github/analyze': ValidationRules.GITHUB_ANALYZE,
            
            # Search endpoints
            '/search': ValidationRules.SEARCH_QUERY,
        }
        
        # Routes that don't require validation
        self.skip_validation_routes = {
            '/docs',
            '/openapi.json',
            '/redoc',
            '/health',
            '/metrics'
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through validation middleware.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response from next middleware or validation error
        """
        try:
            # Skip validation for certain routes
            if self._should_skip_validation(request):
                return await call_next(request)
            
            # Validate request headers
            header_validation = self._validate_headers(request)
            if header_validation.has_errors():
                return self._create_validation_error_response(header_validation.errors)
            
            # Validate request size
            size_validation = await self._validate_request_size(request)
            if size_validation.has_errors():
                return self._create_validation_error_response(size_validation.errors)
            
            # Validate request body for POST/PUT requests
            if request.method in ['POST', 'PUT', 'PATCH']:
                body_validation = await self._validate_request_body(request)
                if body_validation.has_errors():
                    return self._create_validation_error_response(body_validation.errors)
            
            # Validate query parameters for GET requests
            if request.method == 'GET':
                query_validation = self._validate_query_parameters(request)
                if query_validation.has_errors():
                    return self._create_validation_error_response(query_validation.errors)
            
            # Continue to next middleware/endpoint
            response = await call_next(request)
            
            # Log successful validation
            logger.debug(f"Request validation passed for {request.method} {request.url.path}")
            
            return response
            
        except Exception as e:
            logger.error(f"Validation middleware error: {e}")
            
            # Create error response with CORS headers
            headers = {
                "Access-Control-Allow-Origin": "https://reveng.netlify.app",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Accept, Accept-Language, Authorization, Content-Language, Content-Type, X-Request-ID, X-Requested-With",
                "Access-Control-Expose-Headers": "X-Request-ID, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset"
            }
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal validation error"},
                headers=headers
            )
    
    def _should_skip_validation(self, request: Request) -> bool:
        """
        Check if validation should be skipped for this request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if validation should be skipped
        """
        path = request.url.path
        
        # Skip validation for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return True
        
        # Skip validation for specific routes
        if path in self.skip_validation_routes:
            return True
        
        # Skip validation for static files
        if path.startswith('/static/') or path.startswith('/assets/'):
            return True
        
        # Skip validation for health checks
        if path.endswith('/health') or path.endswith('/ping'):
            return True
        
        return False
    
    def _validate_headers(self, request: Request) -> ValidationResult:
        """
        Validate HTTP request headers.
        
        Args:
            request: FastAPI request object
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult()
        
        try:
            # Convert headers to dict
            headers = dict(request.headers)
            
            # Validate headers using validation service
            header_result = self.validation_service.validate_request_headers(headers)
            if header_result.has_errors():
                result.errors.update(header_result.errors)
            
            # Validate user agent if present
            user_agent = headers.get('user-agent', '')
            if user_agent:
                ua_result = self.validation_service.validate_user_agent(user_agent)
                if ua_result.has_errors():
                    result.errors.update(ua_result.errors)
            
            # Check for required headers
            if request.method in ['POST', 'PUT', 'PATCH']:
                content_type = headers.get('content-type', '')
                if not content_type:
                    result.add_error('content-type', 'Content-Type header is required')
                elif 'application/json' not in content_type and 'multipart/form-data' not in content_type:
                    result.add_error('content-type', 'Unsupported Content-Type')
            
        except Exception as e:
            logger.error(f"Header validation error: {e}")
            result.add_error('headers', 'Invalid request headers')
        
        return result
    
    async def _validate_request_size(self, request: Request) -> ValidationResult:
        """
        Validate request body size to prevent DoS attacks.
        
        Args:
            request: FastAPI request object
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult()
        
        try:
            # Check Content-Length header
            content_length = request.headers.get('content-length')
            if content_length:
                size = int(content_length)
                max_size = SecurityValidationRules.SUSPICIOUS_PATTERNS['large_payload']
                
                if size > max_size:
                    result.add_error('request_size', f'Request too large (max {max_size // (1024*1024)}MB)')
            
        except (ValueError, TypeError):
            result.add_error('request_size', 'Invalid Content-Length header')
        
        return result
    
    async def _validate_request_body(self, request: Request) -> ValidationResult:
        """
        Validate request body content and structure.
        
        Args:
            request: FastAPI request object
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult()
        
        try:
            # Get request path for validation rules
            path = request.url.path.rstrip('/')
            
            # Find matching validation rules
            validation_rules = None
            for route_pattern, rules in self.validation_routes.items():
                if path.endswith(route_pattern.rstrip('/')):
                    validation_rules = rules
                    break
            
            # If no specific rules found, apply general validation
            if not validation_rules:
                return await self._validate_general_body(request)
            
            # Read and parse request body
            body = await request.body()
            if not body:
                return result
            
            try:
                # Try to parse as JSON
                data = json.loads(body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                result.add_error('body', 'Invalid JSON format')
                return result
            
            # Apply validation rules
            sanitized_data, validation_result = self.validation_service.sanitize_and_validate_input(
                data, validation_rules
            )
            
            if validation_result.has_errors():
                result.errors.update(validation_result.errors)
            else:
                # Store sanitized data for use by endpoint
                request.state.validated_data = sanitized_data
            
        except Exception as e:
            logger.error(f"Body validation error: {e}")
            result.add_error('body', 'Request body validation failed')
        
        return result
    
    async def _validate_general_body(self, request: Request) -> ValidationResult:
        """
        Apply general validation to request body when no specific rules exist.
        
        Args:
            request: FastAPI request object
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult()
        
        try:
            body = await request.body()
            if not body:
                return result
            
            # Check for malicious content
            body_str = body.decode('utf-8', errors='ignore')
            
            # Check for XSS attempts
            if self.validation_service.detect_xss_attempt(body_str):
                result.add_error('body', 'Potentially malicious content detected')
            
            # Check for SQL injection
            if self.validation_service.sanitizer.check_sql_injection(body_str):
                result.add_error('body', 'Invalid request content')
            
            # Validate JSON structure if applicable
            content_type = request.headers.get('content-type', '')
            if 'application/json' in content_type:
                try:
                    data = json.loads(body_str)
                    json_result = self.validation_service.validate_json_input(data)
                    if json_result.has_errors():
                        result.errors.update(json_result.errors)
                except json.JSONDecodeError:
                    result.add_error('body', 'Invalid JSON format')
            
        except Exception as e:
            logger.error(f"General body validation error: {e}")
            result.add_error('body', 'Request validation failed')
        
        return result
    
    def _validate_query_parameters(self, request: Request) -> ValidationResult:
        """
        Validate query parameters for GET requests.
        
        Args:
            request: FastAPI request object
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult()
        
        try:
            query_params = dict(request.query_params)
            
            for param_name, param_value in query_params.items():
                # Check for SQL injection in parameters
                if self.validation_service.sanitizer.check_sql_injection(param_value):
                    result.add_error(param_name, f'Invalid parameter value: {param_name}')
                
                # Check for XSS attempts
                if self.validation_service.detect_xss_attempt(param_value):
                    result.add_error(param_name, f'Invalid parameter content: {param_name}')
                
                # Validate parameter length
                if len(param_value) > 1000:  # Reasonable limit for query params
                    result.add_error(param_name, f'Parameter too long: {param_name}')
            
        except Exception as e:
            logger.error(f"Query parameter validation error: {e}")
            result.add_error('query_params', 'Query parameter validation failed')
        
        return result
    
    def _create_validation_error_response(self, errors: Dict[str, str]) -> JSONResponse:
        """
        Create standardized validation error response with CORS headers.
        
        Args:
            errors: Dictionary of validation errors
            
        Returns:
            JSONResponse with validation errors and CORS headers
        """
        # Add CORS headers to validation error responses
        headers = {
            "Access-Control-Allow-Origin": "https://reveng.netlify.app",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Accept, Accept-Language, Authorization, Content-Language, Content-Type, X-Request-ID, X-Requested-With",
            "Access-Control-Expose-Headers": "X-Request-ID, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset"
        }
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation failed",
                "errors": errors,
                "code": "VALIDATION_ERROR"
            },
            headers=headers
        )


class RequestSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for sanitizing request data after validation.
    """
    
    def __init__(self, app):
        """Initialize sanitization middleware."""
        super().__init__(app)
        self.validation_service = ValidationService()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through sanitization middleware.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response from next middleware
        """
        try:
            # Apply additional sanitization if needed
            if hasattr(request.state, 'validated_data'):
                # Data was already sanitized by validation middleware
                pass
            
            response = await call_next(request)
            return response
            
        except Exception as e:
            logger.error(f"Sanitization middleware error: {e}")
            
            # Create error response with CORS headers
            headers = {
                "Access-Control-Allow-Origin": "https://reveng.netlify.app",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Accept, Accept-Language, Authorization, Content-Language, Content-Type, X-Request-ID, X-Requested-With",
                "Access-Control-Expose-Headers": "X-Request-ID, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset"
            }
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Request processing error"},
                headers=headers
            )


# Utility functions for manual validation
def validate_request_data(data: Dict[str, Any], validation_rules: Dict[str, Dict[str, Any]]) -> tuple[Dict[str, Any], ValidationResult]:
    """
    Manually validate request data using validation rules.
    
    Args:
        data: Request data to validate
        validation_rules: Validation rules to apply
        
    Returns:
        Tuple of (sanitized_data, validation_result)
    """
    validation_service = ValidationService()
    return validation_service.sanitize_and_validate_input(data, validation_rules)


def create_validation_response(errors: Dict[str, str]) -> JSONResponse:
    """
    Create standardized validation error response with CORS headers.
    
    Args:
        errors: Dictionary of validation errors
        
    Returns:
        JSONResponse with validation errors and CORS headers
    """
    # Add CORS headers to validation error responses
    headers = {
        "Access-Control-Allow-Origin": "https://reveng.netlify.app",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Accept, Accept-Language, Authorization, Content-Language, Content-Type, X-Request-ID, X-Requested-With",
        "Access-Control-Expose-Headers": "X-Request-ID, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset"
    }
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation failed",
            "errors": errors,
            "code": "VALIDATION_ERROR"
        },
        headers=headers
    )


# Global middleware instances
validation_middleware = ValidationMiddleware
sanitization_middleware = RequestSanitizationMiddleware