#!/usr/bin/env python3
"""
Integration Issues Fix Script
Addresses issues found during integration testing
"""

import os
import sys
import subprocess
import json
import logging
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IntegrationIssueFixer:
    def __init__(self):
        self.issues_found = []
        self.fixes_applied = []
        
    def log_issue(self, issue: str, severity: str = "medium"):
        """Log an issue found during testing"""
        self.issues_found.append({"issue": issue, "severity": severity})
        logger.warning(f"[{severity.upper()}] Issue found: {issue}")
    
    def log_fix(self, fix: str):
        """Log a fix that was applied"""
        self.fixes_applied.append(fix)
        logger.info(f"✅ Fix applied: {fix}")
    
    def fix_react_version_conflicts(self):
        """Fix React version conflicts in frontend"""
        logger.info("🔧 Fixing React version conflicts...")
        
        try:
            os.chdir("frontend")
            
            # Check current package.json
            with open("package.json", "r") as f:
                package_data = json.load(f)
            
            # Update React versions to be consistent
            react_version = "18.3.1"
            react_dom_version = "18.3.1"
            react_types_version = "^18.2.42"
            react_dom_types_version = "^18.2.17"
            
            # Update dependencies
            if "dependencies" in package_data:
                package_data["dependencies"]["react"] = react_version
                package_data["dependencies"]["react-dom"] = react_dom_version
                
            if "devDependencies" in package_data:
                package_data["devDependencies"]["@types/react"] = react_types_version
                package_data["devDependencies"]["@types/react-dom"] = react_dom_types_version
            
            # Ensure resolutions are properly set
            if "resolutions" not in package_data:
                package_data["resolutions"] = {}
            
            package_data["resolutions"]["react"] = react_version
            package_data["resolutions"]["react-dom"] = react_dom_version
            package_data["resolutions"]["@types/react"] = react_types_version
            package_data["resolutions"]["@types/react-dom"] = react_dom_types_version
            
            # Write updated package.json
            with open("package.json", "w") as f:
                json.dump(package_data, f, indent=2)
            
            self.log_fix("Updated React versions in package.json for consistency")
            
            # Clear node_modules and reinstall
            logger.info("Clearing node_modules and reinstalling dependencies...")
            if os.path.exists("node_modules"):
                subprocess.run(["rm", "-rf", "node_modules"], shell=True, check=False)
            
            if os.path.exists("package-lock.json"):
                os.remove("package-lock.json")
            
            # Reinstall dependencies
            result = subprocess.run(["npm", "install"], capture_output=True, text=True)
            if result.returncode == 0:
                self.log_fix("Reinstalled frontend dependencies successfully")
            else:
                self.log_issue(f"Failed to reinstall dependencies: {result.stderr}", "high")
            
        except Exception as e:
            self.log_issue(f"Failed to fix React version conflicts: {e}", "high")
        finally:
            os.chdir("..")
    
    def fix_backend_test_issues(self):
        """Fix backend test issues"""
        logger.info("🔧 Fixing backend test issues...")
        
        try:
            os.chdir("backend")
            
            # Check if test models file has issues
            test_models_path = "tests/test_models.py"
            if os.path.exists(test_models_path):
                with open(test_models_path, "r") as f:
                    content = f.read()
                
                # Fix SQLAlchemy deprecation warning
                if "from sqlalchemy.ext.declarative import declarative_base" in content:
                    content = content.replace(
                        "from sqlalchemy.ext.declarative import declarative_base",
                        "from sqlalchemy.orm import declarative_base"
                    )
                    
                    with open(test_models_path, "w") as f:
                        f.write(content)
                    
                    self.log_fix("Fixed SQLAlchemy deprecation warning in test_models.py")
            
            # Ensure test database is properly set up
            if not os.path.exists("test.db"):
                # Create test database
                result = subprocess.run([sys.executable, "-c", 
                    "from app.database import engine, Base; Base.metadata.create_all(bind=engine)"],
                    capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.log_fix("Created test database")
                else:
                    self.log_issue(f"Failed to create test database: {result.stderr}", "medium")
            
        except Exception as e:
            self.log_issue(f"Failed to fix backend test issues: {e}", "medium")
        finally:
            os.chdir("..")
    
    def optimize_database_performance(self):
        """Optimize database performance"""
        logger.info("🔧 Optimizing database performance...")
        
        try:
            os.chdir("backend")
            
            # Check if we need to run migrations
            result = subprocess.run([sys.executable, "-m", "alembic", "current"], 
                                  capture_output=True, text=True)
            
            if "head" not in result.stdout:
                # Run migrations
                migration_result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                                                capture_output=True, text=True)
                
                if migration_result.returncode == 0:
                    self.log_fix("Applied database migrations")
                else:
                    self.log_issue(f"Failed to apply migrations: {migration_result.stderr}", "medium")
            
            # Check database indexes
            db_path = "reverse_coach.db"
            if os.path.exists(db_path):
                # Run ANALYZE to update statistics
                result = subprocess.run([sys.executable, "-c", 
                    "import sqlite3; conn = sqlite3.connect('reverse_coach.db'); conn.execute('ANALYZE'); conn.close()"],
                    capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.log_fix("Updated database statistics")
            
        except Exception as e:
            self.log_issue(f"Failed to optimize database: {e}", "medium")
        finally:
            os.chdir("..")
    
    def validate_environment_setup(self):
        """Validate environment setup"""
        logger.info("🔍 Validating environment setup...")
        
        # Check Python version
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
            self.log_issue("Python version is too old (< 3.8)", "high")
        else:
            self.log_fix("Python version is compatible")
        
        # Check Node.js version
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                node_version = result.stdout.strip()
                self.log_fix(f"Node.js version: {node_version}")
            else:
                self.log_issue("Node.js not found", "high")
        except FileNotFoundError:
            self.log_issue("Node.js not installed", "high")
        
        # Check required environment files
        env_files = [".env", "backend/.env", "frontend/.env.example"]
        for env_file in env_files:
            if os.path.exists(env_file):
                self.log_fix(f"Environment file exists: {env_file}")
            else:
                self.log_issue(f"Missing environment file: {env_file}", "medium")
    
    def create_performance_optimizations(self):
        """Create performance optimization configurations"""
        logger.info("🚀 Creating performance optimizations...")
        
        # Create backend performance config
        backend_perf_config = """
# Performance Configuration for Backend
import os

# Database connection pooling
DATABASE_POOL_SIZE = int(os.getenv("DATABASE_POOL_SIZE", "10"))
DATABASE_MAX_OVERFLOW = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))

# Cache configuration
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "1000"))

# Rate limiting
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
RATE_LIMIT_BURST = int(os.getenv("RATE_LIMIT_BURST", "10"))

# API timeouts
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
GITHUB_API_TIMEOUT = int(os.getenv("GITHUB_API_TIMEOUT", "10"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
"""
        
        try:
            with open("backend/app/performance_config.py", "w") as f:
                f.write(backend_perf_config)
            self.log_fix("Created backend performance configuration")
        except Exception as e:
            self.log_issue(f"Failed to create performance config: {e}", "medium")
        
        # Create frontend performance optimizations
        frontend_perf_config = """
// Performance optimizations for frontend
export const PERFORMANCE_CONFIG = {
  // API request timeouts
  API_TIMEOUT: 30000,
  
  // Debounce delays
  SEARCH_DEBOUNCE: 300,
  INPUT_DEBOUNCE: 150,
  
  // Cache settings
  CACHE_TTL: 5 * 60 * 1000, // 5 minutes
  
  // Pagination
  DEFAULT_PAGE_SIZE: 20,
  MAX_PAGE_SIZE: 100,
  
  // Retry settings
  MAX_RETRIES: 3,
  RETRY_DELAY: 1000,
};
"""
        
        try:
            with open("frontend/src/config/performance.ts", "w") as f:
                f.write(frontend_perf_config)
            self.log_fix("Created frontend performance configuration")
        except Exception as e:
            self.log_issue(f"Failed to create frontend performance config: {e}", "medium")
    
    def run_comprehensive_fixes(self):
        """Run all fixes"""
        logger.info("🚀 Starting comprehensive integration fixes...")
        
        fixes = [
            ("Environment Validation", self.validate_environment_setup),
            ("Backend Test Issues", self.fix_backend_test_issues),
            ("Database Performance", self.optimize_database_performance),
            ("React Version Conflicts", self.fix_react_version_conflicts),
            ("Performance Optimizations", self.create_performance_optimizations),
        ]
        
        for fix_name, fix_func in fixes:
            logger.info(f"\n--- {fix_name} ---")
            try:
                fix_func()
            except Exception as e:
                self.log_issue(f"Failed to apply {fix_name}: {e}", "high")
        
        self.generate_fix_report()
    
    def generate_fix_report(self):
        """Generate comprehensive fix report"""
        logger.info("\n" + "="*80)
        logger.info("🔧 INTEGRATION FIXES REPORT")
        logger.info("="*80)
        
        logger.info(f"Issues Found: {len(self.issues_found)}")
        logger.info(f"Fixes Applied: {len(self.fixes_applied)}")
        
        if self.issues_found:
            logger.info("\n❌ ISSUES FOUND:")
            for issue in self.issues_found:
                logger.info(f"  [{issue['severity'].upper()}] {issue['issue']}")
        
        if self.fixes_applied:
            logger.info("\n✅ FIXES APPLIED:")
            for fix in self.fixes_applied:
                logger.info(f"  • {fix}")
        
        # Recommendations
        critical_issues = [i for i in self.issues_found if i['severity'] == 'critical']
        high_issues = [i for i in self.issues_found if i['severity'] == 'high']
        
        logger.info("\n💡 RECOMMENDATIONS:")
        if critical_issues:
            logger.info("  ❌ Critical issues found - system may not function properly")
        elif high_issues:
            logger.info("  ⚠️  High priority issues found - address before production")
        elif self.issues_found:
            logger.info("  ⚠️  Minor issues found - consider addressing for better performance")
        else:
            logger.info("  ✅ No critical issues found - system should function properly")
        
        logger.info("="*80)

def main():
    """Main fix runner"""
    fixer = IntegrationIssueFixer()
    fixer.run_comprehensive_fixes()

if __name__ == "__main__":
    main()