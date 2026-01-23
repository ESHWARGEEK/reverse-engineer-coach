"""
Data Validation Service for Enhanced User System

This service provides comprehensive data validation and integrity checking
for the multi-tenant user system, ensuring data consistency and security.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_
import re
import json

from app.models import (
    User, LearningProject, LearningSpec, Task, ReferenceSnippet,
    TaskReferenceSnippet, ProjectFile, ChatHistory, RepositoryAnalysis,
    UserCredentials, UserSession, RepositoryCache
)

logger = logging.getLogger(__name__)


class DataValidationService:
    """Service for comprehensive data validation and integrity checking"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def validate_user_data(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate user data integrity and consistency.
        
        Args:
            user_id: Optional specific user ID to validate, if None validates all users
            
        Returns:
            Dict with validation results
        """
        validation_results = {
            "validation_type": "user_data",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "status": "PASS",
            "checks": {},
            "issues": [],
            "warnings": []
        }
        
        try:
            # Build user query
            user_query = self.db.query(User)
            if user_id:
                user_query = user_query.filter(User.id == user_id)
            
            users = user_query.all()
            
            for user in users:
                user_issues = []
                user_warnings = []
                
                # Check 1: Email format validation
                if not self._is_valid_email(user.email):
                    user_issues.append(f"Invalid email format: {user.email}")
                
                # Check 2: Password hash validation
                if not user.hashed_password or len(user.hashed_password) < 50:
                    user_issues.append("Invalid or weak password hash")
                
                # Check 3: User activity validation
                if user.is_active is None:
                    user_warnings.append("User active status is null")
                
                # Check 4: API credentials validation
                if user.github_token and not self._is_encrypted_token(user.github_token):
                    user_warnings.append("GitHub token appears to be unencrypted")
                
                if user.openai_api_key and not self._is_encrypted_token(user.openai_api_key):
                    user_warnings.append("OpenAI API key appears to be unencrypted")
                
                # Check 5: Preferred language validation
                if user.preferred_language and user.preferred_language not in [
                    'python', 'javascript', 'typescript', 'java', 'go', 'rust', 'cpp', 'csharp'
                ]:
                    user_warnings.append(f"Unusual preferred language: {user.preferred_language}")
                
                # Check 6: JSON field validation
                if user.preferred_frameworks:
                    if not isinstance(user.preferred_frameworks, (list, dict)):
                        user_issues.append("Invalid preferred_frameworks format")
                
                if user.learning_preferences:
                    if not isinstance(user.learning_preferences, dict):
                        user_issues.append("Invalid learning_preferences format")
                
                # Store user-specific results
                if user_issues or user_warnings:
                    validation_results["checks"][f"user_{user.id}"] = {
                        "email": user.email,
                        "issues": user_issues,
                        "warnings": user_warnings
                    }
                    
                    if user_issues:
                        validation_results["status"] = "FAIL"
                        validation_results["issues"].extend([f"User {user.email}: {issue}" for issue in user_issues])
                    
                    if user_warnings:
                        validation_results["warnings"].extend([f"User {user.email}: {warning}" for warning in user_warnings])
            
            return validation_results
            
        except Exception as e:
            logger.error(f"User data validation failed: {str(e)}")
            validation_results["status"] = "ERROR"
            validation_results["issues"].append(f"Validation error: {str(e)}")
            return validation_results
    
    def validate_project_data(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate learning project data integrity.
        
        Args:
            user_id: Optional specific user ID to validate projects for
            
        Returns:
            Dict with validation results
        """
        validation_results = {
            "validation_type": "project_data",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "status": "PASS",
            "checks": {},
            "issues": [],
            "warnings": []
        }
        
        try:
            # Build project query
            project_query = self.db.query(LearningProject)
            if user_id:
                project_query = project_query.filter(LearningProject.user_id == user_id)
            
            projects = project_query.all()
            
            for project in projects:
                project_issues = []
                project_warnings = []
                
                # Check 1: Required fields
                if not project.title or len(project.title.strip()) == 0:
                    project_issues.append("Empty or missing title")
                
                if not project.target_repository:
                    project_issues.append("Missing target repository")
                elif not self._is_valid_repository_url(project.target_repository):
                    project_warnings.append(f"Invalid repository URL format: {project.target_repository}")
                
                if not project.architecture_topic:
                    project_issues.append("Missing architecture topic")
                
                # Check 2: User association
                if not project.user_id:
                    project_issues.append("Project not associated with any user")
                else:
                    # Verify user exists
                    user_exists = self.db.query(User).filter(User.id == project.user_id).first()
                    if not user_exists:
                        project_issues.append(f"Associated user {project.user_id} does not exist")
                
                # Check 3: Status validation
                valid_statuses = ['created', 'analyzing', 'ready', 'in_progress', 'completed', 'failed']
                if project.status not in valid_statuses:
                    project_issues.append(f"Invalid status: {project.status}")
                
                # Check 4: Progress tracking validation
                if project.total_tasks is not None and project.total_tasks < 0:
                    project_issues.append("Negative total_tasks value")
                
                if project.completed_tasks is not None and project.completed_tasks < 0:
                    project_issues.append("Negative completed_tasks value")
                
                if (project.total_tasks is not None and project.completed_tasks is not None and 
                    project.completed_tasks > project.total_tasks):
                    project_issues.append("Completed tasks exceed total tasks")
                
                if (project.completion_percentage is not None and 
                    (project.completion_percentage < 0 or project.completion_percentage > 100)):
                    project_issues.append("Invalid completion percentage")
                
                # Check 5: Language and framework validation
                if project.implementation_language and project.implementation_language not in [
                    'python', 'javascript', 'typescript', 'java', 'go', 'rust', 'cpp', 'csharp'
                ]:
                    project_warnings.append(f"Unusual implementation language: {project.implementation_language}")
                
                # Check 6: JSON field validation
                if project.preferred_frameworks and not isinstance(project.preferred_frameworks, list):
                    project_issues.append("Invalid preferred_frameworks format")
                
                if project.language_specific_config and not isinstance(project.language_specific_config, dict):
                    project_issues.append("Invalid language_specific_config format")
                
                if project.discovery_metadata and not isinstance(project.discovery_metadata, dict):
                    project_issues.append("Invalid discovery_metadata format")
                
                # Store project-specific results
                if project_issues or project_warnings:
                    validation_results["checks"][f"project_{project.id}"] = {
                        "title": project.title,
                        "user_id": project.user_id,
                        "issues": project_issues,
                        "warnings": project_warnings
                    }
                    
                    if project_issues:
                        validation_results["status"] = "FAIL"
                        validation_results["issues"].extend([f"Project {project.title}: {issue}" for issue in project_issues])
                    
                    if project_warnings:
                        validation_results["warnings"].extend([f"Project {project.title}: {warning}" for warning in project_warnings])
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Project data validation failed: {str(e)}")
            validation_results["status"] = "ERROR"
            validation_results["issues"].append(f"Validation error: {str(e)}")
            return validation_results
    
    def validate_foreign_key_integrity(self) -> Dict[str, Any]:
        """
        Validate foreign key relationships and referential integrity.
        
        Returns:
            Dict with validation results
        """
        validation_results = {
            "validation_type": "foreign_key_integrity",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "PASS",
            "checks": {},
            "issues": []
        }
        
        try:
            # Check 1: Projects with invalid user_id
            invalid_user_refs = self.db.execute(text("""
                SELECT lp.id, lp.title, lp.user_id 
                FROM learning_projects lp 
                LEFT JOIN users u ON lp.user_id = u.id 
                WHERE lp.user_id IS NOT NULL AND u.id IS NULL
            """)).fetchall()
            
            validation_results["checks"]["invalid_user_references"] = {
                "count": len(invalid_user_refs),
                "description": "Projects referencing non-existent users",
                "status": "PASS" if len(invalid_user_refs) == 0 else "FAIL"
            }
            
            if invalid_user_refs:
                validation_results["status"] = "FAIL"
                for row in invalid_user_refs:
                    validation_results["issues"].append(
                        f"Project '{row.title}' ({row.id}) references non-existent user {row.user_id}"
                    )
            
            # Check 2: Specs with invalid project_id
            invalid_project_refs = self.db.execute(text("""
                SELECT ls.id, ls.title, ls.project_id 
                FROM learning_specs ls 
                LEFT JOIN learning_projects lp ON ls.project_id = lp.id 
                WHERE lp.id IS NULL
            """)).fetchall()
            
            validation_results["checks"]["invalid_project_references"] = {
                "count": len(invalid_project_refs),
                "description": "Specs referencing non-existent projects",
                "status": "PASS" if len(invalid_project_refs) == 0 else "FAIL"
            }
            
            if invalid_project_refs:
                validation_results["status"] = "FAIL"
                for row in invalid_project_refs:
                    validation_results["issues"].append(
                        f"Spec '{row.title}' ({row.id}) references non-existent project {row.project_id}"
                    )
            
            # Check 3: Tasks with invalid spec_id
            invalid_spec_refs = self.db.execute(text("""
                SELECT t.id, t.title, t.spec_id 
                FROM tasks t 
                LEFT JOIN learning_specs ls ON t.spec_id = ls.id 
                WHERE ls.id IS NULL
            """)).fetchall()
            
            validation_results["checks"]["invalid_spec_references"] = {
                "count": len(invalid_spec_refs),
                "description": "Tasks referencing non-existent specs",
                "status": "PASS" if len(invalid_spec_refs) == 0 else "FAIL"
            }
            
            if invalid_spec_refs:
                validation_results["status"] = "FAIL"
                for row in invalid_spec_refs:
                    validation_results["issues"].append(
                        f"Task '{row.title}' ({row.id}) references non-existent spec {row.spec_id}"
                    )
            
            # Check 4: User credentials with invalid user_id
            invalid_cred_refs = self.db.execute(text("""
                SELECT uc.id, uc.user_id 
                FROM user_credentials uc 
                LEFT JOIN users u ON uc.user_id = u.id 
                WHERE u.id IS NULL
            """)).fetchall()
            
            validation_results["checks"]["invalid_credential_references"] = {
                "count": len(invalid_cred_refs),
                "description": "User credentials referencing non-existent users",
                "status": "PASS" if len(invalid_cred_refs) == 0 else "FAIL"
            }
            
            if invalid_cred_refs:
                validation_results["status"] = "FAIL"
                for row in invalid_cred_refs:
                    validation_results["issues"].append(
                        f"User credentials ({row.id}) reference non-existent user {row.user_id}"
                    )
            
            # Check 5: User sessions with invalid user_id
            invalid_session_refs = self.db.execute(text("""
                SELECT us.id, us.user_id 
                FROM user_sessions us 
                LEFT JOIN users u ON us.user_id = u.id 
                WHERE u.id IS NULL
            """)).fetchall()
            
            validation_results["checks"]["invalid_session_references"] = {
                "count": len(invalid_session_refs),
                "description": "User sessions referencing non-existent users",
                "status": "PASS" if len(invalid_session_refs) == 0 else "FAIL"
            }
            
            if invalid_session_refs:
                validation_results["status"] = "FAIL"
                for row in invalid_session_refs:
                    validation_results["issues"].append(
                        f"User session ({row.id}) references non-existent user {row.user_id}"
                    )
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Foreign key integrity validation failed: {str(e)}")
            validation_results["status"] = "ERROR"
            validation_results["issues"].append(f"Validation error: {str(e)}")
            return validation_results
    
    def validate_data_isolation(self) -> Dict[str, Any]:
        """
        Validate that user data is properly isolated (no cross-user data leakage).
        
        Returns:
            Dict with validation results
        """
        validation_results = {
            "validation_type": "data_isolation",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "PASS",
            "checks": {},
            "issues": [],
            "warnings": []
        }
        
        try:
            # Check 1: Projects without user_id (orphaned projects)
            orphaned_projects = self.db.query(LearningProject).filter(
                LearningProject.user_id.is_(None)
            ).count()
            
            validation_results["checks"]["orphaned_projects"] = {
                "count": orphaned_projects,
                "description": "Projects without user association",
                "status": "PASS" if orphaned_projects == 0 else "FAIL"
            }
            
            if orphaned_projects > 0:
                validation_results["status"] = "FAIL"
                validation_results["issues"].append(f"{orphaned_projects} projects are not associated with any user")
            
            # Check 2: Verify all users have unique emails
            duplicate_emails = self.db.execute(text("""
                SELECT email, COUNT(*) as count 
                FROM users 
                GROUP BY email 
                HAVING COUNT(*) > 1
            """)).fetchall()
            
            validation_results["checks"]["duplicate_emails"] = {
                "count": len(duplicate_emails),
                "description": "Users with duplicate email addresses",
                "status": "PASS" if len(duplicate_emails) == 0 else "FAIL"
            }
            
            if duplicate_emails:
                validation_results["status"] = "FAIL"
                for row in duplicate_emails:
                    validation_results["issues"].append(f"Duplicate email '{row.email}' used by {row.count} users")
            
            # Check 3: Verify project file isolation
            cross_user_files = self.db.execute(text("""
                SELECT pf.id, pf.project_id, lp.user_id as project_user, u.email
                FROM project_files pf
                JOIN learning_projects lp ON pf.project_id = lp.id
                JOIN users u ON lp.user_id = u.id
                WHERE EXISTS (
                    SELECT 1 FROM learning_projects lp2 
                    WHERE lp2.id = pf.project_id AND lp2.user_id != lp.user_id
                )
            """)).fetchall()
            
            validation_results["checks"]["cross_user_files"] = {
                "count": len(cross_user_files),
                "description": "Project files with inconsistent user ownership",
                "status": "PASS" if len(cross_user_files) == 0 else "FAIL"
            }
            
            if cross_user_files:
                validation_results["status"] = "FAIL"
                validation_results["issues"].append(f"{len(cross_user_files)} project files have inconsistent user ownership")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Data isolation validation failed: {str(e)}")
            validation_results["status"] = "ERROR"
            validation_results["issues"].append(f"Validation error: {str(e)}")
            return validation_results
    
    def run_comprehensive_validation(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Run all validation checks and return comprehensive results.
        
        Args:
            user_id: Optional specific user ID to validate
            
        Returns:
            Dict with comprehensive validation results
        """
        comprehensive_results = {
            "validation_timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "overall_status": "PASS",
            "validation_checks": {},
            "summary": {
                "total_issues": 0,
                "total_warnings": 0,
                "checks_passed": 0,
                "checks_failed": 0,
                "checks_error": 0
            }
        }
        
        # Run all validation checks
        validations = [
            ("user_data", self.validate_user_data),
            ("project_data", self.validate_project_data),
            ("foreign_key_integrity", self.validate_foreign_key_integrity),
            ("data_isolation", self.validate_data_isolation)
        ]
        
        for validation_name, validation_func in validations:
            try:
                if validation_name in ["user_data", "project_data"] and user_id:
                    result = validation_func(user_id)
                else:
                    result = validation_func()
                
                comprehensive_results["validation_checks"][validation_name] = result
                
                # Update summary
                if result["status"] == "PASS":
                    comprehensive_results["summary"]["checks_passed"] += 1
                elif result["status"] == "FAIL":
                    comprehensive_results["summary"]["checks_failed"] += 1
                    comprehensive_results["overall_status"] = "FAIL"
                else:  # ERROR
                    comprehensive_results["summary"]["checks_error"] += 1
                    comprehensive_results["overall_status"] = "ERROR"
                
                comprehensive_results["summary"]["total_issues"] += len(result.get("issues", []))
                comprehensive_results["summary"]["total_warnings"] += len(result.get("warnings", []))
                
            except Exception as e:
                logger.error(f"Validation {validation_name} failed: {str(e)}")
                comprehensive_results["validation_checks"][validation_name] = {
                    "status": "ERROR",
                    "error": str(e)
                }
                comprehensive_results["summary"]["checks_error"] += 1
                comprehensive_results["overall_status"] = "ERROR"
        
        return comprehensive_results
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email format"""
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _is_valid_repository_url(self, url: str) -> bool:
        """Validate repository URL format"""
        if not url:
            return False
        # Basic GitHub URL validation
        github_pattern = r'^https://github\.com/[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+/?$'
        return re.match(github_pattern, url) is not None
    
    def _is_encrypted_token(self, token: str) -> bool:
        """Check if a token appears to be encrypted (basic heuristic)"""
        if not token:
            return False
        # Encrypted tokens should be longer and contain non-readable characters
        return len(token) > 50 and not token.startswith(('ghp_', 'sk-'))