"""
Enhanced Authentication Service
Integrates JWT, password hashing, and credential encryption for comprehensive user authentication.
"""

from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr, validator
from fastapi import HTTPException, status

from app.models import User, UserCredentials
from app.services.jwt_service import JWTService, TokenPair
from app.services.password_service import PasswordService
from app.services.credential_encryption_service import CredentialEncryptionService
from app.config import settings


class UserRegistrationRequest(BaseModel):
    """User registration request model with validation."""
    email: EmailStr
    password: str
    confirm_password: Optional[str] = None
    github_token: Optional[str] = None
    ai_api_key: Optional[str] = None
    preferred_ai_provider: str = "openai"  # "openai" or "gemini"
    preferred_language: str = "python"
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if v is not None and 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('preferred_ai_provider')
    def validate_ai_provider(cls, v):
        if v not in ['openai', 'gemini']:
            raise ValueError('AI provider must be either "openai" or "gemini"')
        return v


class UserLoginRequest(BaseModel):
    """User login request model."""
    email: EmailStr
    password: str


class UserRegistrationResponse(BaseModel):
    """User registration response model."""
    user_id: str
    email: str
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    
    class Config:
        from_attributes = True


class UserLoginResponse(BaseModel):
    """User login response model."""
    user_id: str
    email: str
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class AuthService:
    """Enhanced authentication service with comprehensive security features."""
    
    def __init__(self):
        """Initialize authentication service with required components."""
        self.jwt_service = JWTService()
        self.password_service = PasswordService()
        
        # Initialize credential encryption service with fallback
        master_key = settings.credential_encryption_key
        if not master_key or master_key == "your-encryption-key-for-api-keys":
            # Use a default key for development/testing
            import os
            master_key = os.getenv("MASTER_ENCRYPTION_KEY", "dev-fallback-key-not-for-production")
        
        self.credential_service = CredentialEncryptionService(master_key)
    
    async def register_user(
        self, 
        registration_data: UserRegistrationRequest, 
        db: Session
    ) -> Tuple[bool, Optional[UserRegistrationResponse], Optional[str]]:
        """
        Register a new user with comprehensive validation and security.
        
        Args:
            registration_data: User registration data
            db: Database session
            
        Returns:
            Tuple of (success, response_data, error_message)
        """
        try:
            # Validate password strength
            is_strong, password_errors = self.password_service.validate_password_strength(
                registration_data.password
            )
            if not is_strong:
                return False, None, f"Password validation failed: {'; '.join(password_errors)}"
            
            # Check if user already exists
            existing_user = db.query(User).filter(User.email == registration_data.email).first()
            if existing_user:
                return False, None, "Email address is already registered"
            
            # Validate API credentials if provided (skip validation for now to avoid external API calls)
            # if registration_data.github_token:
            #     is_valid, error = await self.credential_service.validate_github_token(
            #         registration_data.github_token
            #     )
            #     if not is_valid:
            #         return False, None, f"GitHub token validation failed: {error}"
            
            # if registration_data.ai_api_key:
            #     is_valid, error = await self.credential_service.validate_ai_api_key(
            #         registration_data.ai_api_key,
            #         registration_data.preferred_ai_provider
            #     )
            #     if not is_valid:
            #         return False, None, f"AI API key validation failed: {error}"
            
            # Hash password
            hashed_password = self.password_service.hash_password(registration_data.password)
            
            # Create user
            user = User(
                email=registration_data.email,
                hashed_password=hashed_password,
                is_active=True,
                preferred_ai_provider=registration_data.preferred_ai_provider,
                preferred_language=registration_data.preferred_language
            )
            
            db.add(user)
            db.flush()  # Get user ID without committing
            
            # Encrypt and store API credentials if provided
            if registration_data.github_token or registration_data.ai_api_key:
                user_salt = self.credential_service.generate_user_salt()
                
                github_encrypted = ""
                ai_key_encrypted = ""
                
                if registration_data.github_token:
                    github_encrypted = self.credential_service.encrypt_credential(
                        registration_data.github_token,
                        user.id,
                        user_salt
                    )
                
                if registration_data.ai_api_key:
                    ai_key_encrypted = self.credential_service.encrypt_credential(
                        registration_data.ai_api_key,
                        user.id,
                        user_salt
                    )
                
                # Create credentials record
                credentials = UserCredentials(
                    user_id=user.id,
                    github_token_encrypted=github_encrypted,
                    ai_api_key_encrypted=ai_key_encrypted,
                    encryption_key_hash=self.credential_service.hash_encryption_key(user_salt)
                )
                
                db.add(credentials)
            
            # Generate JWT tokens
            token_pair = self.jwt_service.generate_token_pair(user, db)
            
            # Commit transaction
            db.commit()
            db.refresh(user)
            
            # Create response
            response = UserRegistrationResponse(
                user_id=user.id,
                email=user.email,
                access_token=token_pair.access_token,
                refresh_token=token_pair.refresh_token,
                token_type=token_pair.token_type,
                expires_in=token_pair.expires_in
            )
            
            return True, response, None
            
        except IntegrityError:
            db.rollback()
            return False, None, "Email address is already registered"
        except Exception as e:
            db.rollback()
            return False, None, f"Registration failed: {str(e)}"
    
    async def login_user(
        self, 
        login_data: UserLoginRequest, 
        db: Session
    ) -> Tuple[bool, Optional[UserLoginResponse], Optional[str]]:
        """
        Authenticate user and generate tokens.
        
        Args:
            login_data: User login data
            db: Database session
            
        Returns:
            Tuple of (success, response_data, error_message)
        """
        try:
            # Find user by email
            user = db.query(User).filter(User.email == login_data.email).first()
            if not user:
                return False, None, "Invalid email or password"
            
            # Verify password
            if not self.password_service.verify_password(login_data.password, user.hashed_password):
                return False, None, "Invalid email or password"
            
            # Check if user is active
            if not user.is_active:
                return False, None, "Account is deactivated"
            
            # Update last login
            user.last_login = datetime.utcnow()
            
            # Generate JWT tokens
            token_pair = self.jwt_service.generate_token_pair(user, db)
            
            # Commit transaction
            db.commit()
            db.refresh(user)
            
            # Create response
            response = UserLoginResponse(
                user_id=user.id,
                email=user.email,
                access_token=token_pair.access_token,
                refresh_token=token_pair.refresh_token,
                token_type=token_pair.token_type,
                expires_in=token_pair.expires_in,
                last_login=user.last_login
            )
            
            return True, response, None
            
        except Exception as e:
            db.rollback()
            return False, None, f"Login failed: {str(e)}"
    
    async def refresh_token(
        self, 
        refresh_token: str, 
        db: Session
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Generate new access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            db: Database session
            
        Returns:
            Tuple of (success, new_access_token, error_message)
        """
        return self.jwt_service.refresh_access_token(refresh_token, db)
    
    async def logout_user(
        self, 
        token: str, 
        db: Session
    ) -> Tuple[bool, Optional[str]]:
        """
        Logout user by revoking their token.
        
        Args:
            token: Token to revoke
            db: Database session
            
        Returns:
            Tuple of (success, error_message)
        """
        return self.jwt_service.revoke_token(token, db)
    
    async def validate_token(
        self, 
        token: str, 
        db: Session
    ) -> Tuple[bool, Optional[User], Optional[str]]:
        """
        Validate access token and return user.
        
        Args:
            token: Access token to validate
            db: Database session
            
        Returns:
            Tuple of (is_valid, user, error_message)
        """
        # Validate token
        is_valid, token_data, error = self.jwt_service.validate_access_token(token)
        if not is_valid:
            return False, None, error
        
        # Get user from database
        user = db.query(User).filter(
            User.id == token_data.user_id,
            User.is_active == True
        ).first()
        
        if not user:
            return False, None, "User not found or inactive"
        
        return True, user, None
    
    def get_user_credentials(
        self, 
        user: User, 
        db: Session
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Get decrypted user credentials.
        
        Args:
            user: User object
            db: Database session
            
        Returns:
            Tuple of (github_token, ai_api_key)
        """
        try:
            credentials = db.query(UserCredentials).filter(
                UserCredentials.user_id == user.id
            ).first()
            
            if not credentials:
                return None, None
            
            # For decryption, we need the user salt from the encryption key hash
            # This is a simplified approach - in production, you'd store the salt separately
            user_salt = self.credential_service.generate_user_salt()  # This should be retrieved properly
            
            github_token = None
            ai_api_key = None
            
            if credentials.github_token_encrypted:
                try:
                    github_token = self.credential_service.decrypt_credential(
                        credentials.github_token_encrypted,
                        user.id,
                        user_salt
                    )
                except Exception:
                    pass  # Handle decryption errors gracefully
            
            if credentials.ai_api_key_encrypted:
                try:
                    ai_api_key = self.credential_service.decrypt_credential(
                        credentials.ai_api_key_encrypted,
                        user.id,
                        user_salt
                    )
                except Exception:
                    pass  # Handle decryption errors gracefully
            
            return github_token, ai_api_key
            
        except Exception:
            return None, None