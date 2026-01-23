"""
JWT Token Service for authentication and authorization.
Implements secure JWT token generation, validation, and refresh mechanisms.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.models import User, UserSession
import uuid


class TokenData(BaseModel):
    """Token payload data structure."""
    user_id: str
    email: str
    token_type: str  # "access" or "refresh"
    session_id: Optional[str] = None


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Access token expiration in seconds


class JWTService:
    """Service for JWT token generation, validation, and management."""
    
    def __init__(self):
        """Initialize JWT service with configuration from environment."""
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-jwt-secret-key-change-in-production")
        self.algorithm = "HS256"
        
        # Token expiration times
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))  # 30 minutes
        self.refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))  # 30 days
        
        # Issuer and audience for additional security
        self.issuer = os.getenv("JWT_ISSUER", "reverse-engineer-coach")
        self.audience = os.getenv("JWT_AUDIENCE", "reverse-engineer-coach-users")
    
    def generate_token_pair(self, user: User, db: Session) -> TokenPair:
        """
        Generate access and refresh token pair for a user.
        
        Args:
            user: User object
            db: Database session
            
        Returns:
            TokenPair containing access and refresh tokens
        """
        # Create a new session record
        session_id = str(uuid.uuid4())
        
        # Generate access token
        access_token = self._create_access_token(user, session_id)
        
        # Generate refresh token
        refresh_token = self._create_refresh_token(user, session_id)
        
        # Store session in database
        expires_at = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        session = UserSession(
            id=session_id,
            user_id=user.id,
            token_hash=self._hash_token(refresh_token),
            expires_at=expires_at
        )
        db.add(session)
        db.commit()
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60
        )
    
    def _create_access_token(self, user: User, session_id: str) -> str:
        """Create an access token for the user."""
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": user.id,  # Subject (user ID)
            "email": user.email,
            "token_type": "access",
            "session_id": session_id,
            "iat": now,  # Issued at
            "exp": expire,  # Expiration
            "iss": self.issuer,  # Issuer
            "aud": self.audience,  # Audience
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def _create_refresh_token(self, user: User, session_id: str) -> str:
        """Create a refresh token for the user."""
        now = datetime.utcnow()
        expire = now + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "sub": user.id,  # Subject (user ID)
            "email": user.email,
            "token_type": "refresh",
            "session_id": session_id,
            "iat": now,  # Issued at
            "exp": expire,  # Expiration
            "iss": self.issuer,  # Issuer
            "aud": self.audience,  # Audience
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def validate_access_token(self, token: str) -> Tuple[bool, Optional[TokenData], Optional[str]]:
        """
        Validate an access token.
        
        Args:
            token: JWT access token
            
        Returns:
            Tuple of (is_valid, token_data, error_message)
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer
            )
            
            # Verify token type
            if payload.get("token_type") != "access":
                return False, None, "Invalid token type"
            
            # Extract token data
            token_data = TokenData(
                user_id=payload.get("sub"),
                email=payload.get("email"),
                token_type=payload.get("token_type"),
                session_id=payload.get("session_id")
            )
            
            return True, token_data, None
            
        except JWTError as e:
            return False, None, f"Token validation failed: {str(e)}"
        except Exception as e:
            return False, None, f"Unexpected error: {str(e)}"
    
    def validate_refresh_token(self, token: str, db: Session) -> Tuple[bool, Optional[TokenData], Optional[str]]:
        """
        Validate a refresh token and check if session exists.
        
        Args:
            token: JWT refresh token
            db: Database session
            
        Returns:
            Tuple of (is_valid, token_data, error_message)
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer
            )
            
            # Verify token type
            if payload.get("token_type") != "refresh":
                return False, None, "Invalid token type"
            
            # Check if session exists and is valid
            session_id = payload.get("session_id")
            if not session_id:
                return False, None, "Missing session ID"
            
            session = db.query(UserSession).filter(
                UserSession.id == session_id,
                UserSession.token_hash == self._hash_token(token),
                UserSession.expires_at > datetime.utcnow()
            ).first()
            
            if not session:
                return False, None, "Invalid or expired session"
            
            # Extract token data
            token_data = TokenData(
                user_id=payload.get("sub"),
                email=payload.get("email"),
                token_type=payload.get("token_type"),
                session_id=session_id
            )
            
            return True, token_data, None
            
        except JWTError as e:
            return False, None, f"Token validation failed: {str(e)}"
        except Exception as e:
            return False, None, f"Unexpected error: {str(e)}"
    
    def refresh_access_token(self, refresh_token: str, db: Session) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Generate a new access token using a valid refresh token.
        
        Args:
            refresh_token: Valid refresh token
            db: Database session
            
        Returns:
            Tuple of (success, new_access_token, error_message)
        """
        # Validate refresh token
        is_valid, token_data, error = self.validate_refresh_token(refresh_token, db)
        if not is_valid:
            return False, None, error
        
        # Get user from database
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if not user or not user.is_active:
            return False, None, "User not found or inactive"
        
        # Generate new access token
        new_access_token = self._create_access_token(user, token_data.session_id)
        
        return True, new_access_token, None
    
    def revoke_token(self, token: str, db: Session) -> Tuple[bool, Optional[str]]:
        """
        Revoke a token by removing its session from the database.
        
        Args:
            token: Token to revoke (access or refresh)
            db: Database session
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
                options={"verify_exp": False}  # Allow expired tokens for revocation
            )
            
            session_id = payload.get("session_id")
            if not session_id:
                return False, "Missing session ID"
            
            # Remove session from database
            session = db.query(UserSession).filter(UserSession.id == session_id).first()
            if session:
                db.delete(session)
                db.commit()
            
            return True, None
            
        except JWTError as e:
            return False, f"Token revocation failed: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def revoke_all_user_tokens(self, user_id: str, db: Session) -> Tuple[bool, Optional[str]]:
        """
        Revoke all tokens for a user by removing all their sessions.
        
        Args:
            user_id: User ID
            db: Database session
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Remove all sessions for the user
            db.query(UserSession).filter(UserSession.user_id == user_id).delete()
            db.commit()
            
            return True, None
            
        except Exception as e:
            return False, f"Failed to revoke user tokens: {str(e)}"
    
    def cleanup_expired_sessions(self, db: Session) -> int:
        """
        Clean up expired sessions from the database.
        
        Args:
            db: Database session
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            expired_count = db.query(UserSession).filter(
                UserSession.expires_at < datetime.utcnow()
            ).count()
            
            db.query(UserSession).filter(
                UserSession.expires_at < datetime.utcnow()
            ).delete()
            
            db.commit()
            return expired_count
            
        except Exception:
            db.rollback()
            return 0
    
    def _hash_token(self, token: str) -> str:
        """Create a hash of the token for secure storage."""
        import hashlib
        return hashlib.sha256(token.encode('utf-8')).hexdigest()
    
    def get_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get information from a token without validating expiration.
        Useful for debugging and logging.
        
        Args:
            token: JWT token
            
        Returns:
            Token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": False, "verify_aud": False, "verify_iss": False}
            )
            return payload
        except JWTError:
            return None