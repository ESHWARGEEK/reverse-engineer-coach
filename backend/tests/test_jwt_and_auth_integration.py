"""
JWT Service and Authentication Integration Tests
Tests for JWT token generation, validation, and complete authentication workflows.
"""

import pytest
import asyncio
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

from app.services.jwt_service import JWTService, TokenData, TokenPair
from app.services.auth_service import AuthService, UserRegistrationRequest, UserLoginRequest
from app.services.password_service import PasswordService
from app.models import User, UserCredentials, UserSession


class TestJWTService:
    """Test JWT token generation, validation, and management."""
    
    @pytest.fixture
    def jwt_service(self):
        """Create JWT service with test configuration."""
        with patch.dict(os.environ, {
            'JWT_SECRET_KEY': 'test-jwt-secret-key-for-testing-32-chars',
            'ACCESS_TOKEN_EXPIRE_MINUTES': '30',
            'REFRESH_TOKEN_EXPIRE_DAYS': '30',
            'JWT_ISSUER': 'test-issuer',
            'JWT_AUDIENCE': 'test-audience'
        }):
            return JWTService()
    
    @pytest.fixture
    def test_user(self):
        """Create test user."""
        return User(
            id="test-user-123",
            email="test@example.com",
            hashed_password="hashed_password",
            is_active=True
        )
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        mock_session = Mock(spec=Session)
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.query = Mock()
        mock_session.delete = Mock()
        return mock_session
    
    def test_generate_token_pair(self, jwt_service, test_user, mock_db_session):
        """Test JWT token pair generation."""
        token_pair = jwt_service.generate_token_pair(test_user, mock_db_session)
        
        assert isinstance(token_pair, TokenPair)
        assert token_pair.access_token is not None
        assert token_pair.refresh_token is not None
        assert token_pair.token_type == "bearer"
        assert token_pair.expires_in == 30 * 60  # 30 minutes in seconds
        
        # Verify session was created
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    def test_validate_access_token_valid(self, jwt_service, test_user, mock_db_session):
        """Test valid access token validation."""
        token_pair = jwt_service.generate_token_pair(test_user, mock_db_session)
        
        is_valid, token_data, error = jwt_service.validate_access_token(token_pair.access_token)
        
        assert is_valid is True
        assert token_data is not None
        assert token_data.user_id == test_user.id
        assert token_data.email == test_user.email
        assert token_data.token_type == "access"
        assert error is None
    
    def test_validate_access_token_invalid(self, jwt_service):
        """Test invalid access token validation."""
        invalid_token = "invalid.jwt.token"
        
        is_valid, token_data, error = jwt_service.validate_access_token(invalid_token)
        
        assert is_valid is False
        assert token_data is None
        assert error is not None
        assert "Token validation failed" in error
    
    def test_validate_access_token_wrong_type(self, jwt_service, test_user, mock_db_session):
        """Test access token validation with wrong token type."""
        token_pair = jwt_service.generate_token_pair(test_user, mock_db_session)
        
        # Try to validate refresh token as access token
        is_valid, token_data, error = jwt_service.validate_access_token(token_pair.refresh_token)
        
        assert is_valid is False
        assert token_data is None
        assert "Invalid token type" in error
    
    def test_validate_refresh_token_valid(self, jwt_service, test_user, mock_db_session):
        """Test valid refresh token validation."""
        token_pair = jwt_service.generate_token_pair(test_user, mock_db_session)
        
        # Mock session query for refresh token validation
        mock_session = Mock()
        mock_session.expires_at = datetime.utcnow() + timedelta(days=30)
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_session
        
        is_valid, token_data, error = jwt_service.validate_refresh_token(token_pair.refresh_token, mock_db_session)
        
        assert is_valid is True
        assert token_data is not None
        assert token_data.user_id == test_user.id
        assert token_data.token_type == "refresh"
        assert error is None
    
    def test_validate_refresh_token_no_session(self, jwt_service, test_user, mock_db_session):
        """Test refresh token validation with no session in database."""
        token_pair = jwt_service.generate_token_pair(test_user, mock_db_session)
        
        # Mock no session found
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        is_valid, token_data, error = jwt_service.validate_refresh_token(token_pair.refresh_token, mock_db_session)
        
        assert is_valid is False
        assert token_data is None
        assert "Invalid or expired session" in error
    
    def test_refresh_access_token_success(self, jwt_service, test_user, mock_db_session):
        """Test successful access token refresh."""
        token_pair = jwt_service.generate_token_pair(test_user, mock_db_session)
        
        # Mock session and user queries
        mock_session = Mock()
        mock_session.expires_at = datetime.utcnow() + timedelta(days=30)
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [mock_session, test_user]
        
        success, new_token, error = jwt_service.refresh_access_token(token_pair.refresh_token, mock_db_session)
        
        assert success is True
        assert new_token is not None
        assert error is None
        
        # Verify new token is valid
        is_valid, token_data, _ = jwt_service.validate_access_token(new_token)
        assert is_valid is True
        assert token_data.user_id == test_user.id
    
    def test_refresh_access_token_invalid_refresh_token(self, jwt_service, mock_db_session):
        """Test access token refresh with invalid refresh token."""
        invalid_token = "invalid.refresh.token"
        
        success, new_token, error = jwt_service.refresh_access_token(invalid_token, mock_db_session)
        
        assert success is False
        assert new_token is None
        assert error is not None
    
    def test_revoke_token_success(self, jwt_service, test_user, mock_db_session):
        """Test successful token revocation."""
        token_pair = jwt_service.generate_token_pair(test_user, mock_db_session)
        
        # Mock session query
        mock_session = Mock()
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_session
        
        success, error = jwt_service.revoke_token(token_pair.access_token, mock_db_session)
        
        assert success is True
        assert error is None
        mock_db_session.delete.assert_called_once_with(mock_session)
        mock_db_session.commit.assert_called()
    
    def test_revoke_all_user_tokens(self, jwt_service, mock_db_session):
        """Test revoking all tokens for a user."""
        user_id = "test-user-123"
        
        success, error = jwt_service.revoke_all_user_tokens(user_id, mock_db_session)
        
        assert success is True
        assert error is None
        mock_db_session.query.return_value.filter.return_value.delete.assert_called_once()
        mock_db_session.commit.assert_called()
    
    def test_cleanup_expired_sessions(self, jwt_service, mock_db_session):
        """Test cleanup of expired sessions."""
        # Mock expired sessions count
        mock_db_session.query.return_value.filter.return_value.count.return_value = 5
        
        cleaned_count = jwt_service.cleanup_expired_sessions(mock_db_session)
        
        assert cleaned_count == 5
        mock_db_session.query.return_value.filter.return_value.delete.assert_called_once()
        mock_db_session.commit.assert_called()
    
    def test_get_token_info(self, jwt_service, test_user, mock_db_session):
        """Test getting token information without validation."""
        token_pair = jwt_service.generate_token_pair(test_user, mock_db_session)
        
        token_info = jwt_service.get_token_info(token_pair.access_token)
        
        assert token_info is not None
        assert token_info["sub"] == test_user.id
        assert token_info["email"] == test_user.email
        assert token_info["token_type"] == "access"
    
    def test_get_token_info_invalid_token(self, jwt_service):
        """Test getting token information from invalid token."""
        invalid_token = "invalid.jwt.token"
        
        token_info = jwt_service.get_token_info(invalid_token)
        
        assert token_info is None


