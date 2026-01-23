"""
Enhanced authentication middleware with comprehensive error handling.
Integrates with the error handling service for better user experience.
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
import logging
from typing import Optional, Callable
import time
import uuid

from app.database import get_db
from app.services.jwt_service import jwt_service
from app.services.error_handling_service import (
    error_handling_service, 
    AuthenticationError, 
    AuthorizationError,
    ErrorContext
)
from app.models import User

logger = logging.getLogger(__name__)


class EnhancedAuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Enhanced authentication middleware with comprehensive error handling.
    """
    
    def __init__(self, app, protected_paths: Optional[list] = None):
        super().__init__(app)
        self.protected_paths = protected_paths or [
            "/api/auth/profile",
            "/api/auth/logout", 
            "/api/dashboard",
            "/api/projects",
            "/api/discover",
            "/api/coach",
            "/api/files"
        ]
        self.public_paths = [
            "/api/auth/register",
            "/api/auth/login",
            "/api/auth/refresh",
            "/docs",
            "/openapi.json",
            "/health"
        ]
        self.rate_limit_cache = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """
        Process request through enhanced authentication middleware.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response from next middleware/endpoint or error response
        """
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Create error context
        context = error_handling_service.create_error_context(request)
        context.request_id = request_id
        
        # Initialize request state
        request.state.user = None
        request.state.user_id = None
        request.state.authenticated = False
        request.state.error_context = context
        
        try:
            # Check if path requires authentication
            if not self._requires_authentication(request.url.path):
                return await call_next(request)
            
            # Get database session
            db_gen = get_db()
            db: Session = next(db_gen)
            
            try:
                # Authenticate request
                user = await self._authenticate_request(request, db, context)
                
                if user:
                    # Set authenticated user in request state
                    request.state.user = user
                    request.state.user_id = user.id
                    request.state.authenticated = True
                    context.user_id = user.id
                    
                    # Check rate limiting for authenticated users
                    await self._check_user_rate_limit(user.id, context)
                    
                    # Log successful authentication
                    logger.info(
                        f"User authenticated successfully: {user.id}",
                        extra={
                            "user_id": user.id,
                            "request_id": request_id,
                            "endpoint": request.url.path,
                            "method": request.method
                        }
                    )
                else:
                    # Authentication failed
                    raise await error_handling_service.handle_authentication_error(
                        "AUTHENTICATION_REQUIRED", context
                    )
                
                # Continue to next middleware/endpoint
                response = await call_next(request)
                return response
                
            finally:
                # Clean up database session
                try:
                    db.close()
                except Exception:
                    pass
        
        except AuthenticationError as e:
            # Handle authentication errors with recovery strategies
            return await self._handle_authentication_error(request, e, context)
        
        except AuthorizationError as e:
            # Handle authorization errors
            return await self._handle_authorization_error(request, e, context)
        
        except Exception as e:
            # Handle unexpected errors
            logger.error(
                f"Unexpected error in authentication middleware: {str(e)}",
                extra={
                    "request_id": request_id,
                    "endpoint": request.url.path,
                    "method": request.method,
                    "error": str(e)
                }
            )
            
            # Convert to authentication error
            auth_error = await error_handling_service.handle_authentication_error(
                "AUTHENTICATION_ERROR", context, e
            )
            return await self._handle_authentication_error(request, auth_error, context)
    
    def _requires_authentication(self, path: str) -> bool:
        """
        Check if the given path requires authentication.
        
        Args:
            path: Request path
            
        Returns:
            True if authentication is required, False otherwise
        """
        # Check public paths first
        for public_path in self.public_paths:
            if path.startswith(public_path):
                return False
        
        # Check protected paths
        for protected_path in self.protected_paths:
            if path.startswith(protected_path):
                return True
        
        # Default to requiring authentication for API endpoints
        return path.startswith("/api/")
    
    async def _authenticate_request(
        self, 
        request: Request, 
        db: Session, 
        context: ErrorContext
    ) -> Optional[User]:
        """
        Authenticate the request using JWT token.
        
        Args:
            request: FastAPI request object
            db: Database session
            context: Error context
            
        Returns:
            Authenticated user or None
            
        Raises:
            AuthenticationError: If authentication fails
        """
        # Get authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise await error_handling_service.handle_authentication_error(
                "MISSING_TOKEN", context
            )
        
        # Extract token from header
        if not auth_header.startswith("Bearer "):
            raise await error_handling_service.handle_authentication_error(
                "INVALID_TOKEN_FORMAT", context
            )
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        try:
            # Validate and decode token
            payload = jwt_service.decode_token(token)
            user_id = payload.get("sub")
            
            if not user_id:
                raise await error_handling_service.handle_authentication_error(
                    "INVALID_TOKEN", context
                )
            
            # Get user from database
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise await error_handling_service.handle_authentication_error(
                    "USER_NOT_FOUND", context
                )
            
            # Check if user account is active
            if not getattr(user, 'is_active', True):
                raise await error_handling_service.handle_authentication_error(
                    "ACCOUNT_DISABLED", context
                )
            
            return user
            
        except jwt_service.InvalidTokenError:
            raise await error_handling_service.handle_authentication_error(
                "INVALID_TOKEN", context
            )
        except jwt_service.ExpiredTokenError:
            raise await error_handling_service.handle_authentication_error(
                "EXPIRED_TOKEN", context
            )
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            raise await error_handling_service.handle_authentication_error(
                "TOKEN_VALIDATION_ERROR", context, e
            )
    
    async def _check_user_rate_limit(self, user_id: str, context: ErrorContext) -> None:
        """
        Check rate limiting for authenticated users.
        
        Args:
            user_id: User ID
            context: Error context
            
        Raises:
            AuthenticationError: If rate limit is exceeded
        """
        current_time = time.time()
        window_size = 3600  # 1 hour window
        max_requests = 1000  # Max requests per hour per user
        
        # Clean old entries
        cutoff_time = current_time - window_size
        if user_id in self.rate_limit_cache:
            self.rate_limit_cache[user_id] = [
                timestamp for timestamp in self.rate_limit_cache[user_id]
                if timestamp > cutoff_time
            ]
        else:
            self.rate_limit_cache[user_id] = []
        
        # Check current request count
        request_count = len(self.rate_limit_cache[user_id])
        
        if request_count >= max_requests:
            logger.warning(
                f"Rate limit exceeded for user {user_id}: {request_count} requests in last hour",
                extra={
                    "user_id": user_id,
                    "request_count": request_count,
                    "window_size": window_size,
                    "max_requests": max_requests
                }
            )
            
            raise await error_handling_service.handle_authentication_error(
                "RATE_LIMIT_EXCEEDED", context
            )
        
        # Add current request
        self.rate_limit_cache[user_id].append(current_time)
    
    async def _handle_authentication_error(
        self, 
        request: Request, 
        error: AuthenticationError, 
        context: ErrorContext
    ) -> JSONResponse:
        """
        Handle authentication errors with recovery strategies.
        
        Args:
            request: FastAPI request object
            error: Authentication error
            context: Error context
            
        Returns:
            JSON error response
        """
        # Log authentication failure
        logger.warning(
            f"Authentication failed: {error.error_type}",
            extra={
                "error_type": error.error_type,
                "request_id": context.request_id,
                "endpoint": context.endpoint,
                "method": context.method,
                "ip_address": context.ip_address,
                "user_agent": context.user_agent
            }
        )
        
        # Create response data
        response_data = {
            "error": {
                "message": error.message,
                "code": error.error_code,
                "category": "authentication",
                "timestamp": context.timestamp.isoformat(),
                "request_id": context.request_id
            }
        }
        
        # Add recovery information if available
        if error.recovery_strategy:
            response_data["error"]["recovery"] = {
                "strategy": error.recovery_strategy.strategy_type,
                "user_message": error.recovery_strategy.user_message,
                "actions": error.recovery_strategy.recovery_actions,
                "retry_enabled": error.recovery_strategy.retry_enabled,
                "retry_delay": error.recovery_strategy.retry_delay if error.recovery_strategy.retry_enabled else None
            }
        
        # Add appropriate headers
        headers = {}
        if error.error_type == "EXPIRED_TOKEN":
            headers["X-Token-Expired"] = "true"
        elif error.error_type == "RATE_LIMIT_EXCEEDED":
            headers["Retry-After"] = "3600"  # 1 hour
        
        return JSONResponse(
            status_code=error.status_code,
            content=response_data,
            headers=headers
        )
    
    async def _handle_authorization_error(
        self, 
        request: Request, 
        error: AuthorizationError, 
        context: ErrorContext
    ) -> JSONResponse:
        """
        Handle authorization errors.
        
        Args:
            request: FastAPI request object
            error: Authorization error
            context: Error context
            
        Returns:
            JSON error response
        """
        # Log authorization failure
        logger.warning(
            f"Authorization failed: {error.message}",
            extra={
                "required_permission": error.required_permission,
                "request_id": context.request_id,
                "endpoint": context.endpoint,
                "method": context.method,
                "user_id": context.user_id
            }
        )
        
        response_data = {
            "error": {
                "message": error.message,
                "code": error.error_code,
                "category": "authorization",
                "timestamp": context.timestamp.isoformat(),
                "request_id": context.request_id
            }
        }
        
        if error.required_permission:
            response_data["error"]["required_permission"] = error.required_permission
        
        return JSONResponse(
            status_code=error.status_code,
            content=response_data
        )


