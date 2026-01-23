"""
Comprehensive tests for authentication services: password hashing, credential encryption, JWT tokens, and auth service.
"""

import pytest
import asyncio
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.password_service import PasswordService
from app.services.credential_encryption_service import CredentialEncryptionService
from app.services.jwt_service import JWTService, TokenData, TokenPair
from app.services.auth_service import AuthService, UserRegistrationRequest, UserLoginRequest
from app.models import User, UserCredentials, UserSession, Base


class TestPasswordService:
    """Test password hashing and verification."""
    
    def test_hash_password_success(self):
        """Test successful password hashing."""
        password = "TestPassword123!"
        hashed = PasswordService.hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are typically 60 characters
        assert hashed.startswith('$2b$')  # bcrypt format
    
    def test_hash_password_empty_raises_error(self):
        """Test that empty password raises ValueError."""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            PasswordService.hash_password("")
        
        with pytest.raises(ValueError, match="Password cannot be empty"):
            PasswordService.hash_password(None)
    
    def test_hash_password_different_each_time(self):
        """Test that same password produces different hashes (due to salt)."""
        password = "TestPassword123!"
        hash1 = PasswordService.hash_password(password)
        hash2 = PasswordService.hash_password(password)
        
        assert hash1 != hash2  # Different salts should produce different hashes
        assert PasswordService.verify_password(password, hash1)
        assert PasswordService.verify_password(password, hash2)
    
    def test_verify_password_success(self):
        """Test successful password verification."""
        password = "TestPassword123!"
        hashed = PasswordService.hash_password(password)
        
        assert PasswordService.verify_password(password, hashed) is True
    
    def test_verify_password_wrong_password(self):
        """Test password verification with wrong password."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = PasswordService.hash_password(password)
        
        assert PasswordService.verify_password(wrong_password, hashed) is False
    
    def test_verify_password_empty_inputs(self):
        """Test password verification with empty inputs."""
        assert PasswordService.verify_password("", "hash") is False
        assert PasswordService.verify_password("password", "") is False
        assert PasswordService.verify_password("", "") is False
        assert PasswordService.verify_password(None, "hash") is False
        assert PasswordService.verify_password("password", None) is False
    
    def test_verify_password_invalid_hash_format(self):
        """Test password verification with invalid hash format."""
        password = "TestPassword123!"
        invalid_hash = "not-a-valid-bcrypt-hash"
        
        assert PasswordService.verify_password(password, invalid_hash) is False
    
    def test_validate_password_strength_valid(self):
        """Test password strength validation with valid password."""
        password = "TestPassword123!"
        is_valid, errors = PasswordService.validate_password_strength(password)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_password_strength_invalid_length(self):
        """Test password strength validation with short password."""
        password = "Weak1!"
        is_valid, errors = PasswordService.validate_password_strength(password)
        
        assert is_valid is False
        assert any("at least 8 characters" in error for error in errors)
    
    def test_validate_password_strength_missing_uppercase(self):
        """Test password strength validation without uppercase."""
        password = "testpassword123!"
        is_valid, errors = PasswordService.validate_password_strength(password)
        
        assert is_valid is False
        assert any("uppercase letter" in error for error in errors)
    
    def test_validate_password_strength_missing_lowercase(self):
        """Test password strength validation without lowercase."""
        password = "TESTPASSWORD123!"
        is_valid, errors = PasswordService.validate_password_strength(password)
        
        assert is_valid is False
        assert any("lowercase letter" in error for error in errors)
    
    def test_validate_password_strength_missing_number(self):
        """Test password strength validation without number."""
        password = "TestPassword!"
        is_valid, errors = PasswordService.validate_password_strength(password)
        
        assert is_valid is False
        assert any("number" in error for error in errors)
    
    def test_validate_password_strength_missing_special(self):
        """Test password strength validation without special character."""
        password = "TestPassword123"
        is_valid, errors = PasswordService.validate_password_strength(password)
        
        assert is_valid is False
        assert any("special character" in error for error in errors)
    
    def test_validate_password_strength_empty(self):
        """Test password strength validation with empty password."""
        is_valid, errors = PasswordService.validate_password_strength("")
        
        assert is_valid is False
        assert any("required" in error for error in errors)
    
    def test_bcrypt_rounds_security(self):
        """Test that bcrypt uses secure number of rounds."""
        assert PasswordService.BCRYPT_ROUNDS >= 12  # Security requirement


class TestCredentialEncryptionService:
    """Test credential encryption and decryption."""
    
    @pytest.fixture
    def encryption_service(self):
        """Create encryption service with test master key."""
        return CredentialEncryptionService("test-master-key-for-testing-32-chars")
    
    def test_generate_user_salt(self, encryption_service):
        """Test user salt generation."""
        salt1 = encryption_service.generate_user_salt()
        salt2 = encryption_service.generate_user_salt()
        
        assert salt1 != salt2  # Should be random
        assert len(salt1) > 20  # Should be reasonably long
        assert isinstance(salt1, str)  # Should be string
    
    def test_encrypt_decrypt_credential(self, encryption_service):
        """Test credential encryption and decryption."""
        credential = "sk-test-api-key-12345"
        user_id = "test-user-123"
        user_salt = encryption_service.generate_user_salt()
        
        # Encrypt
        encrypted = encryption_service.encrypt_credential(credential, user_id, user_salt)
        assert encrypted != credential
        assert len(encrypted) > 20
        assert isinstance(encrypted, str)
        
        # Decrypt
        decrypted = encryption_service.decrypt_credential(encrypted, user_id, user_salt)
        assert decrypted == credential
    
    def test_encrypt_decrypt_different_users(self, encryption_service):
        """Test that different users produce different encrypted values."""
        credential = "sk-test-api-key-12345"
        user_id1 = "test-user-123"
        user_id2 = "test-user-456"
        user_salt = encryption_service.generate_user_salt()
        
        encrypted1 = encryption_service.encrypt_credential(credential, user_id1, user_salt)
        encrypted2 = encryption_service.encrypt_credential(credential, user_id2, user_salt)
        
        assert encrypted1 != encrypted2  # Different users should produce different encrypted values
    
    def test_encrypt_decrypt_different_salts(self, encryption_service):
        """Test that different salts produce different encrypted values."""
        credential = "sk-test-api-key-12345"
        user_id = "test-user-123"
        salt1 = encryption_service.generate_user_salt()
        salt2 = encryption_service.generate_user_salt()
        
        encrypted1 = encryption_service.encrypt_credential(credential, user_id, salt1)
        encrypted2 = encryption_service.encrypt_credential(credential, user_id, salt2)
        
        assert encrypted1 != encrypted2  # Different salts should produce different encrypted values
    
    def test_encrypt_empty_credential_raises_error(self, encryption_service):
        """Test that encrypting empty credential raises error."""
        user_id = "test-user-123"
        user_salt = encryption_service.generate_user_salt()
        
        with pytest.raises(ValueError, match="Credential cannot be empty"):
            encryption_service.encrypt_credential("", user_id, user_salt)
        
        with pytest.raises(ValueError, match="Credential cannot be empty"):
            encryption_service.encrypt_credential(None, user_id, user_salt)
    
    def test_decrypt_empty_credential_raises_error(self, encryption_service):
        """Test that decrypting empty credential raises error."""
        user_id = "test-user-123"
        user_salt = encryption_service.generate_user_salt()
        
        with pytest.raises(ValueError, match="Encrypted credential cannot be empty"):
            encryption_service.decrypt_credential("", user_id, user_salt)
        
        with pytest.raises(ValueError, match="Encrypted credential cannot be empty"):
            encryption_service.decrypt_credential(None, user_id, user_salt)
    
    def test_decrypt_with_wrong_user_raises_error(self, encryption_service):
        """Test that decrypting with wrong user fails."""
        credential = "sk-test-api-key-12345"
        user_id = "test-user-123"
        wrong_user_id = "wrong-user-456"
        user_salt = encryption_service.generate_user_salt()
        
        encrypted = encryption_service.encrypt_credential(credential, user_id, user_salt)
        
        with pytest.raises(ValueError, match="Failed to decrypt credential"):
            encryption_service.decrypt_credential(encrypted, wrong_user_id, user_salt)
    
    def test_decrypt_with_wrong_salt_raises_error(self, encryption_service):
        """Test that decrypting with wrong salt fails."""
        credential = "sk-test-api-key-12345"
        user_id = "test-user-123"
        user_salt = encryption_service.generate_user_salt()
        wrong_salt = encryption_service.generate_user_salt()
        
        encrypted = encryption_service.encrypt_credential(credential, user_id, user_salt)
        
        with pytest.raises(ValueError, match="Failed to decrypt credential"):
            encryption_service.decrypt_credential(encrypted, user_id, wrong_salt)
    
    def test_decrypt_invalid_encrypted_data(self, encryption_service):
        """Test that decrypting invalid data fails."""
        user_id = "test-user-123"
        user_salt = encryption_service.generate_user_salt()
        invalid_encrypted = "not-valid-encrypted-data"
        
        with pytest.raises(ValueError, match="Failed to decrypt credential"):
            encryption_service.decrypt_credential(invalid_encrypted, user_id, user_salt)
    
    def test_hash_encryption_key(self, encryption_service):
        """Test encryption key hashing."""
        user_salt = encryption_service.generate_user_salt()
        hash1 = encryption_service.hash_encryption_key(user_salt)
        hash2 = encryption_service.hash_encryption_key(user_salt)
        
        assert hash1 == hash2  # Same salt should produce same hash
        assert len(hash1) == 64  # SHA-256 hex digest length
        assert isinstance(hash1, str)
    
    def test_hash_encryption_key_different_salts(self, encryption_service):
        """Test that different salts produce different hashes."""
        salt1 = encryption_service.generate_user_salt()
        salt2 = encryption_service.generate_user_salt()
        
        hash1 = encryption_service.hash_encryption_key(salt1)
        hash2 = encryption_service.hash_encryption_key(salt2)
        
        assert hash1 != hash2
    
    @pytest.mark.asyncio
    async def test_validate_github_token_invalid_format(self, encryption_service):
        """Test GitHub token validation with invalid format."""
        is_valid, error = await encryption_service.validate_github_token("invalid-token")
        
        assert is_valid is False
        assert "Invalid GitHub token format" in error
    
    @pytest.mark.asyncio
    async def test_validate_github_token_empty(self, encryption_service):
        """Test GitHub token validation with empty token."""
        is_valid, error = await encryption_service.validate_github_token("")
        
        assert is_valid is False
        assert "GitHub token is required" in error
    
    @pytest.mark.asyncio
    async def test_validate_github_token_valid_format(self, encryption_service):
        """Test GitHub token validation with valid format (mocked API call)."""
        valid_token = "ghp_" + "a" * 36
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            is_valid, error = await encryption_service.validate_github_token(valid_token)
            
            assert is_valid is True
            assert error is None
    
    @pytest.mark.asyncio
    async def test_validate_github_token_unauthorized(self, encryption_service):
        """Test GitHub token validation with unauthorized response."""
        valid_token = "ghp_" + "a" * 36
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            is_valid, error = await encryption_service.validate_github_token(valid_token)
            
            assert is_valid is False
            assert "Invalid or expired GitHub token" in error
    
    @pytest.mark.asyncio
    async def test_validate_ai_api_key_invalid_format(self, encryption_service):
        """Test AI API key validation with invalid format."""
        is_valid, error = await encryption_service.validate_ai_api_key("invalid-key", "openai")
        
        assert is_valid is False
        assert "Invalid OpenAI API key format" in error
    
    @pytest.mark.asyncio
    async def test_validate_ai_api_key_empty(self, encryption_service):
        """Test AI API key validation with empty key."""
        is_valid, error = await encryption_service.validate_ai_api_key("", "openai")
        
        assert is_valid is False
        assert "AI API key is required" in error
    
    @pytest.mark.asyncio
    async def test_validate_ai_api_key_unsupported_provider(self, encryption_service):
        """Test AI API key validation with unsupported provider."""
        is_valid, error = await encryption_service.validate_ai_api_key("sk-test", "unsupported")
        
        assert is_valid is False
        assert "Unsupported AI provider" in error
    
    @pytest.mark.asyncio
    async def test_validate_openai_key_valid(self, encryption_service):
        """Test OpenAI API key validation with valid key (mocked)."""
        valid_key = "sk-" + "a" * 48
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            is_valid, error = await encryption_service.validate_ai_api_key(valid_key, "openai")
            
            assert is_valid is True
            assert error is None
    
    @pytest.mark.asyncio
    async def test_validate_gemini_key_valid(self, encryption_service):
        """Test Gemini API key validation with valid key (mocked)."""
        valid_key = "AIza" + "a" * 35
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            is_valid, error = await encryption_service.validate_ai_api_key(valid_key, "gemini")
            
            assert is_valid is True
            assert error is None