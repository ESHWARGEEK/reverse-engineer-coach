"""
Password hashing service using bcrypt with secure defaults.
Implements password hashing and verification for user authentication.
"""

import bcrypt
from typing import List, Tuple


class PasswordService:
    """Service for secure password hashing and verification using bcrypt."""
    
    # Use 12 rounds as specified in requirements (minimum for security)
    BCRYPT_ROUNDS = 12
    
    @classmethod
    def hash_password(cls, password: str) -> str:
        """
        Hash a password using bcrypt with secure salt rounds.
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Hashed password as string
            
        Raises:
            ValueError: If password is empty or None
        """
        if not password:
            raise ValueError("Password cannot be empty")
            
        # Generate salt and hash password
        salt = bcrypt.gensalt(rounds=cls.BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        return hashed.decode('utf-8')
    
    @classmethod
    def verify_password(cls, password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password to verify
            hashed_password: Previously hashed password
            
        Returns:
            True if password matches hash, False otherwise
        """
        if not password or not hashed_password:
            return False
            
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'), 
                hashed_password.encode('utf-8')
            )
        except (ValueError, TypeError):
            return False
    
    @classmethod
    def validate_password_strength(cls, password: str) -> Tuple[bool, List[str]]:
        """
        Validate password strength according to security requirements.
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if not password:
            errors.append("Password is required")
            return False, errors
            
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
            
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
            
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
            
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")
            
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
            
        return len(errors) == 0, errors