#!/usr/bin/env python3
"""
Comprehensive Integration Test Runner
Executes all integration tests and generates final system validation report
"""

import asyncio
import subprocess
import sys
import os
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TestSuiteResult:
    name: str
    passed: bool
    duration: float
    output: str
    error: Optional[str] = None

class IntegrationTestRunner:
    def __init__(self):
        self.results: List[TestSuiteResult] = []
        self.base_url = os.getenv("TEST_BASE_URL", "http://localhost:8000")
        
    async def run_command(self, command: List[str], name: str) -> TestSuiteResult:
        """Run a command and capture results"""
        logger.info(f"🚀 Running {name}...")
        start_time = time.time()
        
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "TEST_BASE_URL": self.base_url}
            )
            
            stdout, stderr = await process.communicate()
            duration = time.time() - start_time
            
            output = stdout.decode('utf-8') if stdout else ""
            error_output = stderr.decode('utf-8') if stderr else ""
            
            passed = process.returncode == 0
            
            result = TestSuiteResult(
                name=name,
                passed=passed,
                duration=duration,
                output=output,
                error=error_output if not passed else None
            )
            
            self.results.append(result)
            
            if passed:
                logger.info(f"✅ {name} completed successfully ({duration:.2f}s)")
            else:
                logger.error(f"❌ {name} failed ({duration:.2f}s)")
                if error_output:
                    logger.error(f"Error output: {error_output[:500]}...")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            result = TestSuiteResult(
                name=name,
                passed=False,
                duration=duration,
                output="",
                error=str(e)
            )
            self.results.append(result)
            logger.error(f"❌ {name} failed with exception: {e}")
            return result
    
    async def check_system_health(self) -> bool:
        """Check if the system is running and healthy"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health", timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        status = data.get("status", "unknown")
                        logger.info(f"✅ System health check passed - Status: {status}")
                        return True
                    else:
                        logger.error(f"❌ System health check failed - Status: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ System health check failed: {e}")
            return False
    
    async def run_backend_tests(self):
        """Run backend integration tests"""
        logger.info("🔧 Running Backend Integration Tests")
        
        # Change to backend directory
        backend_dir = os.path.join(os.getcwd(), "backend")
        
        # Run pytest with specific test files
        test_commands = [
            (["python", "-m", "pytest", "tests/test_integration_e2e.py", "-v"], "Backend E2E Tests"),
            (["python", "-m", "pytest", "tests/test_integration_simple.py", "-v"], "Backend Simple Integration Tests"),
            (["python", "-m", "pytest", "tests/test_authentication_services.py", "-v"], "Authentication Service Tests"),
            (["python", "-m", "pytest", "tests/test_repository_discovery.py", "-v"], "Repository Discovery Tests"),
        ]
        
        for command, name in test_commands:
            # Run command in backend directory
            full_command = command.copy()
            await self.run_command_in_directory(full_command, name, backend_dir)
    
    async def run_frontend_tests(self):
        """Run frontend integration tests"""
        logger.info("🎨 Running Frontend Integration Tests")
        
        # Change to frontend directory
        frontend_dir = os.path.join(os.getcwd(), "frontend")
        
        # Run npm test
        await self.run_command_in_directory(
            ["npm", "test", "--", "--watchAll=false", "--testPathPattern=test", "--verbose"],
            "Frontend Integration Tests",
            frontend_dir
        )
    
    async def run_command_in_directory(self, command: List[str], name: str, directory: str):
        """Run a command in a specific directory"""
        logger.info(f"🚀 Running {name} in {directory}...")
        start_time = time.time()
        
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=directory,
                env={**os.environ, "TEST_BASE_URL": self.base_url}
            )
            
            stdout, stderr = await process.communicate()
            duration = time.time() - start_time
            
            output = stdout.decode('utf-8') if stdout else ""
            error_output = stderr.decode('utf-8') if stderr else ""
            
            passed = process.returncode == 0
            
            result = TestSuiteResult(
                name=name,
                passed=passed,
                duration=duration,
                output=output,
                error=error_output if not passed else None
            )
            
            self.results.append(result)
            
            if passed:
                logger.info(f"✅ {name} completed successfully ({duration:.2f}s)")
            else:
                logger.error(f"❌ {name} failed ({duration:.2f}s)")
                if error_output:
                    logger.error(f"Error output: {error_output[:500]}...")
            
        except Exception as e:
            duration = time.time() - start_time
            result = TestSuiteResult(
                name=name,
                passed=False,
                duration=duration,
                output="",
                error=str(e)
            )
            self.results.append(result)
            logger.error(f"❌ {name} failed with exception: {e}")
    
    async def run_system_tests(self):
        """Run system-level integration tests"""
        logger.info("🔍 Running System Integration Tests")
        
        # Run custom integration test scripts
        test_scripts = [
            (["python", "scripts/integration-test.py"], "System Integration Tests"),
            (["python", "scripts/performance-optimization.py"], "Performance Tests"),
            (["python", "scripts/security-validation.py"], "Security Validation"),
        ]
        
        for command, name in test_scripts:
            await self.run_command(command, name)
    
    async def run_all_tests(self):
        """Run all integration tests"""
        logger.info("🚀 Starting Comprehensive Integration Test Suite")
        logger.info(f"Testing against: {self.base_url}")
        
        # Check system health first
        if not await self.check_system_health():
            logger.error("❌ System health check failed - cannot proceed with tests")
            return False
        
        # Run all test suites
        await self.run_system_tests()
        await self.run_backend_tests()
        await self.run_frontend_tests()
        
        # Generate final report
        return self.generate_final_report()
    
    def generate_final_report(self) -> bool:
        """Generate comprehensive final report"""
        total_suites = len(self.results)
        passed_suites = sum(1 for result in self.results if result.passed)
        failed_suites = total_suites - passed_suites
        
        total_duration = sum(result.duration for result in self.results)
        
        logger.info("\n" + "="*100)
        logger.info("📊 COMPREHENSIVE INTEGRATION TEST REPORT")
        logger.info("="*100)
        logger.info(f"Test Suites Run: {total_suites}")
        logger.info(f"Passed: {passed_suites} ✅")
        logger.info(f"Failed: {failed_suites} ❌")
        logger.info(f"Success Rate: {(passed_suites/total_suites)*100:.1f}%")
        logger.info(f"Total Duration: {total_duration:.2f}s")
        logger.info("="*100)
        
        # Detailed results
        logger.info("\n📋 DETAILED TEST RESULTS:")
        for result in self.results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            logger.info(f"  {status} {result.name} ({result.duration:.2f}s)")
            if not result.passed and result.error:
                logger.info(f"    Error: {result.error[:200]}...")
        
        # Failed tests summary
        if failed_suites > 0:
            logger.info(f"\n❌ FAILED TEST SUITES:")
            for result in self.results:
                if not result.passed:
                    logger.info(f"  • {result.name}")
                    if result.error:
                        logger.info(f"    → {result.error[:300]}...")
        
        # System readiness assessment
        logger.info(f"\n🎯 SYSTEM READINESS ASSESSMENT:")
        
        # Categorize failures
        critical_failures = []
        minor_failures = []
        
        for result in self.results:
            if not result.passed:
                if any(keyword in result.name.lower() for keyword in ['security', 'authentication', 'critical']):
                    critical_failures.append(result.name)
                else:
                    minor_failures.append(result.name)
        
        if len(critical_failures) > 0:
            logger.info("  ❌ SYSTEM NOT READY FOR PRODUCTION")
            logger.info("  Critical issues must be resolved before deployment")
            logger.info(f"  Critical failures: {', '.join(critical_failures)}")
        elif len(minor_failures) > 0:
            logger.info("  ⚠️  SYSTEM READY WITH MINOR ISSUES")
            logger.info("  Consider addressing minor issues for optimal performance")
            logger.info(f"  Minor failures: {', '.join(minor_failures)}")
        else:
            logger.info("  ✅ SYSTEM READY FOR PRODUCTION DEPLOYMENT")
            logger.info("  All integration tests passed successfully")
        
        # Recommendations
        logger.info(f"\n💡 RECOMMENDATIONS:")
        if failed_suites == 0:
            logger.info("  • System is ready for production deployment")
            logger.info("  • Monitor system performance after deployment")
            logger.info("  • Set up continuous monitoring and alerting")
        elif len(critical_failures) > 0:
            logger.info("  • Fix critical security and authentication issues")
            logger.info("  • Re-run integration tests after fixes")
            logger.info("  • Consider additional security auditing")
        else:
            logger.info("  • Address minor issues for better reliability")
            logger.info("  • Consider deploying with enhanced monitoring")
            logger.info("  • Plan fixes for minor issues in next iteration")
        
        logger.info("="*100)
        
        # Return True if system is ready (no critical failures)
        return len(critical_failures) == 0

async def main():
    """Main test runner"""
    runner = IntegrationTestRunner()
    
    try:
        success = await runner.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Test execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Test runner failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())