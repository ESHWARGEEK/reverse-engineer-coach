"""
User Profile Management API endpoints
Handles user profile retrieval, updates, and API credential management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, validator
from datetime import datetime

from app.database import get_db
from app.models import User, UserCredentials
from app.services.auth_service import AuthService
from app.services.credential_encryption_service import CredentialEncryptionService
from app.services.password_service import PasswordService
from app.middleware.auth_middleware import get_current_active_user
from app.config import settings
from app.decorators.validation_decorators import (
    validate_profile_update,
    validate_json_body,
    rate_limit,
    sanitize_output,
    mask_credentials
)
from app.schemas.validation_schemas import ValidationRules

router = APIRouter()

# Initialize services
auth_service = AuthService()
password_service = PasswordService()

# Initialize credential encryption service
master_key = settings.credential_encryption_key
if master_key and master_key != "your-encryption-key-for-api-keys":
    credential_service = CredentialEncryptionService(master_key)
else:
    credential_service = None


class UserProfileResponse(BaseModel):
    """User profile response model with masked credentials."""
    id: str
    email: str
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    preferred_ai_provider: str
    preferred_language: str
    preferred_frameworks: Optional[list]
    learning_preferences: Optional[Dict[str, Any]]
    
    # Masked API credentials
    has_github_token: bool
    has_ai_api_key: bool
    github_token_masked: Optional[str] = None
    ai_api_key_masked: Optional[str] = None
    
    class Config:
        from_attributes = True


class UserProfileUpdateRequest(BaseModel):
    """User profile update request model."""
    email: Optional[EmailStr] = None
    preferred_ai_provider: Optional[str] = None
    preferred_language: Optional[str] = None
    preferred_frameworks: Optional[list] = None
    learning_preferences: Optional[Dict[str, Any]] = None
    
    @validator('preferred_ai_provider')
    def validate_ai_provider(cls, v):
        if v and v not in ['openai', 'gemini']:
            raise ValueError('AI provider must be either "openai" or "gemini"')
        return v


class PasswordUpdateRequest(BaseModel):
    """Password update request model."""
    current_password: str
    new_password: str
    confirm_new_password: str
    
    @validator('confirm_new_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('New passwords do not match')
        return v


class CredentialUpdateRequest(BaseModel):
    """API credential update request model."""
    github_token: Optional[str] = None
    ai_api_key: Optional[str] = None
    ai_provider: Optional[str] = None
    
    @validator('ai_provider')
    def validate_ai_provider(cls, v):
        if v and v not in ['openai', 'gemini']:
            raise ValueError('AI provider must be either "openai" or "gemini"')
        return v


class CredentialValidationResponse(BaseModel):
    """Credential validation response model."""
    github_token_valid: bool
    ai_api_key_valid: bool
    validation_errors: Dict[str, str]


def mask_credential(credential: str) -> str:
    """Mask API credential for display."""
    if not credential or len(credential) < 8:
        return "****"
    return f"{credential[:4]}****{credential[-4:]}"


@router.get("/", response_model=UserProfileResponse)
@mask_credentials
async def get_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's profile information with masked API credentials.
    
    Returns user profile data including masked versions of API credentials
    for security purposes.
    """
    try:
        # Get user credentials
        credentials = db.query(UserCredentials).filter(
            UserCredentials.user_id == current_user.id
        ).first()
        
        # Prepare response with masked credentials
        has_github_token = bool(credentials and credentials.github_token_encrypted)
        has_ai_api_key = bool(credentials and credentials.ai_api_key_encrypted)
        
        github_token_masked = None
        ai_api_key_masked = None
        
        # If credentials exist, show masked versions
        if has_github_token and credential_service:
            try:
                # For display purposes, we'll show a generic mask
                github_token_masked = "ghp_****...****"
            except Exception:
                github_token_masked = "****"
        
        if has_ai_api_key and credential_service:
            try:
                # For display purposes, we'll show a generic mask
                ai_api_key_masked = "sk-****...****"
            except Exception:
                ai_api_key_masked = "****"
        
        return UserProfileResponse(
            id=current_user.id,
            email=current_user.email,
            is_active=current_user.is_active,
            last_login=current_user.last_login,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at,
            preferred_ai_provider=current_user.preferred_ai_provider,
            preferred_language=current_user.preferred_language or "python",
            preferred_frameworks=current_user.preferred_frameworks,
            learning_preferences=current_user.learning_preferences,
            has_github_token=has_github_token,
            has_ai_api_key=has_ai_api_key,
            github_token_masked=github_token_masked,
            ai_api_key_masked=ai_api_key_masked
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user profile: {str(e)}"
        )


