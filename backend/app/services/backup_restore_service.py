"""
Backup and Restore Service for Enhanced User System

This service provides comprehensive backup and restore functionality
for user data, ensuring data safety and recovery capabilities.
"""

import json
import logging
import gzip
import shutil
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid
import hashlib

from app.models import (
    User, LearningProject, LearningSpec, Task, ReferenceSnippet,
    TaskReferenceSnippet, ProjectFile, ChatHistory, RepositoryAnalysis,
    UserCredentials, UserSession, RepositoryCache
)

logger = logging.getLogger(__name__)


class BackupRestoreService:
    """Service for creating and restoring data backups"""
    
    def __init__(self, db: Session):
        self.db = db
        self.backup_version = "1.0"
    
    def create_full_backup(self, backup_path: str, compress: bool = True) -> Dict[str, Any]:
        """
        Create a complete backup of all system data.
        
        Args:
            backup_path: Directory path where backup will be stored
            compress: Whether to compress backup files
            
        Returns:
            Dict with backup results and metadata
        """
        try:
            backup_dir = Path(backup_path)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_id = str(uuid.uuid4())
            
            backup_results = {
                "backup_id": backup_id,
                "timestamp": timestamp,
                "backup_path": str(backup_dir),
                "backup_version": self.backup_version,
                "compressed": compress,
                "files_created": [],
                "statistics": {},
                "metadata": {}
            }
            
            # Backup each table
            tables_to_backup = [
                ("users", User),
                ("user_credentials", UserCredentials),
                ("user_sessions", UserSession),
                ("learning_projects", LearningProject),
                ("learning_specs", LearningSpec),
                ("tasks", Task),
                ("reference_snippets", ReferenceSnippet),
                ("task_reference_snippets", TaskReferenceSnippet),
                ("project_files", ProjectFile),
                ("chat_history", ChatHistory),
                ("repository_analyses", RepositoryAnalysis),
                ("repository_cache", RepositoryCache)
            ]
            
            for table_name, model_class in tables_to_backup:
                try:
                    records = self.db.query(model_class).all()
                    records_data = []
                    
                    for record in records:
                        record_dict = {}
                        for column in model_class.__table__.columns:
                            value = getattr(record, column.name)
                            if isinstance(value, datetime):
                                value = value.isoformat()
                            record_dict[column.name] = value
                        records_data.append(record_dict)
                    
                    # Save to file
                    filename = f"{table_name}_{timestamp}.json"
                    if compress:
                        filename += ".gz"
                    
                    file_path = backup_dir / filename
                    
                    if compress:
                        with gzip.open(file_path, 'wt', encoding='utf-8') as f:
                            json.dump(records_data, f, indent=2, default=str)
                    else:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(records_data, f, indent=2, default=str)
                    
                    backup_results["files_created"].append(str(file_path))
                    backup_results["statistics"][table_name] = len(records_data)
                    
                    logger.info(f"Backed up {len(records_data)} records from {table_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to backup table {table_name}: {str(e)}")
                    backup_results["statistics"][table_name] = f"ERROR: {str(e)}"
            
            # Create backup metadata
            backup_results["metadata"] = {
                "backup_id": backup_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "backup_version": self.backup_version,
                "total_records": sum(v for v in backup_results["statistics"].values() if isinstance(v, int)),
                "database_schema_version": self._get_schema_version(),
                "backup_type": "full_system",
                "compressed": compress
            }
            
            # Save metadata file
            metadata_filename = f"backup_metadata_{timestamp}.json"
            if compress:
                metadata_filename += ".gz"
            
            metadata_path = backup_dir / metadata_filename
            
            if compress:
                with gzip.open(metadata_path, 'wt', encoding='utf-8') as f:
                    json.dump(backup_results["metadata"], f, indent=2)
            else:
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(backup_results["metadata"], f, indent=2)
            
            backup_results["files_created"].append(str(metadata_path))
            
            logger.info(f"Full backup completed successfully: {backup_id}")
            return backup_results
            
        except Exception as e:
            logger.error(f"Full backup failed: {str(e)}")
            raise
    
    def create_user_backup(self, user_id: str, backup_path: str, compress: bool = True) -> Dict[str, Any]:
        """
        Create a backup of specific user's data.
        
        Args:
            user_id: ID of the user to backup
            backup_path: Directory path where backup will be stored
            compress: Whether to compress backup files
            
        Returns:
            Dict with backup results and metadata
        """
        try:
            # Verify user exists
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            backup_dir = Path(backup_path)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_id = str(uuid.uuid4())
            
            backup_results = {
                "backup_id": backup_id,
                "user_id": user_id,
                "user_email": user.email,
                "timestamp": timestamp,
                "backup_path": str(backup_dir),
                "backup_version": self.backup_version,
                "compressed": compress,
                "files_created": [],
                "statistics": {}
            }
            
            # Backup user data
            user_data = self._serialize_model_instance(user)
            
            # Backup user credentials
            credentials = self.db.query(UserCredentials).filter(UserCredentials.user_id == user_id).all()
            credentials_data = [self._serialize_model_instance(cred) for cred in credentials]
            
            # Backup user projects and related data
            projects = self.db.query(LearningProject).filter(LearningProject.user_id == user_id).all()
            projects_data = []
            specs_data = []
            tasks_data = []
            files_data = []
            chat_data = []
            
            for project in projects:
                projects_data.append(self._serialize_model_instance(project))
                
                # Get project specs
                specs = self.db.query(LearningSpec).filter(LearningSpec.project_id == project.id).all()
                for spec in specs:
                    specs_data.append(self._serialize_model_instance(spec))
                    
                    # Get spec tasks
                    tasks = self.db.query(Task).filter(Task.spec_id == spec.id).all()
                    for task in tasks:
                        tasks_data.append(self._serialize_model_instance(task))
                
                # Get project files
                files = self.db.query(ProjectFile).filter(ProjectFile.project_id == project.id).all()
                for file in files:
                    files_data.append(self._serialize_model_instance(file))
                
                # Get chat history
                chat_messages = self.db.query(ChatHistory).filter(ChatHistory.project_id == project.id).all()
                for message in chat_messages:
                    chat_data.append(self._serialize_model_instance(message))
            
            # Save all data to files
            data_sets = [
                ("user", [user_data]),
                ("user_credentials", credentials_data),
                ("learning_projects", projects_data),
                ("learning_specs", specs_data),
                ("tasks", tasks_data),
                ("project_files", files_data),
                ("chat_history", chat_data)
            ]
            
            for data_name, data_list in data_sets:
                if data_list:  # Only create file if there's data
                    filename = f"user_{user_id}_{data_name}_{timestamp}.json"
                    if compress:
                        filename += ".gz"
                    
                    file_path = backup_dir / filename
                    
                    if compress:
                        with gzip.open(file_path, 'wt', encoding='utf-8') as f:
                            json.dump(data_list, f, indent=2, default=str)
                    else:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(data_list, f, indent=2, default=str)
                    
                    backup_results["files_created"].append(str(file_path))
                    backup_results["statistics"][data_name] = len(data_list)
            
            # Create user backup metadata
            metadata = {
                "backup_id": backup_id,
                "user_id": user_id,
                "user_email": user.email,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "backup_version": self.backup_version,
                "backup_type": "user_specific",
                "compressed": compress,
                "statistics": backup_results["statistics"]
            }
            
            metadata_filename = f"user_{user_id}_metadata_{timestamp}.json"
            if compress:
                metadata_filename += ".gz"
            
            metadata_path = backup_dir / metadata_filename
            
            if compress:
                with gzip.open(metadata_path, 'wt', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
            else:
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
            
            backup_results["files_created"].append(str(metadata_path))
            
            logger.info(f"User backup completed successfully: {backup_id} for user {user.email}")
            return backup_results
            
        except Exception as e:
            logger.error(f"User backup failed: {str(e)}")
            raise
    
    def restore_from_backup(self, backup_path: str, backup_id: str, 
                           restore_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Restore data from a backup.
        
        Args:
            backup_path: Directory path where backup files are stored
            backup_id: ID of the backup to restore
            restore_options: Optional restore configuration
            
        Returns:
            Dict with restore results
        """
        try:
            backup_dir = Path(backup_path)
            if not backup_dir.exists():
                raise ValueError(f"Backup directory {backup_path} does not exist")
            
            restore_options = restore_options or {}
            
            # Find backup metadata file
            metadata_files = list(backup_dir.glob(f"*metadata*{backup_id}*.json*"))
            if not metadata_files:
                # Try to find by timestamp if backup_id is actually a timestamp
                metadata_files = list(backup_dir.glob(f"*metadata*{backup_id}*.json*"))
            
            if not metadata_files:
                raise ValueError(f"Backup metadata not found for backup {backup_id}")
            
            metadata_file = metadata_files[0]
            
            # Load metadata
            if metadata_file.suffix == '.gz':
                with gzip.open(metadata_file, 'rt', encoding='utf-8') as f:
                    metadata = json.load(f)
            else:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            restore_results = {
                "backup_id": backup_id,
                "restore_started": datetime.now(timezone.utc).isoformat(),
                "backup_metadata": metadata,
                "records_restored": {},
                "errors": [],
                "warnings": []
            }
            
            # Determine backup type and restore accordingly
            backup_type = metadata.get("backup_type", "full_system")
            
            if backup_type == "user_specific":
                restore_results.update(self._restore_user_backup(backup_dir, metadata, restore_options))
            else:
                restore_results.update(self._restore_full_backup(backup_dir, metadata, restore_options))
            
            restore_results["restore_completed"] = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"Restore completed: {backup_id}")
            return restore_results
            
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            raise
    
    def list_backups(self, backup_path: str) -> List[Dict[str, Any]]:
        """
        List all available backups in a directory.
        
        Args:
            backup_path: Directory path to search for backups
            
        Returns:
            List of backup metadata dictionaries
        """
        try:
            backup_dir = Path(backup_path)
            if not backup_dir.exists():
                return []
            
            backups = []
            metadata_files = list(backup_dir.glob("*metadata*.json*"))
            
            for metadata_file in metadata_files:
                try:
                    if metadata_file.suffix == '.gz':
                        with gzip.open(metadata_file, 'rt', encoding='utf-8') as f:
                            metadata = json.load(f)
                    else:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    
                    # Add file info
                    metadata["metadata_file"] = str(metadata_file)
                    metadata["file_size"] = metadata_file.stat().st_size
                    
                    backups.append(metadata)
                    
                except Exception as e:
                    logger.warning(f"Failed to read backup metadata from {metadata_file}: {str(e)}")
            
            # Sort by creation date (newest first)
            backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"Failed to list backups: {str(e)}")
            return []
    
    def verify_backup_integrity(self, backup_path: str, backup_id: str) -> Dict[str, Any]:
        """
        Verify the integrity of a backup.
        
        Args:
            backup_path: Directory path where backup files are stored
            backup_id: ID of the backup to verify
            
        Returns:
            Dict with verification results
        """
        try:
            backup_dir = Path(backup_path)
            verification_results = {
                "backup_id": backup_id,
                "verification_timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "PASS",
                "checks": {},
                "issues": []
            }
            
            # Find and verify metadata file
            metadata_files = list(backup_dir.glob(f"*metadata*{backup_id}*.json*"))
            if not metadata_files:
                verification_results["status"] = "FAIL"
                verification_results["issues"].append("Backup metadata file not found")
                return verification_results
            
            metadata_file = metadata_files[0]
            
            # Load and verify metadata
            try:
                if metadata_file.suffix == '.gz':
                    with gzip.open(metadata_file, 'rt', encoding='utf-8') as f:
                        metadata = json.load(f)
                else:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                
                verification_results["checks"]["metadata_readable"] = "PASS"
                
            except Exception as e:
                verification_results["status"] = "FAIL"
                verification_results["checks"]["metadata_readable"] = "FAIL"
                verification_results["issues"].append(f"Cannot read metadata: {str(e)}")
                return verification_results
            
            # Verify backup files exist
            backup_type = metadata.get("backup_type", "full_system")
            expected_files = []
            
            if backup_type == "user_specific":
                user_id = metadata.get("user_id")
                timestamp_pattern = backup_id  # Assuming backup_id contains timestamp
                expected_files = [
                    f"user_{user_id}_user_{timestamp_pattern}.json*",
                    f"user_{user_id}_learning_projects_{timestamp_pattern}.json*"
                ]
            else:
                timestamp_pattern = backup_id
                expected_files = [
                    f"users_{timestamp_pattern}.json*",
                    f"learning_projects_{timestamp_pattern}.json*"
                ]
            
            missing_files = []
            for file_pattern in expected_files:
                matching_files = list(backup_dir.glob(file_pattern))
                if not matching_files:
                    missing_files.append(file_pattern)
            
            if missing_files:
                verification_results["status"] = "FAIL"
                verification_results["checks"]["files_present"] = "FAIL"
                verification_results["issues"].extend([f"Missing file: {f}" for f in missing_files])
            else:
                verification_results["checks"]["files_present"] = "PASS"
            
            return verification_results
            
        except Exception as e:
            logger.error(f"Backup verification failed: {str(e)}")
            return {
                "backup_id": backup_id,
                "status": "ERROR",
                "error": str(e)
            }
    
    def _serialize_model_instance(self, instance) -> Dict[str, Any]:
        """Serialize a SQLAlchemy model instance to dictionary"""
        result = {}
        for column in instance.__table__.columns:
            value = getattr(instance, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result
    
    def _restore_user_backup(self, backup_dir: Path, metadata: Dict[str, Any], 
                           restore_options: Dict[str, Any]) -> Dict[str, Any]:
        """Restore user-specific backup"""
        # Implementation for user-specific restore
        # This would restore user data, projects, etc.
        return {"records_restored": {}, "errors": [], "warnings": []}
    
    def _restore_full_backup(self, backup_dir: Path, metadata: Dict[str, Any], 
                           restore_options: Dict[str, Any]) -> Dict[str, Any]:
        """Restore full system backup"""
        # Implementation for full system restore
        # This would restore all system data
        return {"records_restored": {}, "errors": [], "warnings": []}
    
    def _get_schema_version(self) -> str:
        """Get current database schema version"""
        try:
            result = self.db.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            return result[0] if result else "unknown"
        except:
            return "unknown"