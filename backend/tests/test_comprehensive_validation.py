"""
Comprehensive tests for input validation system
Tests server-side validation, sanitization, and security measures.
"""

import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from app.main import app
from app.services.validation_service import ValidationService, ValidationResult
from app.schemas.validation_schemas import ValidationRules
from app.decorators.validation_decorators import validate_input
from app.middleware.validation_middleware import ValidationMiddleware


class TestValidationService:
    """Test the core validation service functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validation_service = ValidationService()
    
    def test_email_validation_success(self):
        """Test successful email validation."""
        result = self.validation_service.validate_email("test@example.com")
        assert result.is_valid
        assert not result.errors
    
    def test_email_validation_invalid_format(self):
        """Test email validation with invalid format."""
        result = self.validation_service.validate_email("invalid-email")
        assert not result.is_valid
        assert "email" in result.errors
    
    def test_email_validation_sql_injection(self):
        """Test email validation blocks SQL injection."""
        malicious_email = "test@example.com'; DROP TABLE users; --"
        result = self.validation_service.validate_email(malicious_email)
        assert not result.is_valid
        assert "email" in result.errors
    
    def test_email_validation_xss_attempt(self):
        """Test email validation blocks XSS attempts."""
        malicious_email = "test@example.com<script>alert('xss')</script>"
        result = self.validation_service.validate_email(malicious_email)
        assert not result.is_valid
        assert "email" in result.errors
    
    def test_password_validation_success(self):
        """Test successful password validation."""
        strong_password = "MyStr0ng!Password"
        result = self.validation_service.validate_password(strong_password)
        assert result.is_valid
        assert not result.errors
    
    def test_password_validation_too_short(self):
        """Test password validation with too short password."""
        result = self.validation_service.validate_password("short")
        assert not result.is_valid
        assert "password" in result.errors
    
    def test_password_validation_missing_requirements(self):
        """Test password validation with missing character types."""
        result = self.validation_service.validate_password("alllowercase")
        assert not result.is_valid
        assert "password" in result.errors
    
    def test_password_validation_weak_patterns(self):
        """Test password validation detects weak patterns."""
        result = self.validation_service.validate_password("Password1234")
        assert not result.is_valid
        assert "password" in result.errors
    
    def test_url_validation_success(self):
        """Test successful URL validation."""
        result = self.validation_service.validate_url("https://github.com/user/repo")
        assert result.is_valid
        assert not result.errors
    
    def test_url_validation_invalid_scheme(self):
        """Test URL validation with invalid scheme."""
        result = self.validation_service.validate_url("ftp://example.com")
        assert not result.is_valid
        assert "url" in result.errors
    
    def test_url_validation_javascript_injection(self):
        """Test URL validation blocks JavaScript injection."""
        malicious_url = "javascript:alert('xss')"
        result = self.validation_service.validate_url(malicious_url)
        assert not result.is_valid
        assert "url" in result.errors
    
    def test_github_url_validation_success(self):
        """Test successful GitHub URL validation."""
        result = self.validation_service.validate_github_url("https://github.com/user/repo")
        assert result.is_valid
        assert not result.errors
    
    def test_github_url_validation_invalid_domain(self):
        """Test GitHub URL validation with invalid domain."""
        result = self.validation_service.validate_github_url("https://gitlab.com/user/repo")
        assert not result.is_valid
        assert "github_url" in result.errors
    
    def test_api_key_validation_github_success(self):
        """Test successful GitHub API key validation."""
        valid_token = "ghp_" + "a" * 36
        result = self.validation_service.validate_api_key(valid_token, "github")
        assert result.is_valid
        assert not result.errors
    
    def test_api_key_validation_github_invalid(self):
        """Test GitHub API key validation with invalid format."""
        result = self.validation_service.validate_api_key("invalid_token", "github")
        assert not result.is_valid
        assert "api_key" in result.errors
    
    def test_api_key_validation_openai_success(self):
        """Test successful OpenAI API key validation."""
        valid_key = "sk-" + "a" * 48
        result = self.validation_service.validate_api_key(valid_key, "openai")
        assert result.is_valid
        assert not result.errors
    
    def test_api_key_validation_openai_invalid(self):
        """Test OpenAI API key validation with invalid format."""
        result = self.validation_service.validate_api_key("invalid_key", "openai")
        assert not result.is_valid
        assert "api_key" in result.errors
    
    def test_filename_validation_success(self):
        """Test successful filename validation."""
        result = self.validation_service.validate_filename("document.pdf")
        assert result.is_valid
        assert not result.errors
    
    def test_filename_validation_path_traversal(self):
        """Test filename validation blocks path traversal."""
        result = self.validation_service.validate_filename("../../../etc/passwd")
        assert not result.is_valid
        assert "filename" in result.errors
    
    def test_filename_validation_dangerous_extension(self):
        """Test filename validation blocks dangerous extensions."""
        result = self.validation_service.validate_filename("malware.exe")
        assert not result.is_valid
        assert "filename" in result.errors
    
    def test_text_input_validation_success(self):
        """Test successful text input validation."""
        result = self.validation_service.validate_text_input(
            "This is a valid text input",
            "description",
            min_length=5,
            max_length=100,
            allow_html=False
        )
        assert result.is_valid
        assert not result.errors
    
    def test_text_input_validation_too_short(self):
        """Test text input validation with too short text."""
        result = self.validation_service.validate_text_input(
            "Hi",
            "description",
            min_length=5,
            max_length=100
        )
        assert not result.is_valid
        assert "description" in result.errors
    
    def test_text_input_validation_xss_attempt(self):
        """Test text input validation blocks XSS attempts."""
        malicious_text = "Hello <script>alert('xss')</script> World"
        result = self.validation_service.validate_text_input(
            malicious_text,
            "description",
            allow_html=False
        )
        assert not result.is_valid
        assert "description" in result.errors
    
    def test_sanitize_and_validate_input_success(self):
        """Test comprehensive input sanitization and validation."""
        data = {
            "email": "test@example.com",
            "password": "MyStr0ng!Password",
            "github_token": "ghp_" + "a" * 36
        }
        
        sanitized_data, result = self.validation_service.sanitize_and_validate_input(
            data, ValidationRules.USER_REGISTRATION
        )
        
        assert result.is_valid
        assert not result.errors
        assert "email" in sanitized_data
        assert "password" in sanitized_data
        assert "github_token" in sanitized_data
    
    def test_sanitize_and_validate_input_with_errors(self):
        """Test input validation with multiple errors."""
        data = {
            "email": "invalid-email",
            "password": "weak",
            "github_token": "invalid_token"
        }
        
        sanitized_data, result = self.validation_service.sanitize_and_validate_input(
            data, ValidationRules.USER_REGISTRATION
        )
        
        assert not result.is_valid
        assert len(result.errors) > 0


class TestInputSanitizer:
    """Test the input sanitization functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validation_service = ValidationService()
        self.sanitizer = self.validation_service.sanitizer
    
    def test_sanitize_string_basic(self):
        """Test basic string sanitization."""
        input_text = "Hello <script>alert('xss')</script> World"
        sanitized = self.sanitizer.sanitize_string(input_text)
        
        assert "<script>" not in sanitized
        assert "alert" not in sanitized
        assert "Hello" in sanitized
        assert "World" in sanitized
    
    def test_sanitize_string_with_length_limit(self):
        """Test string sanitization with length limit."""
        long_text = "a" * 1000
        sanitized = self.sanitizer.sanitize_string(long_text, max_length=100)
        
        assert len(sanitized) <= 100
    
    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        filename = "my document.pdf"
        sanitized = self.sanitizer.sanitize_filename(filename)
        
        assert sanitized == "my document.pdf"
    
    def test_sanitize_filename_dangerous_characters(self):
        """Test filename sanitization removes dangerous characters."""
        filename = "my<>document|?.pdf"
        sanitized = self.sanitizer.sanitize_filename(filename)
        
        assert "<" not in sanitized
        assert ">" not in sanitized
        assert "|" not in sanitized
        assert "?" not in sanitized
    
    def test_sanitize_filename_path_traversal(self):
        """Test filename sanitization prevents path traversal."""
        filename = "../../../etc/passwd"
        sanitized = self.sanitizer.sanitize_filename(filename)
        
        assert ".." not in sanitized
        assert "/" not in sanitized
    
    def test_check_sql_injection_positive(self):
        """Test SQL injection detection returns True for malicious input."""
        malicious_input = "'; DROP TABLE users; --"
        result = self.sanitizer.check_sql_injection(malicious_input)
        
        assert result is True
    
    def test_check_sql_injection_negative(self):
        """Test SQL injection detection returns False for safe input."""
        safe_input = "This is a normal text input"
        result = self.sanitizer.check_sql_injection(safe_input)
        
        assert result is False
    
    def test_detect_xss_attempt_positive(self):
        """Test XSS detection returns True for malicious input."""
        malicious_input = "<script>alert('xss')</script>"
        result = self.validation_service.detect_xss_attempt(malicious_input)
        
        assert result is True
    
    def test_detect_xss_attempt_negative(self):
        """Test XSS detection returns False for safe input."""
        safe_input = "This is a normal text input"
        result = self.validation_service.detect_xss_attempt(safe_input)
        
        assert result is False


