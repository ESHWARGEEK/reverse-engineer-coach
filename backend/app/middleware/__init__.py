"""
Middleware package for FastAPI application.
Contains authentication, logging, and other middleware components.
"""

from .auth_middleware import (
    AuthenticationMiddleware,
    auth_middleware,
    get_current_user,
    get_current_active_user,
    get_optional_user,
    RequirePermissions,
    require_authenticated,
    require_admin,
    create_auth_dependency,
    AuthenticationError,
    AuthorizationError,
    authenticate_user_from_token,
    get_user_from_request
)

__all__ = [
    "AuthenticationMiddleware",
    "auth_middleware", 
    "get_current_user",
    "get_current_active_user",
    "get_optional_user",
    "RequirePermissions",
    "require_authenticated",
    "require_admin",
    "create_auth_dependency",
    "AuthenticationError",
    "AuthorizationError",
    "authenticate_user_from_token",
    "get_user_from_request"
]