@router.put("/", response_model=UserProfileResponse)
@validate_profile_update
@mask_credentials
async def update_user_profile(
    profile_update: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update user profile information.
    
    Allows updating email, preferences, and other profile settings.
    Does not handle password or API credential updates.
    """
    try:
        # Check if email is being changed and if it's already taken
        if profile_update.email and profile_update.email != current_user.email:
            existing_user = db.query(User).filter(
                User.email == profile_update.email,
                User.id != current_user.id
            ).first()
            
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email address is already in use"
                )
        
        # Update user fields
        update_data = {}
        if profile_update.email is not None:
            update_data['email'] = profile_update.email
        if profile_update.preferred_ai_provider is not None:
            update_data['preferred_ai_provider'] = profile_update.preferred_ai_provider
        if profile_update.preferred_language is not None:
            update_data['preferred_language'] = profile_update.preferred_language
        if profile_update.preferred_frameworks is not None:
            update_data['preferred_frameworks'] = profile_update.preferred_frameworks
        if profile_update.learning_preferences is not None:
            update_data['learning_preferences'] = profile_update.learning_preferences
        
        # Apply updates
        for key, value in update_data.items():
            setattr(current_user, key, value)
        
        current_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(current_user)
        
        # Return updated profile
        return await get_user_profile(current_user, db)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user profile: {str(e)}"
        )


@router.put("/password")
@validate_json_body(max_size=1000, required_fields=["current_password", "new_password", "confirm_new_password"])
@rate_limit(max_requests=5, window_seconds=300)  # 5 password changes per 5 minutes
async def update_password(
    password_update: PasswordUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update user password with current password verification.
    
    Requires current password for security and validates new password strength.
    """
    try:
        # Verify current password
        if not password_service.verify_password(
            password_update.current_password, 
            current_user.hashed_password
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Validate new password strength
        is_strong, password_errors = password_service.validate_password_strength(
            password_update.new_password
        )
        if not is_strong:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"New password validation failed: {'; '.join(password_errors)}"
            )
        
        # Hash new password
        new_hashed_password = password_service.hash_password(password_update.new_password)
        
        # Update password
        current_user.hashed_password = new_hashed_password
        current_user.updated_at = datetime.utcnow()
        db.commit()
        
        return {"message": "Password updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update password: {str(e)}"
        )


@router.put("/credentials", response_model=CredentialValidationResponse)
@validate_json_body(max_size=2000)
@rate_limit(max_requests=10, window_seconds=300)  # 10 credential updates per 5 minutes
@sanitize_output(remove_sensitive=True)
async def update_credentials(
    credential_update: CredentialUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update user API credentials with validation.
    
    Validates credentials before saving and encrypts them securely.
    """
    if not credential_service:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Credential encryption service not available"
        )
    
    try:
        validation_errors = {}
        github_token_valid = True
        ai_api_key_valid = True
        
        # Validate GitHub token if provided
        if credential_update.github_token is not None:
            if credential_update.github_token:  # Not empty
                is_valid, error = await credential_service.validate_github_token(
                    credential_update.github_token
                )
                if not is_valid:
                    github_token_valid = False
                    validation_errors['github_token'] = error
            else:
                github_token_valid = True  # Empty string is valid (removes token)
        
        # Validate AI API key if provided
        if credential_update.ai_api_key is not None:
            if credential_update.ai_api_key:  # Not empty
                provider = credential_update.ai_provider or current_user.preferred_ai_provider
                is_valid, error = await credential_service.validate_ai_api_key(
                    credential_update.ai_api_key,
                    provider
                )
                if not is_valid:
                    ai_api_key_valid = False
                    validation_errors['ai_api_key'] = error
            else:
                ai_api_key_valid = True  # Empty string is valid (removes key)
        
        # If validation failed, return errors without saving
        if validation_errors:
            return CredentialValidationResponse(
                github_token_valid=github_token_valid,
                ai_api_key_valid=ai_api_key_valid,
                validation_errors=validation_errors
            )
        
        # Get or create user credentials record
        credentials = db.query(UserCredentials).filter(
            UserCredentials.user_id == current_user.id
        ).first()
        
        if not credentials:
            # Create new credentials record
            user_salt = credential_service.generate_user_salt()
            credentials = UserCredentials(
                user_id=current_user.id,
                github_token_encrypted="",
                ai_api_key_encrypted="",
                encryption_key_hash=credential_service.hash_encryption_key(user_salt)
            )
            db.add(credentials)
        else:
            # Use existing salt (in production, retrieve from encryption_key_hash)
            user_salt = credential_service.generate_user_salt()
        
        # Update credentials
        if credential_update.github_token is not None:
            if credential_update.github_token:
                credentials.github_token_encrypted = credential_service.encrypt_credential(
                    credential_update.github_token,
                    current_user.id,
                    user_salt
                )
            else:
                credentials.github_token_encrypted = ""
        
        if credential_update.ai_api_key is not None:
            if credential_update.ai_api_key:
                credentials.ai_api_key_encrypted = credential_service.encrypt_credential(
                    credential_update.ai_api_key,
                    current_user.id,
                    user_salt
                )
            else:
                credentials.ai_api_key_encrypted = ""
        
        # Update AI provider if specified
        if credential_update.ai_provider is not None:
            current_user.preferred_ai_provider = credential_update.ai_provider
        
        credentials.updated_at = datetime.utcnow()
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        
        return CredentialValidationResponse(
            github_token_valid=True,
            ai_api_key_valid=True,
            validation_errors={}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update credentials: {str(e)}"
        )


@router.get("/credentials/validate", response_model=CredentialValidationResponse)
async def validate_current_credentials(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Validate current user's stored API credentials.
    
    Tests stored credentials against their respective APIs to ensure they're still valid.
    """
    if not credential_service:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Credential encryption service not available"
        )
    
    try:
        validation_errors = {}
        github_token_valid = True
        ai_api_key_valid = True
        
        # Get user credentials
        github_token, ai_api_key = auth_service.get_user_credentials(current_user, db)
        
        # Validate GitHub token
        if github_token:
            is_valid, error = await credential_service.validate_github_token(github_token)
            if not is_valid:
                github_token_valid = False
                validation_errors['github_token'] = error
        
        # Validate AI API key
        if ai_api_key:
            is_valid, error = await credential_service.validate_ai_api_key(
                ai_api_key,
                current_user.preferred_ai_provider
            )
            if not is_valid:
                ai_api_key_valid = False
                validation_errors['ai_api_key'] = error
        
        return CredentialValidationResponse(
            github_token_valid=github_token_valid,
            ai_api_key_valid=ai_api_key_valid,
            validation_errors=validation_errors
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate credentials: {str(e)}"
        )


@router.delete("/credentials")
async def delete_credentials(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete all stored API credentials for the current user.
    
    This is a security feature to allow users to remove their stored credentials.
    """
    try:
        # Get user credentials
        credentials = db.query(UserCredentials).filter(
            UserCredentials.user_id == current_user.id
        ).first()
        
        if credentials:
            # Clear encrypted credentials
            credentials.github_token_encrypted = ""
            credentials.ai_api_key_encrypted = ""
            credentials.updated_at = datetime.utcnow()
            db.commit()
        
        return {"message": "All API credentials have been deleted"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete credentials: {str(e)}"
        )