# Enhanced authentication dependency for FastAPI endpoints
async def get_current_user_enhanced(request: Request) -> User:
    """
    Enhanced dependency to get current authenticated user with error handling.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Current authenticated user
        
    Raises:
        AuthenticationError: If user is not authenticated
    """
    user = getattr(request.state, 'user', None)
    if not user:
        context = getattr(request.state, 'error_context', None)
        if not context:
            context = error_handling_service.create_error_context(request)
        
        raise await error_handling_service.handle_authentication_error(
            "AUTHENTICATION_REQUIRED", context
        )
    
    return user


async def require_permission(permission: str):
    """
    Dependency factory to require specific permissions.
    
    Args:
        permission: Required permission
        
    Returns:
        Dependency function
    """
    async def permission_dependency(request: Request) -> User:
        user = await get_current_user_enhanced(request)
        
        # Check if user has required permission
        # This is a placeholder - implement based on your permission system
        user_permissions = getattr(user, 'permissions', [])
        
        if permission not in user_permissions and not getattr(user, 'is_admin', False):
            context = getattr(request.state, 'error_context', None)
            if not context:
                context = error_handling_service.create_error_context(request)
            
            raise AuthorizationError(
                message=f"Permission '{permission}' is required for this action",
                required_permission=permission,
                context=context
            )
        
        return user
    
    return permission_dependency