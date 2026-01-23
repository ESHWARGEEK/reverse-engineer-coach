#!/usr/bin/env python3
"""
Security Validation Script for Enhanced User System
Validates security measures and identifies vulnerabilities
"""

import asyncio
import aiohttp
import json
import time
import sys
import os
import base64
import hashlib
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SecurityTest:
    name: str
    passed: bool
    severity: str  # "critical", "high", "medium", "low"
    description: str
    recommendation: Optional[str] = None

class SecurityValidator:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.security_tests: List[SecurityTest] = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def add_test_result(self, name: str, passed: bool, severity: str, description: str, recommendation: str = None):
        """Add a security test result"""
        self.security_tests.append(SecurityTest(name, passed, severity, description, recommendation))
        
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} [{severity.upper()}] {name}")
        if not passed and recommendation:
            logger.info(f"  → Recommendation: {recommendation}")
    
    async def test_https_enforcement(self) -> bool:
        """Test HTTPS enforcement and security headers"""
        try:
            # Test if HTTP redirects to HTTPS (in production)
            if "https://" in self.base_url:
                http_url = self.base_url.replace("https://", "http://")
                async with self.session.get(http_url, allow_redirects=False) as response:
                    if response.status in [301, 302, 307, 308]:
                        location = response.headers.get('Location', '')
                        if location.startswith('https://'):
                            self.add_test_result(
                                "HTTPS Redirect", True, "high",
                                "HTTP requests are properly redirected to HTTPS"
                            )
                            return True
            
            # Test security headers
            async with self.session.get(f"{self.base_url}/") as response:
                headers = response.headers
                
                # Check for security headers
                security_headers = {
                    'X-Content-Type-Options': 'nosniff',
                    'X-Frame-Options': ['DENY', 'SAMEORIGIN'],
                    'X-XSS-Protection': '1; mode=block',
                    'Strict-Transport-Security': None,  # Should exist for HTTPS
                }
                
                missing_headers = []
                for header, expected_value in security_headers.items():
                    if header not in headers:
                        missing_headers.append(header)
                    elif expected_value and isinstance(expected_value, list):
                        if headers[header] not in expected_value:
                            missing_headers.append(f"{header} (incorrect value)")
                
                if missing_headers:
                    self.add_test_result(
                        "Security Headers", False, "medium",
                        f"Missing security headers: {', '.join(missing_headers)}",
                        "Add missing security headers to prevent common attacks"
                    )
                    return False
                else:
                    self.add_test_result(
                        "Security Headers", True, "medium",
                        "All required security headers are present"
                    )
                    return True
                    
        except Exception as e:
            self.add_test_result(
                "HTTPS Enforcement", False, "critical",
                f"Could not test HTTPS enforcement: {e}",
                "Ensure HTTPS is properly configured"
            )
            return False
    
    async def test_authentication_security(self) -> bool:
        """Test authentication security measures"""
        # Test password strength requirements
        weak_passwords = [
            "123456",
            "password",
            "abc123",
            "test",
            "qwerty"
        ]
        
        registration_data_base = {
            "email": f"security_test_{int(time.time())}@example.com",
            "github_token": "ghp_test_token",
            "ai_api_key": "sk-test_key"
        }
        
        weak_password_rejected = True
        for weak_password in weak_passwords:
            registration_data = {**registration_data_base, "password": weak_password}
            
            async with self.session.post(f"{self.base_url}/api/v1/auth/register", json=registration_data) as response:
                if response.status == 201:  # Registration succeeded with weak password
                    weak_password_rejected = False
                    break
        
        self.add_test_result(
            "Password Strength Validation", weak_password_rejected, "high",
            "Weak passwords are rejected during registration" if weak_password_rejected else "Weak passwords are accepted",
            "Implement stronger password validation rules" if not weak_password_rejected else None
        )
        
        return weak_password_rejected
    
    async def test_rate_limiting(self) -> bool:
        """Test rate limiting on authentication endpoints"""
        # Test login rate limiting
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        rate_limited = False
        for i in range(15):  # Try 15 failed login attempts
            async with self.session.post(f"{self.base_url}/api/v1/auth/login", json=login_data) as response:
                if response.status == 429:  # Too Many Requests
                    rate_limited = True
                    break
                await asyncio.sleep(0.1)  # Small delay between requests
        
        self.add_test_result(
            "Authentication Rate Limiting", rate_limited, "high",
            "Rate limiting is active on authentication endpoints" if rate_limited else "No rate limiting detected",
            "Implement rate limiting to prevent brute force attacks" if not rate_limited else None
        )
        
        return rate_limited
    
    async def test_jwt_security(self) -> bool:
        """Test JWT token security"""
        # Create a test user to get a valid JWT
        test_email = f"jwt_test_{int(time.time())}@example.com"
        registration_data = {
            "email": test_email,
            "password": "SecurePassword123!",
            "github_token": "ghp_test_token",
            "ai_api_key": "sk-test_key"
        }
        
        try:
            async with self.session.post(f"{self.base_url}/api/v1/auth/register", json=registration_data) as response:
                if response.status != 201:
                    self.add_test_result(
                        "JWT Security Test", False, "medium",
                        "Could not create test user for JWT testing",
                        "Ensure user registration is working"
                    )
                    return False
                
                data = await response.json()
                token = data.get("access_token")
                
                if not token:
                    self.add_test_result(
                        "JWT Token Generation", False, "critical",
                        "No JWT token returned on registration",
                        "Ensure JWT tokens are properly generated"
                    )
                    return False
            
            # Test token structure (should be three base64 parts separated by dots)
            token_parts = token.split('.')
            if len(token_parts) != 3:
                self.add_test_result(
                    "JWT Token Structure", False, "high",
                    "JWT token does not have correct structure",
                    "Ensure JWT tokens follow standard format"
                )
                return False
            
            # Test that token is required for protected endpoints
            async with self.session.get(f"{self.base_url}/api/v1/profile") as response:
                if response.status != 401:
                    self.add_test_result(
                        "JWT Authorization", False, "critical",
                        "Protected endpoints accessible without authentication",
                        "Ensure all protected endpoints require valid JWT tokens"
                    )
                    return False
            
            # Test that invalid tokens are rejected
            invalid_headers = {"Authorization": "Bearer invalid_token"}
            async with self.session.get(f"{self.base_url}/api/v1/profile", headers=invalid_headers) as response:
                if response.status != 401:
                    self.add_test_result(
                        "Invalid JWT Rejection", False, "critical",
                        "Invalid JWT tokens are not properly rejected",
                        "Implement proper JWT token validation"
                    )
                    return False
            
            self.add_test_result(
                "JWT Security", True, "critical",
                "JWT tokens are properly generated and validated"
            )
            return True
            
        except Exception as e:
            self.add_test_result(
                "JWT Security Test", False, "critical",
                f"JWT security test failed: {e}",
                "Review JWT implementation for security issues"
            )
            return False
    
    async def test_input_validation(self) -> bool:
        """Test input validation and sanitization"""
        # Test SQL injection attempts
        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users --"
        ]
        
        sql_injection_blocked = True
        for payload in sql_injection_payloads:
            login_data = {
                "email": payload,
                "password": "test"
            }
            
            try:
                async with self.session.post(f"{self.base_url}/api/v1/auth/login", json=login_data) as response:
                    # Should return 400 (validation error) or 401 (unauthorized), not 500 (server error)
                    if response.status == 500:
                        sql_injection_blocked = False
                        break
            except Exception:
                # Connection errors might indicate server crash from injection
                sql_injection_blocked = False
                break
        
        self.add_test_result(
            "SQL Injection Protection", sql_injection_blocked, "critical",
            "SQL injection attempts are properly handled" if sql_injection_blocked else "Potential SQL injection vulnerability",
            "Implement proper input validation and parameterized queries" if not sql_injection_blocked else None
        )
        
        # Test XSS prevention
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>"
        ]
        
        xss_blocked = True
        for payload in xss_payloads:
            registration_data = {
                "email": f"test_{int(time.time())}@example.com",
                "password": "SecurePassword123!",
                "github_token": payload,  # Try XSS in API credential field
                "ai_api_key": "sk-test_key"
            }
            
            async with self.session.post(f"{self.base_url}/api/v1/auth/register", json=registration_data) as response:
                if response.status == 201:
                    # Check if the payload was stored as-is (potential XSS)
                    data = await response.json()
                    token = data.get("access_token")
                    if token:
                        headers = {"Authorization": f"Bearer {token}"}
                        async with self.session.get(f"{self.base_url}/api/v1/profile", headers=headers) as profile_response:
                            if profile_response.status == 200:
                                profile_data = await profile_response.json()
                                # Check if XSS payload appears in response
                                if payload in str(profile_data):
                                    xss_blocked = False
                                    break
        
        self.add_test_result(
            "XSS Protection", xss_blocked, "high",
            "XSS payloads are properly sanitized" if xss_blocked else "Potential XSS vulnerability detected",
            "Implement proper input sanitization and output encoding" if not xss_blocked else None
        )
        
        return sql_injection_blocked and xss_blocked
    
    async def test_data_encryption(self) -> bool:
        """Test that sensitive data is properly encrypted"""
        # Create a test user with API credentials
        test_email = f"encryption_test_{int(time.time())}@example.com"
        test_github_token = "ghp_test_token_for_encryption"
        test_ai_key = "sk-test_key_for_encryption"
        
        registration_data = {
            "email": test_email,
            "password": "SecurePassword123!",
            "github_token": test_github_token,
            "ai_api_key": test_ai_key
        }
        
        try:
            async with self.session.post(f"{self.base_url}/api/v1/auth/register", json=registration_data) as response:
                if response.status != 201:
                    self.add_test_result(
                        "Data Encryption Test", False, "medium",
                        "Could not create test user for encryption testing",
                        "Ensure user registration is working"
                    )
                    return False
                
                data = await response.json()
                token = data.get("access_token")
                
                # Get user profile to check if credentials are masked
                headers = {"Authorization": f"Bearer {token}"}
                async with self.session.get(f"{self.base_url}/api/v1/profile", headers=headers) as profile_response:
                    if profile_response.status == 200:
                        profile_data = await profile_response.json()
                        
                        # Check that raw credentials are not exposed
                        profile_str = str(profile_data)
                        if test_github_token in profile_str or test_ai_key in profile_str:
                            self.add_test_result(
                                "Credential Masking", False, "critical",
                                "Raw API credentials are exposed in profile responses",
                                "Ensure API credentials are properly masked in all responses"
                            )
                            return False
                        else:
                            self.add_test_result(
                                "Credential Masking", True, "critical",
                                "API credentials are properly masked in responses"
                            )
                            return True
                    else:
                        self.add_test_result(
                            "Data Encryption Test", False, "medium",
                            "Could not retrieve user profile for encryption testing",
                            "Ensure profile endpoint is working"
                        )
                        return False
                        
        except Exception as e:
            self.add_test_result(
                "Data Encryption Test", False, "critical",
                f"Encryption test failed: {e}",
                "Review data encryption implementation"
            )
            return False
    
    async def test_cors_configuration(self) -> bool:
        """Test CORS configuration"""
        try:
            # Test preflight request
            headers = {
                'Origin': 'https://malicious-site.com',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            
            async with self.session.options(f"{self.base_url}/api/v1/auth/login", headers=headers) as response:
                cors_headers = response.headers
                
                # Check if malicious origin is allowed
                allowed_origins = cors_headers.get('Access-Control-Allow-Origin', '')
                if allowed_origins == '*' or 'malicious-site.com' in allowed_origins:
                    self.add_test_result(
                        "CORS Configuration", False, "medium",
                        "CORS allows requests from any origin or malicious origins",
                        "Configure CORS to only allow trusted origins"
                    )
                    return False
                else:
                    self.add_test_result(
                        "CORS Configuration", True, "medium",
                        "CORS is properly configured to restrict origins"
                    )
                    return True
                    
        except Exception as e:
            self.add_test_result(
                "CORS Configuration", False, "medium",
                f"Could not test CORS configuration: {e}",
                "Ensure CORS is properly configured"
            )
            return False
    
    async def run_security_validation(self):
        """Run comprehensive security validation"""
        logger.info("🔒 Starting Security Validation Tests")
        logger.info(f"Testing against: {self.base_url}")
        
        # Run all security tests
        await self.test_https_enforcement()
        await self.test_authentication_security()
        await self.test_rate_limiting()
        await self.test_jwt_security()
        await self.test_input_validation()
        await self.test_data_encryption()
        await self.test_cors_configuration()
        
        # Generate security report
        self.generate_security_report()
    
    def generate_security_report(self):
        """Generate comprehensive security report"""
        total_tests = len(self.security_tests)
        passed_tests = sum(1 for test in self.security_tests if test.passed)
        failed_tests = total_tests - passed_tests
        
        # Count by severity
        critical_failures = sum(1 for test in self.security_tests if not test.passed and test.severity == "critical")
        high_failures = sum(1 for test in self.security_tests if not test.passed and test.severity == "high")
        medium_failures = sum(1 for test in self.security_tests if not test.passed and test.severity == "medium")
        
        logger.info("\n" + "="*80)
        logger.info("🔒 SECURITY VALIDATION REPORT")
        logger.info("="*80)
        logger.info(f"Total Security Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests} ✅")
        logger.info(f"Failed: {failed_tests} ❌")
        logger.info(f"Security Score: {(passed_tests/total_tests)*100:.1f}%")
        logger.info("="*80)
        
        if failed_tests > 0:
            logger.info(f"\n❌ SECURITY ISSUES FOUND:")
            logger.info(f"  Critical: {critical_failures}")
            logger.info(f"  High: {high_failures}")
            logger.info(f"  Medium: {medium_failures}")
            
            logger.info(f"\n🚨 FAILED SECURITY TESTS:")
            for test in self.security_tests:
                if not test.passed:
                    logger.info(f"  [{test.severity.upper()}] {test.name}: {test.description}")
                    if test.recommendation:
                        logger.info(f"    → {test.recommendation}")
        
        # Security assessment
        logger.info(f"\n🛡️  SECURITY ASSESSMENT:")
        if critical_failures > 0:
            logger.info("  ❌ CRITICAL SECURITY ISSUES - Deployment not recommended")
        elif high_failures > 0:
            logger.info("  ⚠️  HIGH SECURITY RISKS - Address before production deployment")
        elif medium_failures > 0:
            logger.info("  ⚠️  MEDIUM SECURITY RISKS - Consider addressing for better security")
        else:
            logger.info("  ✅ Security validation passed - System is secure for deployment")
        
        return critical_failures == 0 and high_failures == 0

async def main():
    """Main security validation runner"""
    base_url = os.getenv("TEST_BASE_URL", "http://localhost:8000")
    
    async with SecurityValidator(base_url) as validator:
        await validator.run_security_validation()

if __name__ == "__main__":
    asyncio.run(main())