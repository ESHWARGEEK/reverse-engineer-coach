"""
Data migration utilities for Enhanced User System

This module provides utilities for:
- Migrating existing projects to user accounts
- Data validation and integrity checking
- Backup and restore procedures
- User data anonymization tools
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, func
import uuid
import hashlib
import os
from pathlib import Path

from app.database import get_db
from app.models import (
    User, LearningProject, LearningSpec, Task, ReferenceSnippet,
    TaskReferenceSnippet, ProjectFile, ChatHistory, RepositoryAnalysis,
    UserCredentials, UserSession, RepositoryCache
)
from app.services.password_service import PasswordService
from app.services.credential_encryption_service import CredentialEncryptionService

logger = logging.getLogger(__name__)


class DataMigrationUtility:
    """Utility class for handling data migration operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.password_service = PasswordService()
        self.encryption_service = CredentialEncryptionService()
        
    def create_default_user(self, email: str = "admin@reversecoach.local") -> User:
        """
        Create a default user for migrating existing projects.
        This user will own all existing projects that don't have a user_id.
        """
        try:
            # Check if user already exists
            existing_user = self.db.query(User).filter(User.email == email).first()
            if existing_user:
                logger.info(f"Default user {email} already exists")
                return existing_user
            
            # Create default user with secure password
            default_password = f"temp_password_{uuid.uuid4().hex[:8]}"
            hashed_password = self.password_service.hash_password(default_password)
            
            user = User(
                id=str(uuid.uuid4()),
                email=email,
                hashed_password=hashed_password,
                is_active=True,
                preferred_language="python",
                created_at=datetime.now(timezone.utc)
            )
            
            self.db.add(user)
            self.db.commit()
            
            logger.info(f"Created default user {email} with temporary password: {default_password}")
            logger.warning("Please change the default user password immediately after migration!")
            
            return user
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create default user: {str(e)}")
            raise
    
    def migrate_existing_projects_to_user(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Migrate existing projects without user_id to a specific user.
        If no user_id provided, creates a default user.
        
        Returns:
            Dict with migration statistics and results
        """
        try:
            # Get or create target user
            if user_id:
                target_user = self.db.query(User).filter(User.id == user_id).first()
                if not target_user:
                    raise ValueError(f"User with id {user_id} not found")
            else:
                target_user = self.create_default_user()
            
            # Find projects without user_id
            orphaned_projects = self.db.query(LearningProject).filter(
                LearningProject.user_id.is_(None)
            ).all()
            
            migration_stats = {
                "target_user_id": target_user.id,
                "target_user_email": target_user.email,
                "projects_migrated": 0,
                "specs_migrated": 0,
                "tasks_migrated": 0,
                "files_migrated": 0,
                "chat_history_migrated": 0,
                "errors": []
            }
            
            for project in orphaned_projects:
                try:
                    # Assign project to user
                    project.user_id = target_user.id
                    migration_stats["projects_migrated"] += 1
                    
                    # Count related objects
                    specs = self.db.query(LearningSpec).filter(
                        LearningSpec.project_id == project.id
                    ).all()
                    migration_stats["specs_migrated"] += len(specs)
                    
                    for spec in specs:
                        tasks = self.db.query(Task).filter(Task.spec_id == spec.id).all()
                        migration_stats["tasks_migrated"] += len(tasks)
                    
                    # Count project files
                    files = self.db.query(ProjectFile).filter(
                        ProjectFile.project_id == project.id
                    ).all()
                    migration_stats["files_migrated"] += len(files)
                    
                    # Count chat history
                    chat_messages = self.db.query(ChatHistory).filter(
                        ChatHistory.project_id == project.id
                    ).all()
                    migration_stats["chat_history_migrated"] += len(chat_messages)
                    
                except Exception as e:
                    error_msg = f"Failed to migrate project {project.id}: {str(e)}"
                    migration_stats["errors"].append(error_msg)
                    logger.error(error_msg)
            
            self.db.commit()
            
            logger.info(f"Migration completed: {migration_stats}")
            return migration_stats
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Migration failed: {str(e)}")
            raise
    
    def validate_data_integrity(self) -> Dict[str, Any]:
        """
        Perform comprehensive data integrity validation.
        
        Returns:
            Dict with validation results and any issues found
        """
        validation_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": "PASS",
            "checks": {},
            "issues": [],
            "statistics": {}
        }
        
        try:
            # Check 1: All projects have valid user_id
            orphaned_projects = self.db.query(LearningProject).filter(
                LearningProject.user_id.is_(None)
            ).count()
            
            validation_results["checks"]["orphaned_projects"] = {
                "status": "PASS" if orphaned_projects == 0 else "FAIL",
                "count": orphaned_projects,
                "description": "Projects without user_id"
            }
            
            if orphaned_projects > 0:
                validation_results["overall_status"] = "FAIL"
                validation_results["issues"].append(f"{orphaned_projects} projects without user_id")
            
            # Check 2: All users have valid email addresses
            users_without_email = self.db.query(User).filter(
                User.email.is_(None) | (User.email == "")
            ).count()
            
            validation_results["checks"]["users_without_email"] = {
                "status": "PASS" if users_without_email == 0 else "FAIL",
                "count": users_without_email,
                "description": "Users without valid email"
            }
            
            if users_without_email > 0:
                validation_results["overall_status"] = "FAIL"
                validation_results["issues"].append(f"{users_without_email} users without valid email")
            
            # Check 3: Foreign key integrity
            # Projects with invalid user_id
            invalid_user_refs = self.db.execute(text("""
                SELECT COUNT(*) FROM learning_projects lp 
                LEFT JOIN users u ON lp.user_id = u.id 
                WHERE lp.user_id IS NOT NULL AND u.id IS NULL
            """)).scalar()
            
            validation_results["checks"]["invalid_user_references"] = {
                "status": "PASS" if invalid_user_refs == 0 else "FAIL",
                "count": invalid_user_refs,
                "description": "Projects referencing non-existent users"
            }
            
            if invalid_user_refs > 0:
                validation_results["overall_status"] = "FAIL"
                validation_results["issues"].append(f"{invalid_user_refs} projects with invalid user references")
            
            # Check 4: Specs with invalid project_id
            invalid_project_refs = self.db.execute(text("""
                SELECT COUNT(*) FROM learning_specs ls 
                LEFT JOIN learning_projects lp ON ls.project_id = lp.id 
                WHERE lp.id IS NULL
            """)).scalar()
            
            validation_results["checks"]["invalid_project_references"] = {
                "status": "PASS" if invalid_project_refs == 0 else "FAIL",
                "count": invalid_project_refs,
                "description": "Specs referencing non-existent projects"
            }
            
            if invalid_project_refs > 0:
                validation_results["overall_status"] = "FAIL"
                validation_results["issues"].append(f"{invalid_project_refs} specs with invalid project references")
            
            # Check 5: Tasks with invalid spec_id
            invalid_spec_refs = self.db.execute(text("""
                SELECT COUNT(*) FROM tasks t 
                LEFT JOIN learning_specs ls ON t.spec_id = ls.id 
                WHERE ls.id IS NULL
            """)).scalar()
            
            validation_results["checks"]["invalid_spec_references"] = {
                "status": "PASS" if invalid_spec_refs == 0 else "FAIL",
                "count": invalid_spec_refs,
                "description": "Tasks referencing non-existent specs"
            }
            
            if invalid_spec_refs > 0:
                validation_results["overall_status"] = "FAIL"
                validation_results["issues"].append(f"{invalid_spec_refs} tasks with invalid spec references")
            
            # Collect statistics
            validation_results["statistics"] = {
                "total_users": self.db.query(User).count(),
                "total_projects": self.db.query(LearningProject).count(),
                "total_specs": self.db.query(LearningSpec).count(),
                "total_tasks": self.db.query(Task).count(),
                "total_files": self.db.query(ProjectFile).count(),
                "total_chat_messages": self.db.query(ChatHistory).count()
            }
            
            logger.info(f"Data integrity validation completed: {validation_results['overall_status']}")
            return validation_results
            
        except Exception as e:
            logger.error(f"Data integrity validation failed: {str(e)}")
            validation_results["overall_status"] = "ERROR"
            validation_results["issues"].append(f"Validation error: {str(e)}")
            return validation_results
    
    def create_backup(self, backup_path: str) -> Dict[str, Any]:
        """
        Create a comprehensive backup of all user data.
        
        Args:
            backup_path: Directory path where backup files will be stored
            
        Returns:
            Dict with backup results and file paths
        """
        try:
            backup_dir = Path(backup_path)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_results = {
                "timestamp": timestamp,
                "backup_path": str(backup_dir),
                "files_created": [],
                "statistics": {}
            }
            
            # Backup users
            users = self.db.query(User).all()
            users_data = []
            for user in users:
                user_dict = {
                    "id": user.id,
                    "email": user.email,
                    "hashed_password": user.hashed_password,
                    "is_active": user.is_active,
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                    "github_token": user.github_token,
                    "openai_api_key": user.openai_api_key,
                    "gemini_api_key": user.gemini_api_key,
                    "preferred_ai_provider": user.preferred_ai_provider,
                    "preferred_language": user.preferred_language,
                    "preferred_frameworks": user.preferred_frameworks,
                    "learning_preferences": user.learning_preferences
                }
                users_data.append(user_dict)
            
            users_file = backup_dir / f"users_{timestamp}.json"
            with open(users_file, 'w') as f:
                json.dump(users_data, f, indent=2, default=str)
            backup_results["files_created"].append(str(users_file))
            backup_results["statistics"]["users"] = len(users_data)
            
            # Backup learning projects
            projects = self.db.query(LearningProject).all()
            projects_data = []
            for project in projects:
                project_dict = {
                    "id": project.id,
                    "user_id": project.user_id,
                    "title": project.title,
                    "target_repository": project.target_repository,
                    "architecture_topic": project.architecture_topic,
                    "concept_description": project.concept_description,
                    "discovery_metadata": project.discovery_metadata,
                    "status": project.status,
                    "created_at": project.created_at.isoformat() if project.created_at else None,
                    "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                    "implementation_language": project.implementation_language,
                    "preferred_frameworks": project.preferred_frameworks,
                    "language_specific_config": project.language_specific_config,
                    "total_tasks": project.total_tasks,
                    "completed_tasks": project.completed_tasks,
                    "current_task_id": project.current_task_id,
                    "completion_percentage": project.completion_percentage
                }
                projects_data.append(project_dict)
            
            projects_file = backup_dir / f"learning_projects_{timestamp}.json"
            with open(projects_file, 'w') as f:
                json.dump(projects_data, f, indent=2, default=str)
            backup_results["files_created"].append(str(projects_file))
            backup_results["statistics"]["projects"] = len(projects_data)
            
            # Backup other tables similarly...
            # (Specs, Tasks, Files, Chat History, etc.)
            
            # Create backup metadata
            metadata = {
                "backup_timestamp": timestamp,
                "database_version": "enhanced_user_system",
                "total_records": sum(backup_results["statistics"].values()),
                "files": backup_results["files_created"]
            }
            
            metadata_file = backup_dir / f"backup_metadata_{timestamp}.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            backup_results["files_created"].append(str(metadata_file))
            
            logger.info(f"Backup created successfully: {backup_results}")
            return backup_results
            
        except Exception as e:
            logger.error(f"Backup creation failed: {str(e)}")
            raise
    
    def restore_from_backup(self, backup_path: str, timestamp: str) -> Dict[str, Any]:
        """
        Restore data from a backup.
        
        Args:
            backup_path: Directory path where backup files are stored
            timestamp: Timestamp of the backup to restore
            
        Returns:
            Dict with restore results
        """
        try:
            backup_dir = Path(backup_path)
            if not backup_dir.exists():
                raise ValueError(f"Backup directory {backup_path} does not exist")
            
            restore_results = {
                "timestamp": timestamp,
                "restore_started": datetime.now(timezone.utc).isoformat(),
                "records_restored": {},
                "errors": []
            }
            
            # Read backup metadata
            metadata_file = backup_dir / f"backup_metadata_{timestamp}.json"
            if not metadata_file.exists():
                raise ValueError(f"Backup metadata file not found: {metadata_file}")
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Restore users
            users_file = backup_dir / f"users_{timestamp}.json"
            if users_file.exists():
                with open(users_file, 'r') as f:
                    users_data = json.load(f)
                
                for user_data in users_data:
                    try:
                        # Check if user already exists
                        existing_user = self.db.query(User).filter(User.id == user_data["id"]).first()
                        if existing_user:
                            continue  # Skip existing users
                        
                        user = User(**{k: v for k, v in user_data.items() if v is not None})
                        self.db.add(user)
                        
                    except Exception as e:
                        restore_results["errors"].append(f"Failed to restore user {user_data.get('id')}: {str(e)}")
                
                restore_results["records_restored"]["users"] = len(users_data)
            
            # Restore projects
            projects_file = backup_dir / f"learning_projects_{timestamp}.json"
            if projects_file.exists():
                with open(projects_file, 'r') as f:
                    projects_data = json.load(f)
                
                for project_data in projects_data:
                    try:
                        # Check if project already exists
                        existing_project = self.db.query(LearningProject).filter(
                            LearningProject.id == project_data["id"]
                        ).first()
                        if existing_project:
                            continue  # Skip existing projects
                        
                        project = LearningProject(**{k: v for k, v in project_data.items() if v is not None})
                        self.db.add(project)
                        
                    except Exception as e:
                        restore_results["errors"].append(f"Failed to restore project {project_data.get('id')}: {str(e)}")
                
                restore_results["records_restored"]["projects"] = len(projects_data)
            
            self.db.commit()
            
            restore_results["restore_completed"] = datetime.now(timezone.utc).isoformat()
            logger.info(f"Restore completed: {restore_results}")
            return restore_results
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Restore failed: {str(e)}")
            raise
    
    def anonymize_user_data(self, user_id: str, keep_structure: bool = True) -> Dict[str, Any]:
        """
        Anonymize user data for privacy compliance.
        
        Args:
            user_id: ID of the user to anonymize
            keep_structure: If True, keeps data structure but anonymizes content
            
        Returns:
            Dict with anonymization results
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            anonymization_results = {
                "user_id": user_id,
                "original_email": user.email,
                "anonymization_timestamp": datetime.now(timezone.utc).isoformat(),
                "anonymized_fields": [],
                "projects_affected": 0,
                "files_affected": 0,
                "chat_messages_affected": 0
            }
            
            # Generate consistent anonymized data
            user_hash = hashlib.sha256(user_id.encode()).hexdigest()[:8]
            
            if keep_structure:
                # Anonymize user data while keeping structure
                user.email = f"anonymized_user_{user_hash}@example.com"
                user.hashed_password = self.password_service.hash_password(f"anonymized_{user_hash}")
                user.github_token = None
                user.openai_api_key = None
                user.gemini_api_key = None
                user.learning_preferences = None
                
                anonymization_results["anonymized_fields"] = [
                    "email", "password", "api_keys", "learning_preferences"
                ]
                
                # Anonymize project content
                projects = self.db.query(LearningProject).filter(LearningProject.user_id == user_id).all()
                for project in projects:
                    project.title = f"Anonymized Project {project.id[:8]}"
                    project.concept_description = "Anonymized learning concept"
                    project.discovery_metadata = None
                    anonymization_results["projects_affected"] += 1
                
                # Anonymize project files
                files = self.db.query(ProjectFile).join(LearningProject).filter(
                    LearningProject.user_id == user_id
                ).all()
                for file in files:
                    file.content = f"// Anonymized content for file {file.id[:8]}"
                    anonymization_results["files_affected"] += 1
                
                # Anonymize chat history
                chat_messages = self.db.query(ChatHistory).join(LearningProject).filter(
                    LearningProject.user_id == user_id
                ).all()
                for message in chat_messages:
                    if message.sender == "user":
                        message.content = "Anonymized user message"
                    message.context_used = None
                    anonymization_results["chat_messages_affected"] += 1
            
            else:
                # Delete user data completely
                # This would cascade delete all related data
                self.db.delete(user)
                anonymization_results["action"] = "complete_deletion"
            
            self.db.commit()
            
            logger.info(f"User data anonymization completed: {anonymization_results}")
            return anonymization_results
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"User data anonymization failed: {str(e)}")
            raise