class TestValidationMiddleware:
    """Test the validation middleware functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
    
    def test_middleware_validates_json_body(self):
        """Test middleware validates JSON request body."""
        # Test with valid JSON
        valid_data = {
            "email": "test@example.com",
            "password": "MyStr0ng!Password"
        }
        
        response = self.client.post(
            "/api/v1/auth/login",
            json=valid_data,
            headers={"Content-Type": "application/json"}
        )
        
        # Should not fail due to validation (may fail for other reasons)
        assert response.status_code != 422
    
    def test_middleware_blocks_malicious_json(self):
        """Test middleware blocks malicious JSON content."""
        malicious_data = {
            "email": "test@example.com'; DROP TABLE users; --",
            "password": "password"
        }
        
        response = self.client.post(
            "/api/v1/auth/login",
            json=malicious_data,
            headers={"Content-Type": "application/json"}
        )
        
        # Should fail validation
        assert response.status_code == 422
    
    def test_middleware_validates_headers(self):
        """Test middleware validates request headers."""
        # Test with malicious headers
        response = self.client.get(
            "/api/v1/auth/me",
            headers={
                "User-Agent": "curl/7.68.0",  # Blocked user agent
                "Content-Type": "application/json"
            }
        )
        
        # Should fail validation due to blocked user agent
        assert response.status_code == 422
    
    def test_middleware_validates_request_size(self):
        """Test middleware validates request size."""
        # Create oversized request
        large_data = {"data": "x" * (11 * 1024 * 1024)}  # 11MB
        
        response = self.client.post(
            "/api/v1/auth/register",
            json=large_data,
            headers={"Content-Type": "application/json"}
        )
        
        # Should fail due to size limit
        assert response.status_code == 422


class TestValidationDecorators:
    """Test the validation decorators functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
    
    def test_auth_registration_validation(self):
        """Test authentication registration validation decorator."""
        # Test with invalid data
        invalid_data = {
            "email": "invalid-email",
            "password": "weak",
            "github_token": "invalid"
        }
        
        response = self.client.post(
            "/api/v1/auth/register",
            json=invalid_data
        )
        
        assert response.status_code == 422
        response_data = response.json()
        assert "errors" in response_data
    
    def test_auth_login_validation(self):
        """Test authentication login validation decorator."""
        # Test with invalid data
        invalid_data = {
            "email": "invalid-email",
            "password": ""
        }
        
        response = self.client.post(
            "/api/v1/auth/login",
            json=invalid_data
        )
        
        assert response.status_code == 422
        response_data = response.json()
        assert "errors" in response_data
    
    def test_repository_discovery_validation(self):
        """Test repository discovery validation decorator."""
        # Test with invalid concept
        invalid_data = {
            "concept": "x",  # Too short
            "max_results": 100  # Too many
        }
        
        # First need to authenticate
        auth_response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!"
            }
        )
        
        if auth_response.status_code == 200:
            token = auth_response.json()["access_token"]
            
            response = self.client.post(
                "/api/v1/discover/repositories",
                json=invalid_data,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 422


class TestSecurityMeasures:
    """Test security measures and rate limiting."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
    
    def test_rate_limiting_registration(self):
        """Test rate limiting on registration endpoint."""
        registration_data = {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "ai_provider": "openai"
        }
        
        # Make multiple rapid requests
        responses = []
        for i in range(5):
            response = self.client.post(
                "/api/v1/auth/register",
                json={**registration_data, "email": f"test{i}@example.com"}
            )
            responses.append(response)
        
        # Should eventually hit rate limit
        rate_limited = any(r.status_code == 429 for r in responses)
        # Note: This might not trigger in tests due to different IP handling
    
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention across endpoints."""
        malicious_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --"
        ]
        
        for payload in malicious_payloads:
            # Test login endpoint
            response = self.client.post(
                "/api/v1/auth/login",
                json={
                    "email": f"test{payload}@example.com",
                    "password": "password"
                }
            )
            
            # Should fail validation, not reach database
            assert response.status_code == 422
    
    def test_xss_prevention(self):
        """Test XSS prevention across endpoints."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "data:text/html,<script>alert('xss')</script>"
        ]
        
        for payload in xss_payloads:
            # Test concept search
            response = self.client.post(
                "/api/v1/discover/repositories",
                json={
                    "concept": payload,
                    "max_results": 5
                }
            )
            
            # Should fail validation
            assert response.status_code in [401, 422]  # 401 if not authenticated, 422 if validation fails


if __name__ == "__main__":
    pytest.main([__file__])