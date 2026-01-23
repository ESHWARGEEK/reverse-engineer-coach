"""
Credential encryption service using AES-256 encryption.
Implements secure encryption and decryption of API credentials with user-specific keys.
"""

import os
import hashlib
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional, Tuple
import httpx
import asyncio


class CredentialEncryptionService:
    """Service for encrypting and decrypting user API credentials."""
    
    def __init__(self, master_key: str):
        """
        Initialize the encryption service with a master key.
        
        Args:
            master_key: Master encryption key from environment
        """
        self.master_key = master_key.encode('utf-8')
    
    def _derive_user_key(self, user_id: str, user_salt: str) -> bytes:
        """
        Derive a user-specific encryption key from master key and user salt.
        
        Args:
            user_id: User identifier
            user_salt: User-specific salt
            
        Returns:
            Derived encryption key
        """
        # Combine user_id and salt for key derivation
        combined_salt = f"{user_id}:{user_salt}".encode('utf-8')
        
        # Use PBKDF2 to derive key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits for AES-256
            salt=combined_salt,
            iterations=100000,  # High iteration count for security
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        return key
    
    def generate_user_salt(self) -> str:
        """
        Generate a random salt for a user.
        
        Returns:
            Base64-encoded random salt
        """
        salt = os.urandom(32)  # 256 bits of randomness
        return base64.urlsafe_b64encode(salt).decode('utf-8')
    
    def encrypt_credential(self, credential: str, user_id: str, user_salt: str) -> str:
        """
        Encrypt a credential using user-specific encryption key.
        
        Args:
            credential: Plain text credential to encrypt
            user_id: User identifier
            user_salt: User-specific salt
            
        Returns:
            Encrypted credential as base64 string
            
        Raises:
            ValueError: If credential is empty
        """
        if not credential:
            raise ValueError("Credential cannot be empty")
            
        # Derive user-specific key
        key = self._derive_user_key(user_id, user_salt)
        fernet = Fernet(key)
        
        # Encrypt the credential
        encrypted = fernet.encrypt(credential.encode('utf-8'))
        
        return base64.urlsafe_b64encode(encrypted).decode('utf-8')
    
    def decrypt_credential(self, encrypted_credential: str, user_id: str, user_salt: str) -> str:
        """
        Decrypt a credential using user-specific encryption key.
        
        Args:
            encrypted_credential: Base64-encoded encrypted credential
            user_id: User identifier
            user_salt: User-specific salt
            
        Returns:
            Decrypted plain text credential
            
        Raises:
            ValueError: If decryption fails
        """
        if not encrypted_credential:
            raise ValueError("Encrypted credential cannot be empty")
            
        try:
            # Derive user-specific key
            key = self._derive_user_key(user_id, user_salt)
            fernet = Fernet(key)
            
            # Decode and decrypt
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_credential.encode('utf-8'))
            decrypted = fernet.decrypt(encrypted_bytes)
            
            return decrypted.decode('utf-8')
            
        except Exception as e:
            raise ValueError(f"Failed to decrypt credential: {str(e)}")
    
    def hash_encryption_key(self, user_salt: str) -> str:
        """
        Create a hash of the encryption key for storage verification.
        
        Args:
            user_salt: User-specific salt
            
        Returns:
            SHA-256 hash of the encryption key
        """
        key_material = f"{self.master_key.decode('utf-8')}:{user_salt}"
        return hashlib.sha256(key_material.encode('utf-8')).hexdigest()
    
    async def validate_github_token(self, token: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a GitHub token by making a test API call.
        
        Args:
            token: GitHub personal access token
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not token:
            return False, "GitHub token is required"
            
        if not token.startswith(('ghp_', 'github_pat_')):
            return False, "Invalid GitHub token format"
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return True, None
                elif response.status_code == 401:
                    return False, "Invalid or expired GitHub token"
                else:
                    return False, f"GitHub API error: {response.status_code}"
                    
        except httpx.TimeoutException:
            return False, "GitHub API request timed out"
        except Exception as e:
            return False, f"Failed to validate GitHub token: {str(e)}"
    
    async def validate_ai_api_key(self, api_key: str, provider: str = "openai") -> Tuple[bool, Optional[str]]:
        """
        Validate an AI service API key by making a test API call.
        
        Args:
            api_key: AI service API key
            provider: AI provider ("openai" or "gemini")
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not api_key:
            return False, "AI API key is required"
            
        try:
            if provider.lower() == "openai":
                return await self._validate_openai_key(api_key)
            elif provider.lower() == "gemini":
                return await self._validate_gemini_key(api_key)
            else:
                return False, f"Unsupported AI provider: {provider}"
                
        except Exception as e:
            return False, f"Failed to validate AI API key: {str(e)}"
    
    async def _validate_openai_key(self, api_key: str) -> Tuple[bool, Optional[str]]:
        """Validate OpenAI API key."""
        if not api_key.startswith('sk-'):
            return False, "Invalid OpenAI API key format"
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return True, None
                elif response.status_code == 401:
                    return False, "Invalid or expired OpenAI API key"
                else:
                    return False, f"OpenAI API error: {response.status_code}"
                    
        except httpx.TimeoutException:
            return False, "OpenAI API request timed out"
        except Exception as e:
            return False, f"OpenAI API validation failed: {str(e)}"
    
    async def _validate_gemini_key(self, api_key: str) -> Tuple[bool, Optional[str]]:
        """Validate Gemini API key."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://generativelanguage.googleapis.com/v1/models?key={api_key}",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return True, None
                elif response.status_code == 400:
                    return False, "Invalid Gemini API key"
                else:
                    return False, f"Gemini API error: {response.status_code}"
                    
        except httpx.TimeoutException:
            return False, "Gemini API request timed out"
        except Exception as e:
            return False, f"Gemini API validation failed: {str(e)}"