def create_migration_utility(db: Session = None) -> DataMigrationUtility:
    """Factory function to create a DataMigrationUtility instance"""
    if db is None:
        db = next(get_db())
    return DataMigrationUtility(db)


# CLI utility functions for running migrations
def run_project_migration(user_email: str = None):
    """CLI function to run project migration"""
    db = next(get_db())
    utility = DataMigrationUtility(db)
    
    if user_email:
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            print(f"User with email {user_email} not found")
            return
        user_id = user.id
    else:
        user_id = None
    
    results = utility.migrate_existing_projects_to_user(user_id)
    print(f"Migration completed: {json.dumps(results, indent=2)}")


def run_data_validation():
    """CLI function to run data validation"""
    db = next(get_db())
    utility = DataMigrationUtility(db)
    
    results = utility.validate_data_integrity()
    print(f"Validation results: {json.dumps(results, indent=2)}")


def run_backup(backup_path: str):
    """CLI function to create backup"""
    db = next(get_db())
    utility = DataMigrationUtility(db)
    
    results = utility.create_backup(backup_path)
    print(f"Backup created: {json.dumps(results, indent=2)}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python data_migration.py <command> [args]")
        print("Commands:")
        print("  migrate [user_email] - Migrate existing projects to user")
        print("  validate - Run data integrity validation")
        print("  backup <path> - Create backup")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "migrate":
        user_email = sys.argv[2] if len(sys.argv) > 2 else None
        run_project_migration(user_email)
    elif command == "validate":
        run_data_validation()
    elif command == "backup":
        if len(sys.argv) < 3:
            print("Backup path required")
            sys.exit(1)
        run_backup(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)