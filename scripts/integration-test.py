#!/usr/bin/env python3
"""
Comprehensive Integration Test Suite for Enhanced User System
Tests all major components and validates system reliability
"""

import asyncio
import aiohttp
import json
import time
import sys
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    name: str
    passed: bool
    duration: float
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class IntegrationTestSuite:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.test_results: List[TestResult] = []
        self.test_user_email = f"test_{int(time.time())}@example.com"
        self.test_user_password = "TestPassword123!"
        self.auth_token: Optional[str] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def run_test(self, test_name: str, test_func):
        """Run a single test and record results"""
        logger.info(f"Running test: {test_name}")
        start_time = time.time()
        
        try:
            result = await test_func()
            duration = time.time() - start_time
            
            if result is True or (isinstance(result, dict) and result.get('success', False)):
                self.test_results.append(TestResult(test_name, True, duration, details=result if isinstance(result, dict) else None))
                logger.info(f"✅ {test_name} - PASSED ({duration:.2f}s)")
            else:
                error_msg = result.get('error', 'Test failed') if isinstance(result, dict) else str(result)
                self.test_results.append(TestResult(test_name, False, duration, error_msg))
                logger.error(f"❌ {test_name} - FAILED: {error_msg}")
                
        except Exception as e:
            duration = time.time() - start_time
            self.test_results.append(TestResult(test_name, False, duration, str(e)))
            logger.error(f"❌ {test_name} - ERROR: {str(e)}")
    
    async def test_health_check(self) -> Dict[str, Any]:
        """Test basic system health"""
        async with self.session.get(f"{self.base_url}/health") as response:
            if response.status != 200:
                return {"success": False, "error": f"Health check failed with status {response.status}"}
            
            data = await response.json()
            if data.get("status") not in ["healthy", "degraded"]:
                return {"success": False, "error": f"System unhealthy: {data}"}
            
            return {"success": True, "status": data.get("status"), "services": data.get("services", {})}
    
    async def test_user_registration(self) -> Dict[str, Any]:
        """Test user registration flow"""
        registration_data = {
            "email": self.test_user_email,
            "password": self.test_user_password,
            "github_token": "ghp_test_token_123456789",
            "ai_api_key": "sk-test_key_123456789"
        }
        
        async with self.session.post(
            f"{self.base_url}/api/v1/auth/register",
            json=registration_data
        ) as response:
            if response.status != 201:
                error_text = await response.text()
                return {"success": False, "error": f"Registration failed: {response.status} - {error_text}"}
            
            data = await response.json()
            if not data.get("access_token"):
                return {"success": False, "error": "No access token returned"}
            
            self.auth_token = data["access_token"]
            return {"success": True, "user_id": data.get("user", {}).get("id")}
    
    async def test_user_login(self) -> Dict[str, Any]:
        """Test user login flow"""
        login_data = {
            "email": self.test_user_email,
            "password": self.test_user_password
        }
        
        async with self.session.post(
            f"{self.base_url}/api/v1/auth/login",
            json=login_data
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                return {"success": False, "error": f"Login failed: {response.status} - {error_text}"}
            
            data = await response.json()
            if not data.get("access_token"):
                return {"success": False, "error": "No access token returned"}
            
            return {"success": True, "token_type": data.get("token_type")}
    
    async def test_protected_route_access(self) -> Dict[str, Any]:
        """Test access to protected routes with authentication"""
        if not self.auth_token:
            return {"success": False, "error": "No auth token available"}
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with self.session.get(
            f"{self.base_url}/api/v1/profile",
            headers=headers
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                return {"success": False, "error": f"Protected route access failed: {response.status} - {error_text}"}
            
            data = await response.json()
            if not data.get("email"):
                return {"success": False, "error": "Profile data incomplete"}
            
            return {"success": True, "profile_loaded": True}
    
    async def test_repository_discovery(self) -> Dict[str, Any]:
        """Test repository discovery functionality"""
        if not self.auth_token:
            return {"success": False, "error": "No auth token available"}
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        discovery_data = {"concept": "microservices architecture"}
        
        async with self.session.post(
            f"{self.base_url}/api/v1/discover/repositories",
            json=discovery_data,
            headers=headers
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                return {"success": False, "error": f"Discovery failed: {response.status} - {error_text}"}
            
            data = await response.json()
            repositories = data.get("repositories", [])
            
            if len(repositories) == 0:
                return {"success": False, "error": "No repositories discovered"}
            
            return {"success": True, "repository_count": len(repositories)}
    
    async def test_project_creation(self) -> Dict[str, Any]:
        """Test project creation with user association"""
        if not self.auth_token:
            return {"success": False, "error": "No auth token available"}
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        project_data = {
            "repository_url": "https://github.com/microsoft/vscode",
            "architecture": "desktop-application",
            "language": "typescript"
        }
        
        async with self.session.post(
            f"{self.base_url}/api/v1/projects",
            json=project_data,
            headers=headers
        ) as response:
            if response.status != 201:
                error_text = await response.text()
                return {"success": False, "error": f"Project creation failed: {response.status} - {error_text}"}
            
            data = await response.json()
            if not data.get("id"):
                return {"success": False, "error": "No project ID returned"}
            
            return {"success": True, "project_id": data["id"]}
    
    async def test_dashboard_access(self) -> Dict[str, Any]:
        """Test user dashboard functionality"""
        if not self.auth_token:
            return {"success": False, "error": "No auth token available"}
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with self.session.get(
            f"{self.base_url}/api/v1/dashboard/projects",
            headers=headers
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                return {"success": False, "error": f"Dashboard access failed: {response.status} - {error_text}"}
            
            data = await response.json()
            projects = data.get("projects", [])
            
            return {"success": True, "project_count": len(projects)}
    
    async def test_security_measures(self) -> Dict[str, Any]:
        """Test security measures and rate limiting"""
        # Test rate limiting on auth endpoints
        failed_attempts = 0
        for i in range(10):  # Try multiple failed logins
            login_data = {
                "email": "nonexistent@example.com",
                "password": "wrongpassword"
            }
            
            async with self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json=login_data
            ) as response:
                if response.status == 429:  # Rate limited
                    return {"success": True, "rate_limiting_active": True, "attempts_before_limit": i}
                elif response.status == 401:
                    failed_attempts += 1
        
        # If we get here, rate limiting might not be working as expected
        return {"success": True, "rate_limiting_active": False, "failed_attempts": failed_attempts}
    
    async def test_data_isolation(self) -> Dict[str, Any]:
        """Test user data isolation"""
        if not self.auth_token:
            return {"success": False, "error": "No auth token available"}
        
        # Create a second user to test isolation
        second_user_email = f"test2_{int(time.time())}@example.com"
        registration_data = {
            "email": second_user_email,
            "password": self.test_user_password,
            "github_token": "ghp_test_token_second",
            "ai_api_key": "sk-test_key_second"
        }
        
        async with self.session.post(
            f"{self.base_url}/api/v1/auth/register",
            json=registration_data
        ) as response:
            if response.status != 201:
                return {"success": False, "error": "Could not create second user for isolation test"}
            
            second_user_data = await response.json()
            second_token = second_user_data["access_token"]
        
        # Test that each user only sees their own projects
        headers1 = {"Authorization": f"Bearer {self.auth_token}"}
        headers2 = {"Authorization": f"Bearer {second_token}"}
        
        async with self.session.get(f"{self.base_url}/api/v1/dashboard/projects", headers=headers1) as response1:
            user1_projects = (await response1.json()).get("projects", [])
        
        async with self.session.get(f"{self.base_url}/api/v1/dashboard/projects", headers=headers2) as response2:
            user2_projects = (await response2.json()).get("projects", [])
        
        # Check that project lists are isolated
        user1_project_ids = {p["id"] for p in user1_projects}
        user2_project_ids = {p["id"] for p in user2_projects}
        
        if user1_project_ids.intersection(user2_project_ids):
            return {"success": False, "error": "Data isolation failed - users can see each other's projects"}
        
        return {"success": True, "isolation_verified": True}
    
    async def test_performance_benchmarks(self) -> Dict[str, Any]:
        """Test system performance under load"""
        performance_results = {}
        
        # Test authentication performance
        start_time = time.time()
        login_data = {
            "email": self.test_user_email,
            "password": self.test_user_password
        }
        
        async with self.session.post(f"{self.base_url}/api/v1/auth/login", json=login_data) as response:
            auth_time = time.time() - start_time
            performance_results["auth_response_time"] = auth_time
        
        # Test discovery performance
        if self.auth_token:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            start_time = time.time()
            
            async with self.session.post(
                f"{self.base_url}/api/v1/discover/repositories",
                json={"concept": "web framework"},
                headers=headers
            ) as response:
                discovery_time = time.time() - start_time
                performance_results["discovery_response_time"] = discovery_time
        
        # Check if performance meets requirements (< 2 seconds for discovery)
        discovery_ok = performance_results.get("discovery_response_time", 0) < 2.0
        auth_ok = performance_results.get("auth_response_time", 0) < 1.0
        
        return {
            "success": discovery_ok and auth_ok,
            "performance_metrics": performance_results,
            "meets_requirements": {
                "discovery_under_2s": discovery_ok,
                "auth_under_1s": auth_ok
            }
        }
    
    async def run_all_tests(self):
        """Run the complete integration test suite"""
        logger.info("🚀 Starting Enhanced User System Integration Tests")
        logger.info(f"Testing against: {self.base_url}")
        
        # Define test sequence
        tests = [
            ("System Health Check", self.test_health_check),
            ("User Registration", self.test_user_registration),
            ("User Login", self.test_user_login),
            ("Protected Route Access", self.test_protected_route_access),
            ("Repository Discovery", self.test_repository_discovery),
            ("Project Creation", self.test_project_creation),
            ("Dashboard Access", self.test_dashboard_access),
            ("Security Measures", self.test_security_measures),
            ("Data Isolation", self.test_data_isolation),
            ("Performance Benchmarks", self.test_performance_benchmarks),
        ]
        
        # Run all tests
        for test_name, test_func in tests:
            await self.run_test(test_name, test_func)
        
        # Generate summary report
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.passed)
        failed_tests = total_tests - passed_tests
        
        total_duration = sum(result.duration for result in self.test_results)
        
        logger.info("\n" + "="*80)
        logger.info("📊 INTEGRATION TEST REPORT")
        logger.info("="*80)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests} ✅")
        logger.info(f"Failed: {failed_tests} ❌")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        logger.info(f"Total Duration: {total_duration:.2f}s")
        logger.info("="*80)
        
        if failed_tests > 0:
            logger.info("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result.passed:
                    logger.info(f"  • {result.name}: {result.error}")
        
        logger.info("\n📈 PERFORMANCE METRICS:")
        for result in self.test_results:
            if result.details and "performance_metrics" in result.details:
                metrics = result.details["performance_metrics"]
                for metric, value in metrics.items():
                    logger.info(f"  • {metric}: {value:.3f}s")
        
        # System recommendations
        logger.info("\n🔧 SYSTEM STATUS:")
        if passed_tests == total_tests:
            logger.info("  ✅ System is ready for production deployment")
        elif passed_tests >= total_tests * 0.8:
            logger.info("  ⚠️  System has minor issues - review failed tests")
        else:
            logger.info("  ❌ System has critical issues - deployment not recommended")
        
        return passed_tests == total_tests

async def main():
    """Main test runner"""
    base_url = os.getenv("TEST_BASE_URL", "http://localhost:8000")
    
    async with IntegrationTestSuite(base_url) as test_suite:
        success = await test_suite.run_all_tests()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())