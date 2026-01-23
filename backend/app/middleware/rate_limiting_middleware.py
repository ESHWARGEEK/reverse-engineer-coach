"""
Rate Limiting Middleware
Applies rate limiting to API endpoints with IP-based and user-based limits.
"""

import logging
from typing import Callable, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.services.rate_limiting_service import rate_limiting_service, RateLimitResult

logger = logging.getLogger(__name__)


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for applying rate limiting to API endpoints.
    """
    
    def __init__(self, app, enable_ip_limiting: bool = True, enable_user_limiting: bool = True):
        """
        Initialize rate limiting middleware.
        
        Args:
            app: FastAPI application instance
            enable_ip_limiting: Whether to enable IP-based rate limiting
            enable_user_limiting: Whether to enable user-based rate limiting
        """
        super().__init__(app)
        self.enable_ip_limiting = enable_ip_limiting
        self.enable_user_limiting = enable_user_limiting
        
        # Endpoints that require rate limiting
        self.rate_limited_endpoints = {
            '/api/v1/auth/login': 'auth_login',
            '/api/v1/auth/register': 'auth_register',
            '/api/v1/auth/refresh': 'auth_refresh',
            '/api/v1/discover/repositories': 'api_discovery',
            '/api/v1/discover/analyze': 'api_analysis',
            '/api/v1/profile/password': 'password_change',
            '/api/v1/profile/credentials': 'credential_update',
        }
        
        # Endpoints to skip rate limiting
        self.skip_rate_limiting = {
            '/docs',
            '/openapi.json',
            '/redoc',
            '/health',
            '/metrics',
            '/',
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through rate limiting middleware.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response from next middleware or rate limit error
        """
        try:
            # Skip rate limiting for certain endpoints
            if self._should_skip_rate_limiting(request):
                return await call_next(request)
            
            # Get client IP address
            client_ip = self._get_client_ip(request)
            
            # Check for suspicious activity
            user_agent = request.headers.get('user-agent', '')
            is_suspicious, reason = rate_limiting_service.is_suspicious_activity(
                client_ip, user_agent
            )
            
            if is_suspicious:
                logger.warning(f"Suspicious activity detected from {client_ip}: {reason}")
                return self._create_rate_limit_response(
                    "Suspicious activity detected", 
                    429, 
                    retry_after=300  # 5 minutes
                )
            
            # Apply IP-based rate limiting
            if self.enable_ip_limiting:
                ip_result = self._check_ip_rate_limit(request, client_ip)
                if not ip_result.allowed:
                    logger.warning(f"IP rate limit exceeded for {client_ip}")
                    return self._create_rate_limit_response_from_result(ip_result)
            
            # Apply user-based rate limiting for authenticated requests
            if self.enable_user_limiting:
                user_id = getattr(request.state, 'user_id', None)
                if user_id:
                    user_result = self._check_user_rate_limit(request, user_id)
                    if not user_result.allowed:
                        logger.warning(f"User rate limit exceeded for user {user_id}")
                        return self._create_rate_limit_response_from_result(user_result)
            
            # Continue to next middleware/endpoint
            response = await call_next(request)
            
            # Add rate limit headers to response
            self._add_rate_limit_headers(response, request, client_ip)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting middleware error: {e}")
            # Continue without rate limiting on error
            return await call_next(request)
    
    def _should_skip_rate_limiting(self, request: Request) -> bool:
        """
        Check if rate limiting should be skipped for this request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if rate limiting should be skipped
        """
        path = request.url.path
        
        # Skip for specific endpoints
        if path in self.skip_rate_limiting:
            return True
        
        # Skip for static files
        if path.startswith('/static/') or path.startswith('/assets/'):
            return True
        
        # Skip for OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            return True
        
        return False
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client IP address
        """
        # Check for forwarded headers (behind proxy)
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip.strip()
        
        # Fallback to direct client IP
        if request.client:
            return request.client.host
        
        return 'unknown'
    
    def _get_endpoint_type(self, request: Request) -> str:
        """
        Get endpoint type for rate limiting rules.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Endpoint type string
        """
        path = request.url.path
        
        # Check for exact matches
        if path in self.rate_limited_endpoints:
            return self.rate_limited_endpoints[path]
        
        # Check for pattern matches
        if path.startswith('/api/v1/auth/'):
            return 'auth_general'
        elif path.startswith('/api/v1/discover/'):
            return 'api_discovery'
        elif path.startswith('/api/v1/profile/'):
            return 'api_general'
        elif path.startswith('/api/v1/'):
            return 'api_general'
        
        return 'api_general'
    
    def _check_ip_rate_limit(self, request: Request, client_ip: str) -> RateLimitResult:
        """
        Check IP-based rate limit.
        
        Args:
            request: FastAPI request object
            client_ip: Client IP address
            
        Returns:
            RateLimitResult
        """
        endpoint_type = self._get_endpoint_type(request)
        return rate_limiting_service.check_ip_rate_limit(client_ip, endpoint_type)
    
    def _check_user_rate_limit(self, request: Request, user_id: str) -> RateLimitResult:
        """
        Check user-based rate limit.
        
        Args:
            request: FastAPI request object
            user_id: User ID
            
        Returns:
            RateLimitResult
        """
        endpoint_type = self._get_endpoint_type(request)
        return rate_limiting_service.check_user_rate_limit(user_id, endpoint_type)
    
    def _create_rate_limit_response_from_result(self, result: RateLimitResult) -> JSONResponse:
        """
        Create rate limit response from RateLimitResult.
        
        Args:
            result: RateLimitResult object
            
        Returns:
            JSONResponse with rate limit error
        """
        return self._create_rate_limit_response(
            "Rate limit exceeded",
            status.HTTP_429_TOO_MANY_REQUESTS,
            retry_after=result.retry_after,
            reset_time=result.reset_time.isoformat()
        )
    
    def _create_rate_limit_response(
        self, 
        message: str, 
        status_code: int = 429,
        retry_after: Optional[int] = None,
        reset_time: Optional[str] = None
    ) -> JSONResponse:
        """
        Create standardized rate limit error response.
        
        Args:
            message: Error message
            status_code: HTTP status code
            retry_after: Seconds to wait before retry
            reset_time: When rate limit resets
            
        Returns:
            JSONResponse with rate limit error
        """
        content = {
            "detail": message,
            "code": "RATE_LIMIT_EXCEEDED",
            "retry_after": retry_after,
            "reset_time": reset_time
        }
        
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        if reset_time:
            headers["X-RateLimit-Reset"] = reset_time
        
        return JSONResponse(
            status_code=status_code,
            content=content,
            headers=headers
        )
    
    def _add_rate_limit_headers(self, response: Response, request: Request, client_ip: str):
        """
        Add rate limit headers to response.
        
        Args:
            response: Response object
            request: Request object
            client_ip: Client IP address
        """
        try:
            endpoint_type = self._get_endpoint_type(request)
            
            # Get current rate limit status
            ip_result = rate_limiting_service.check_ip_rate_limit(client_ip, endpoint_type)
            
            # Add headers
            response.headers["X-RateLimit-Limit"] = str(
                rate_limiting_service.get_rate_limit_for_endpoint(endpoint_type).max_requests
            )
            response.headers["X-RateLimit-Remaining"] = str(ip_result.remaining)
            response.headers["X-RateLimit-Reset"] = ip_result.reset_time.isoformat()
            
        except Exception as e:
            logger.error(f"Failed to add rate limit headers: {e}")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding comprehensive security headers.
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
        
        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS header for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Remove server information
        response.headers.pop("Server", None)
        
        return response


# Global middleware instances
rate_limiting_middleware = RateLimitingMiddleware
security_headers_middleware = SecurityHeadersMiddleware