"""
Enhanced Authentication API endpoints with JWT tokens and comprehensive security
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from typing import Optional
import time
from collections import defaultdict

from app.database import get_db
from app.models import User
from app.services.auth_service import (
    AuthService, 
    UserRegistrationRequest, 
    UserLoginRequest,
    UserRegistrationResponse,
    UserLoginResponse
)
from app.auth import (
    UserResponse, UserUpdate,
    get_current_active_user, encrypt_api_key, decrypt_api_key
)
from app.decorators.validation_decorators import (
    validate_auth_registration,
    validate_auth_login,
    validate_json_body,
    rate_limit,
    sanitize_output,
    mask_credentials
)
from app.schemas.validation_schemas import ValidationRules

router = APIRouter()
security = HTTPBearer()

# Initialize auth service
auth_service = AuthService()

# Rate limiting storage (in production, use Redis)
rate_limit_storage = defaultdict(list)
RATE_LIMIT_ATTEMPTS = 10  # Max attempts
RATE_LIMIT_WINDOW = 300  # 5 minutes in seconds


class TokenRefreshRequest(BaseModel):
    """Token refresh request model."""
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """Token refresh response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


def check_rate_limit(request: Request, max_attempts: int = RATE_LIMIT_ATTEMPTS) -> bool:
    """
    Check if request is within rate limit.
    
    Args:
        request: FastAPI request object
        max_attempts: Maximum attempts allowed
        
    Returns:
        True if within limit, False otherwise
    """
    client_ip = request.client.host
    current_time = time.time()
    
    # Clean old attempts
    rate_limit_storage[client_ip] = [
        attempt_time for attempt_time in rate_limit_storage[client_ip]
        if current_time - attempt_time < RATE_LIMIT_WINDOW
    ]
    
    # Check if over limit
    if len(rate_limit_storage[client_ip]) >= max_attempts:
        return False
    
    # Record this attempt
    rate_limit_storage[client_ip].append(current_time)
    return True


@router.post("/register", response_model=UserRegistrationResponse)
@validate_auth_registration
@rate_limit(max_requests=10, window_seconds=3600)  # 10 registrations per hour
async def register_user(
    user_data: UserRegistrationRequest, 
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new user with comprehensive validation and security.
    
    - Validates email format and password strength
    - Encrypts and stores API credentials securely
    - Returns JWT tokens upon successful registration
    - Implements rate limiting to prevent abuse
    """
    
    # Check rate limit
    if not check_rate_limit(request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please try again later."
        )
    
    # Register user using auth service
    success, response, error = await auth_service.register_user(user_data, db)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return response


@router.post("/login", response_model=UserLoginResponse)
@validate_auth_login
@rate_limit(max_requests=15, window_seconds=300)  # 15 login attempts per 5 minutes
async def login_user(
    user_data: UserLoginRequest, 
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Login user with credential verification and JWT token generation.
    
    - Verifies email and password
    - Updates last login timestamp
    - Returns JWT access and refresh tokens
    - Implements rate limiting to prevent brute force attacks
    """
    
    # Check rate limit
    if not check_rate_limit(request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )
    
    # Login user using auth service
    success, response, error = await auth_service.login_user(user_data, db)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return response


@router.post("/refresh", response_model=TokenRefreshResponse)
@validate_json_body(max_size=1000, required_fields=["refresh_token"])
@rate_limit(max_requests=10, window_seconds=60)  # 10 refresh attempts per minute
async def refresh_token(
    token_data: TokenRefreshRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using a valid refresh token.
    
    - Validates refresh token
    - Generates new access token
    - Maintains session continuity
    """
    
    success, new_access_token, error = await auth_service.refresh_token(
        token_data.refresh_token, db
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return TokenRefreshResponse(
        access_token=new_access_token,
        expires_in=auth_service.jwt_service.access_token_expire_minutes * 60
    )


@router.post("/logout")
async def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Logout user by revoking their token session.
    
    - Revokes current token session
    - Invalidates both access and refresh tokens
    - Cleans up session data
    """
    
    success, error = await auth_service.logout_user(credentials.credentials, db)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "Successfully logged out"}


# Enhanced current user dependency
async def get_current_user_enhanced(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Enhanced dependency to get current authenticated user using JWT validation.
    """
    
    success, user, error = await auth_service.validate_token(credentials.credentials, db)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


@router.get("/me", response_model=UserResponse)
@mask_credentials
async def get_current_user_info(current_user: User = Depends(get_current_user_enhanced)):
    """Get current user information using enhanced authentication"""
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
@validate_json_body(max_size=5000)
@mask_credentials
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user_enhanced),
    db: Session = Depends(get_db)
):
    """Update current user information using enhanced authentication"""
    
    # Validate API keys if changing provider
    if user_update.preferred_ai_provider:
        if user_update.preferred_ai_provider == "openai" and not (user_update.openai_api_key or current_user.openai_api_key):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OpenAI API key is required when OpenAI is selected as preferred provider"
            )
        
        if user_update.preferred_ai_provider == "gemini" and not (user_update.gemini_api_key or current_user.gemini_api_key):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gemini API key is required when Gemini is selected as preferred provider"
            )
    
    # Update user fields
    if user_update.github_token is not None:
        current_user.github_token = encrypt_api_key(user_update.github_token) if user_update.github_token else None
    
    if user_update.openai_api_key is not None:
        current_user.openai_api_key = encrypt_api_key(user_update.openai_api_key) if user_update.openai_api_key else None
    
    if user_update.gemini_api_key is not None:
        current_user.gemini_api_key = encrypt_api_key(user_update.gemini_api_key) if user_update.gemini_api_key else None
    
    if user_update.preferred_ai_provider is not None:
        current_user.preferred_ai_provider = user_update.preferred_ai_provider
    
    if user_update.preferred_language is not None:
        current_user.preferred_language = user_update.preferred_language
    
    if user_update.preferred_frameworks is not None:
        current_user.preferred_frameworks = user_update.preferred_frameworks
    
    db.commit()
    db.refresh(current_user)
    
    return UserResponse.from_orm(current_user)


@router.get("/api-keys/test")
async def test_api_keys(current_user: User = Depends(get_current_user_enhanced)):
    """Test if user's API keys are valid using enhanced authentication"""
    
    results = {
        "github_token": bool(current_user.github_token),
        "openai_api_key": bool(current_user.openai_api_key),
        "gemini_api_key": bool(current_user.gemini_api_key),
        "preferred_provider": current_user.preferred_ai_provider
    }
    
    # TODO: Add actual API key validation logic here
    # For now, just return whether keys exist
    
    return results


@router.post("/debug/reset-rate-limits")
async def reset_rate_limits(request: Request):
    """Reset rate limits for testing purposes (development only)"""
    
    # Only allow in development environment
    from app.config import settings
    if settings.environment != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Rate limit reset only available in development mode"
        )
    
    client_ip = request.client.host
    rate_limit_storage[client_ip] = []
    
    return {"message": f"Rate limits reset for IP: {client_ip}"}