class TestAuthServiceIntegration:
    """Integration tests for the complete authentication service."""
    
    @pytest.fixture
    def auth_service(self):
        """Create auth service with test configuration."""
        with patch.dict(os.environ, {
            'CREDENTIAL_ENCRYPTION_KEY': 'test-encryption-key-for-testing-32-chars',
            'JWT_SECRET_KEY': 'test-jwt-secret-key-for-testing-32-chars'
        }), patch('app.services.auth_service.settings') as mock_settings:
            mock_settings.credential_encryption_key = 'test-encryption-key-for-testing-32-chars'
            return AuthService()
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        mock_session = Mock(spec=Session)
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.flush = Mock()
        mock_session.refresh = Mock()
        mock_session.rollback = Mock()
        mock_session.query = Mock()
        return mock_session
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_service, mock_db_session):
        """Test successful user registration."""
        registration_data = UserRegistrationRequest(
            email="test@example.com",
            password="TestPassword123!",
            confirm_password="TestPassword123!",
            github_token="ghp_" + "a" * 36,
            ai_api_key="sk-" + "a" * 48,
            ai_provider="openai"
        )
        
        # Mock user doesn't exist
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Mock user creation
        mock_user = Mock()
        mock_user.id = "test-user-123"
        mock_user.email = "test@example.com"
        mock_db_session.flush.side_effect = lambda: setattr(mock_user, 'id', 'test-user-123')
        
        # Mock API validation
        with patch.object(auth_service.credential_service, 'validate_github_token', return_value=(True, None)), \
             patch.object(auth_service.credential_service, 'validate_ai_api_key', return_value=(True, None)), \
             patch('app.models.User') as mock_user_class:
            
            mock_user_class.return_value = mock_user
            
            success, response, error = await auth_service.register_user(registration_data, mock_db_session)
        
        assert success is True
        assert response is not None
        assert response.user_id == "test-user-123"
        assert response.email == "test@example.com"
        assert response.access_token is not None
        assert response.refresh_token is not None
        assert error is None
    
    @pytest.mark.asyncio
    async def test_register_user_existing_email(self, auth_service, mock_db_session):
        """Test user registration with existing email."""
        registration_data = UserRegistrationRequest(
            email="test@example.com",
            password="TestPassword123!",
            confirm_password="TestPassword123!"
        )
        
        # Mock existing user
        existing_user = Mock()
        mock_db_session.query.return_value.filter.return_value.first.return_value = existing_user
        
        success, response, error = await auth_service.register_user(registration_data, mock_db_session)
        
        assert success is False
        assert response is None
        assert "already registered" in error
    
    @pytest.mark.asyncio
    async def test_register_user_weak_password(self, auth_service, mock_db_session):
        """Test user registration with weak password."""
        registration_data = UserRegistrationRequest(
            email="test@example.com",
            password="weak",
            confirm_password="weak"
        )
        
        success, response, error = await auth_service.register_user(registration_data, mock_db_session)
        
        assert success is False
        assert response is None
        assert "Password validation failed" in error
    
    @pytest.mark.asyncio
    async def test_login_user_success(self, auth_service, mock_db_session):
        """Test successful user login."""
        login_data = UserLoginRequest(
            email="test@example.com",
            password="TestPassword123!"
        )
        
        # Mock user exists with correct password
        mock_user = Mock()
        mock_user.id = "test-user-123"
        mock_user.email = "test@example.com"
        mock_user.hashed_password = PasswordService.hash_password("TestPassword123!")
        mock_user.is_active = True
        mock_user.last_login = None
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        success, response, error = await auth_service.login_user(login_data, mock_db_session)
        
        assert success is True
        assert response is not None
        assert response.user_id == "test-user-123"
        assert response.email == "test@example.com"
        assert response.access_token is not None
        assert response.refresh_token is not None
        assert error is None
    
    @pytest.mark.asyncio
    async def test_login_user_invalid_credentials(self, auth_service, mock_db_session):
        """Test user login with invalid credentials."""
        login_data = UserLoginRequest(
            email="test@example.com",
            password="WrongPassword123!"
        )
        
        # Mock user doesn't exist
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        success, response, error = await auth_service.login_user(login_data, mock_db_session)
        
        assert success is False
        assert response is None
        assert "Invalid email or password" in error
    
    @pytest.mark.asyncio
    async def test_login_user_inactive_account(self, auth_service, mock_db_session):
        """Test user login with inactive account."""
        login_data = UserLoginRequest(
            email="test@example.com",
            password="TestPassword123!"
        )
        
        # Mock inactive user
        mock_user = Mock()
        mock_user.hashed_password = PasswordService.hash_password("TestPassword123!")
        mock_user.is_active = False
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        success, response, error = await auth_service.login_user(login_data, mock_db_session)
        
        assert success is False
        assert response is None
        assert "Account is deactivated" in error
    
    @pytest.mark.asyncio
    async def test_validate_token_success(self, auth_service, mock_db_session):
        """Test successful token validation."""
        # Create a valid token first
        mock_user = Mock()
        mock_user.id = "test-user-123"
        mock_user.email = "test@example.com"
        mock_user.is_active = True
        
        token_pair = auth_service.jwt_service.generate_token_pair(mock_user, mock_db_session)
        
        # Mock user query for validation
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        is_valid, user, error = await auth_service.validate_token(token_pair.access_token, mock_db_session)
        
        assert is_valid is True
        assert user == mock_user
        assert error is None
    
    @pytest.mark.asyncio
    async def test_validate_token_invalid(self, auth_service, mock_db_session):
        """Test token validation with invalid token."""
        invalid_token = "invalid.jwt.token"
        
        is_valid, user, error = await auth_service.validate_token(invalid_token, mock_db_session)
        
        assert is_valid is False
        assert user is None
        assert error is not None


