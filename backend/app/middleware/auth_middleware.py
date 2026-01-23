"""
Authentication middleware for JWT token validation and user context injection.
Provides comprehensive authentication and authorization for protected routes.
"""

from typing import Optional, Callable, List
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models import User
from app.services.auth_service import AuthService

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize auth service
auth_service = AuthService()
security = HTTPBearer(auto_error=False)


class AuthenticationMiddleware:
    """
    Authentication middleware for validating JWT tokens and injecting user context.
    """
    
    def __init__(self):
        """Initialize authentication middleware."""
        self.auth_service = AuthService()
        
        # Routes that don't require authentication
        self.public_routes = {
            "/",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/health",
            "/auth/register",
            "/auth/login",
            "/auth/refresh"
        }
        
        # Routes that require authentication
        self.protected_route_prefixes = [
            "/auth/me",
            "/auth/logout",
            "/projects",
            "/coach",
            "/files",
            "/github"
        ]
    
    def is_protected_route(self, path: str) -> bool:
        """
        Check if a route requires authentication.
        
        Args:
            path: Request path
            
        Returns:
            True if route is protected, False otherwise
        """
        # Check if it's a public route
        if path in self.public_routes:
            return False
        
        # Check if it matches protected route prefixes
        for prefix in self.protected_route_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    async def authenticate_request(
        self, 
        request: Request, 
        db: Session
    ) -> Optional[User]:
        """
        Authenticate request and return user if valid.
        
        Args:
            request: FastAPI request object
            db: Database session
            
        Returns:
            User object if authenticated, None otherwise
            
        Raises:
            HTTPException: If authentication fails on protected route
        """
        path = request.url.path
        
        # Skip authentication for public routes
        if not self.is_protected_route(path):
            return None
        
        # Extract authorization header
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Parse bearer token
        try:
            scheme, token = authorization.split(" ", 1)
            if scheme.lower() != "bearer":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Validate token and get user
        success, user, error = await self.auth_service.validate_token(token, db)
        if not success:
            logger.warning(f"Authentication failed for path {path}: {error}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error,
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user


# Global middleware instance
auth_middleware = AuthenticationMiddleware()


# Dependency functions for FastAPI
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get current authenticated user.
    
    Args:
        credentials: HTTP authorization credentials
        db: Database session
        
    Returns:
        Current authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization credentials missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    success, user, error = await auth_service.validate_token(credentials.credentials, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI dependency to get current active user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    
    return current_user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    FastAPI dependency to get current user if authenticated, None otherwise.
    Useful for endpoints that work with or without authentication.
    
    Args:
        credentials: HTTP authorization credentials (optional)
        db: Database session
        
    Returns:
        Current authenticated user or None
    """
    if not credentials:
        return None
    
    try:
        success, user, _ = await auth_service.validate_token(credentials.credentials, db)
        return user if success else None
    except Exception:
        return None


class RequirePermissions:
    """
    Dependency class for role-based access control.
    Can be extended for more complex permission systems.
    """
    
    def __init__(self, required_permissions: List[str]):
        """
        Initialize permission requirement.
        
        Args:
            required_permissions: List of required permissions
        """
        self.required_permissions = required_permissions
    
    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        """
        Check if user has required permissions.
        
        Args:
            current_user: Current authenticated user
            
        Returns:
            User if authorized
            
        Raises:
            HTTPException: If user lacks required permissions
        """
        # For now, all active users have all permissions
        # This can be extended with a proper role/permission system
        return current_user


# Common permission dependencies
require_authenticated = Depends(get_current_active_user)
require_admin = RequirePermissions(["admin"])


def create_auth_dependency(
    require_active: bool = True,
    required_permissions: Optional[List[str]] = None
) -> Callable:
    """
    Factory function to create custom authentication dependencies.
    
    Args:
        require_active: Whether user must be active
        required_permissions: List of required permissions
        
    Returns:
        FastAPI dependency function
    """
    async def auth_dependency(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)
    ) -> User:
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization credentials missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        success, user, error = await auth_service.validate_token(credentials.credentials, db)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error,
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if require_active and not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user account"
            )
        
        # Check permissions if specified
        if required_permissions:
            # Implement permission checking logic here
            # For now, assume all active users have all permissions
            pass
        
        return user
    
    return auth_dependency


# Error handling for authentication failures
class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    
    def __init__(self, message: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthorizationError(Exception):
    """Custom exception for authorization errors."""
    
    def __init__(self, message: str, status_code: int = status.HTTP_403_FORBIDDEN):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


# Utility functions for manual authentication
async def authenticate_user_from_token(
    token: str, 
    db: Session
) -> tuple[bool, Optional[User], Optional[str]]:
    """
    Manually authenticate user from token.
    
    Args:
        token: JWT token
        db: Database session
        
    Returns:
        Tuple of (success, user, error_message)
    """
    return await auth_service.validate_token(token, db)


async def get_user_from_token(
    token: str, 
    db: Session
) -> Optional[User]:
    """
    Get user from JWT token.
    
    Args:
        token: JWT token
        db: Database session
        
    Returns:
        User object if token is valid, None otherwise
    """
    try:
        success, user, _ = await auth_service.validate_token(token, db)
        return user if success else None
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        return None


async def get_user_from_request(
    request: Request, 
    db: Session
) -> Optional[User]:
    """
    Extract and authenticate user from request.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        User object if authenticated, None otherwise
    """
    try:
        return await auth_middleware.authenticate_request(request, db)
    except HTTPException:
        return None