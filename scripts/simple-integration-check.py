#!/usr/bin/env python3
"""
Simple Integration Check - Basic system validation
"""

import sys
import os
import subprocess
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_backend_dependencies():
    """Check if backend dependencies are installed"""
    logger.info("🔍 Checking backend dependencies...")
    
    try:
        os.chdir("backend")
        result = subprocess.run([sys.executable, "-c", "import fastapi, uvicorn, sqlalchemy"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("✅ Backend dependencies are installed")
            return True
        else:
            logger.error("❌ Backend dependencies missing")
            logger.error(result.stderr)
            return False
    except Exception as e:
        logger.error(f"❌ Error checking backend dependencies: {e}")
        return False
    finally:
        os.chdir("..")

def check_frontend_dependencies():
    """Check if frontend dependencies are installed"""
    logger.info("🔍 Checking frontend dependencies...")
    
    try:
        os.chdir("frontend")
        if os.path.exists("node_modules"):
            logger.info("✅ Frontend dependencies are installed")
            return True
        else:
            logger.error("❌ Frontend node_modules not found")
            return False
    except Exception as e:
        logger.error(f"❌ Error checking frontend dependencies: {e}")
        return False
    finally:
        os.chdir("..")

def check_database_setup():
    """Check if database is set up"""
    logger.info("🔍 Checking database setup...")
    
    try:
        os.chdir("backend")
        # Check if database file exists
        if os.path.exists("reverse_coach.db"):
            logger.info("✅ Database file exists")
            return True
        else:
            logger.warning("⚠️  Database file not found - may need migration")
            return False
    except Exception as e:
        logger.error(f"❌ Error checking database: {e}")
        return False
    finally:
        os.chdir("..")

def run_basic_backend_tests():
    """Run basic backend tests"""
    logger.info("🧪 Running basic backend tests...")
    
    try:
        os.chdir("backend")
        result = subprocess.run([sys.executable, "-m", "pytest", "tests/test_models.py", "-v"], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            logger.info("✅ Basic backend tests passed")
            return True
        else:
            logger.error("❌ Basic backend tests failed")
            logger.error(result.stdout)
            logger.error(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        logger.error("❌ Backend tests timed out")
        return False
    except Exception as e:
        logger.error(f"❌ Error running backend tests: {e}")
        return False
    finally:
        os.chdir("..")

def run_basic_frontend_tests():
    """Run basic frontend tests"""
    logger.info("🧪 Running basic frontend tests...")
    
    try:
        os.chdir("frontend")
        result = subprocess.run(["npm", "test", "--", "--watchAll=false", "--testPathPattern=HomePage"], 
                              capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            logger.info("✅ Basic frontend tests passed")
            return True
        else:
            logger.error("❌ Basic frontend tests failed")
            logger.error(result.stdout)
            logger.error(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        logger.error("❌ Frontend tests timed out")
        return False
    except Exception as e:
        logger.error(f"❌ Error running frontend tests: {e}")
        return False
    finally:
        os.chdir("..")

def main():
    """Main integration check"""
    logger.info("🚀 Starting Simple Integration Check")
    
    checks = [
        ("Backend Dependencies", check_backend_dependencies),
        ("Frontend Dependencies", check_frontend_dependencies),
        ("Database Setup", check_database_setup),
        ("Basic Backend Tests", run_basic_backend_tests),
        ("Basic Frontend Tests", run_basic_frontend_tests),
    ]
    
    results = []
    for name, check_func in checks:
        logger.info(f"\n--- {name} ---")
        result = check_func()
        results.append((name, result))
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("📊 INTEGRATION CHECK SUMMARY")
    logger.info("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"  {status} {name}")
    
    logger.info(f"\nOverall: {passed}/{total} checks passed")
    
    if passed == total:
        logger.info("✅ System is ready for comprehensive integration testing")
        return True
    else:
        logger.info("❌ System needs fixes before comprehensive testing")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)