class TestSecurityFeatures:
    """Test security-specific features of the authentication system."""
    
    @pytest.fixture
    def auth_service(self):
        """Create auth service with test configuration."""
        with patch.dict(os.environ, {
            'CREDENTIAL_ENCRYPTION_KEY': 'test-encryption-key-for-testing-32-chars',
            'JWT_SECRET_KEY': 'test-jwt-secret-key-for-testing-32-chars'
        }), patch('app.services.auth_service.settings') as mock_settings:
            mock_settings.credential_encryption_key = 'test-encryption-key-for-testing-32-chars'
            return AuthService()
    
    def test_password_hashing_security(self):
        """Test that password hashing uses secure parameters."""
        password = "TestPassword123!"
        hashed = PasswordService.hash_password(password)
        
        # Verify bcrypt format and rounds
        assert hashed.startswith('$2b$')
        rounds = int(hashed.split('$')[2])
        assert rounds >= 12  # Security requirement
    
    def test_jwt_token_security(self):
        """Test JWT token security features."""
        with patch.dict(os.environ, {
            'JWT_SECRET_KEY': 'test-jwt-secret-key-for-testing-32-chars',
            'JWT_ISSUER': 'test-issuer',
            'JWT_AUDIENCE': 'test-audience'
        }):
            jwt_service = JWTService()
            
            # Verify security configuration
            assert jwt_service.secret_key is not None
            assert len(jwt_service.secret_key) >= 32  # Minimum key length
            assert jwt_service.algorithm == "HS256"
            assert jwt_service.issuer is not None
            assert jwt_service.audience is not None
    
    def test_credential_encryption_security(self, auth_service):
        """Test credential encryption security."""
        user_id = "test-user-123"
        credential = "sk-test-api-key-12345"
        
        # Generate salt and encrypt
        salt = auth_service.credential_service.generate_user_salt()
        encrypted = auth_service.credential_service.encrypt_credential(credential, user_id, salt)
        
        # Verify encryption properties
        assert encrypted != credential  # Must be encrypted
        assert len(encrypted) > len(credential)  # Encrypted data is longer
        
        # Verify decryption works
        decrypted = auth_service.credential_service.decrypt_credential(encrypted, user_id, salt)
        assert decrypted == credential
    
    @pytest.mark.asyncio
    async def test_api_credential_validation_security(self, auth_service):
        """Test API credential validation security."""
        # Test GitHub token validation
        invalid_github_token = "invalid-token"
        is_valid, error = await auth_service.credential_service.validate_github_token(invalid_github_token)
        assert is_valid is False
        assert "Invalid GitHub token format" in error
        
        # Test AI API key validation
        invalid_ai_key = "invalid-key"
        is_valid, error = await auth_service.credential_service.validate_ai_api_key(invalid_ai_key, "openai")
        assert is_valid is False
        assert "Invalid OpenAI API key format" in error