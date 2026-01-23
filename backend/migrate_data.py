#!/usr/bin/env python3
"""
Data Migration CLI Tool for Enhanced User System

This script provides command-line utilities for:
- Running database migrations
- Migrating existing data to user accounts
- Validating data integrity
- Creating and restoring backups
- Anonymizing user data

Usage:
    python migrate_data.py <command> [options]

Commands:
    db-migrate          - Run Alembic database migrations
    migrate-projects    - Migrate existing projects to user accounts
    validate           - Validate data integrity
    backup             - Create data backup
    restore            - Restore from backup
    anonymize          - Anonymize user data
    help               - Show this help message

Examples:
    python migrate_data.py db-migrate
    python migrate_data.py migrate-projects --user-email admin@example.com
    python migrate_data.py validate
    python migrate_data.py backup --path ./backups
    python migrate_data.py restore --path ./backups --timestamp 20260123_120000
    python migrate_data.py anonymize --user-id 12345 --keep-structure
"""

import argparse
import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime

# Add the app directory to the path
sys.path.append(os.path.dirname(__file__))

from app.database import get_db
from app.utils.data_migration import DataMigrationUtility
from alembic.config import Config
from alembic import command

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_db_migrations():
    """Run Alembic database migrations"""
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        print("✅ Database migrations completed successfully")
        return True
    except Exception as e:
        print(f"❌ Database migration failed: {str(e)}")
        return False


def migrate_projects(user_email: str = None, create_default: bool = True):
    """Migrate existing projects to user accounts"""
    try:
        db = next(get_db())
        utility = DataMigrationUtility(db)
        
        user_id = None
        if user_email:
            from app.models import User
            user = db.query(User).filter(User.email == user_email).first()
            if not user:
                if create_default:
                    print(f"User {user_email} not found. Creating default user...")
                    user = utility.create_default_user(user_email)
                    user_id = user.id
                else:
                    print(f"❌ User {user_email} not found")
                    return False
            else:
                user_id = user.id
        
        print("🔄 Starting project migration...")
        results = utility.migrate_existing_projects_to_user(user_id)
        
        print("✅ Project migration completed!")
        print(f"📊 Migration Statistics:")
        print(f"   Target User: {results['target_user_email']} ({results['target_user_id']})")
        print(f"   Projects Migrated: {results['projects_migrated']}")
        print(f"   Specs Migrated: {results['specs_migrated']}")
        print(f"   Tasks Migrated: {results['tasks_migrated']}")
        print(f"   Files Migrated: {results['files_migrated']}")
        print(f"   Chat Messages Migrated: {results['chat_history_migrated']}")
        
        if results['errors']:
            print(f"⚠️  Errors encountered:")
            for error in results['errors']:
                print(f"   - {error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Project migration failed: {str(e)}")
        return False


def validate_data():
    """Validate data integrity"""
    try:
        db = next(get_db())
        utility = DataMigrationUtility(db)
        
        print("🔍 Running data integrity validation...")
        results = utility.validate_data_integrity()
        
        status_emoji = "✅" if results['overall_status'] == "PASS" else "❌"
        print(f"{status_emoji} Validation Status: {results['overall_status']}")
        
        print(f"📊 Database Statistics:")
        for key, value in results['statistics'].items():
            print(f"   {key.replace('_', ' ').title()}: {value}")
        
        print(f"🔍 Validation Checks:")
        for check_name, check_result in results['checks'].items():
            check_emoji = "✅" if check_result['status'] == "PASS" else "❌"
            print(f"   {check_emoji} {check_result['description']}: {check_result['count']}")
        
        if results['issues']:
            print(f"⚠️  Issues Found:")
            for issue in results['issues']:
                print(f"   - {issue}")
        
        return results['overall_status'] == "PASS"
        
    except Exception as e:
        print(f"❌ Data validation failed: {str(e)}")
        return False


def create_backup(backup_path: str):
    """Create data backup"""
    try:
        db = next(get_db())
        utility = DataMigrationUtility(db)
        
        print(f"💾 Creating backup in {backup_path}...")
        results = utility.create_backup(backup_path)
        
        print("✅ Backup created successfully!")
        print(f"📁 Backup Location: {results['backup_path']}")
        print(f"🕐 Timestamp: {results['timestamp']}")
        print(f"📊 Statistics:")
        for key, value in results['statistics'].items():
            print(f"   {key.title()}: {value}")
        
        print(f"📄 Files Created:")
        for file_path in results['files_created']:
            print(f"   - {file_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Backup creation failed: {str(e)}")
        return False


def restore_backup(backup_path: str, timestamp: str):
    """Restore from backup"""
    try:
        db = next(get_db())
        utility = DataMigrationUtility(db)
        
        print(f"🔄 Restoring backup from {backup_path} (timestamp: {timestamp})...")
        results = utility.restore_from_backup(backup_path, timestamp)
        
        print("✅ Restore completed!")
        print(f"📊 Records Restored:")
        for key, value in results['records_restored'].items():
            print(f"   {key.title()}: {value}")
        
        if results['errors']:
            print(f"⚠️  Errors encountered:")
            for error in results['errors']:
                print(f"   - {error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Restore failed: {str(e)}")
        return False


def anonymize_user(user_id: str, keep_structure: bool = True):
    """Anonymize user data"""
    try:
        db = next(get_db())
        utility = DataMigrationUtility(db)
        
        action = "anonymizing" if keep_structure else "deleting"
        print(f"🔒 {action.title()} user data for user {user_id}...")
        
        results = utility.anonymize_user_data(user_id, keep_structure)
        
        print("✅ User data anonymization completed!")
        print(f"👤 Original Email: {results['original_email']}")
        print(f"🕐 Anonymization Time: {results['anonymization_timestamp']}")
        
        if keep_structure:
            print(f"📊 Data Anonymized:")
            print(f"   Fields: {', '.join(results['anonymized_fields'])}")
            print(f"   Projects Affected: {results['projects_affected']}")
            print(f"   Files Affected: {results['files_affected']}")
            print(f"   Chat Messages Affected: {results['chat_messages_affected']}")
        else:
            print("🗑️  User data completely deleted")
        
        return True
        
    except Exception as e:
        print(f"❌ User anonymization failed: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Data Migration CLI Tool for Enhanced User System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Database migration command
    subparsers.add_parser('db-migrate', help='Run Alembic database migrations')
    
    # Project migration command
    migrate_parser = subparsers.add_parser('migrate-projects', help='Migrate existing projects to user accounts')
    migrate_parser.add_argument('--user-email', help='Email of target user (creates default if not found)')
    migrate_parser.add_argument('--no-create-default', action='store_true', 
                               help='Do not create default user if target user not found')
    
    # Validation command
    subparsers.add_parser('validate', help='Validate data integrity')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create data backup')
    backup_parser.add_argument('--path', required=True, help='Backup directory path')
    
    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument('--path', required=True, help='Backup directory path')
    restore_parser.add_argument('--timestamp', required=True, help='Backup timestamp to restore')
    
    # Anonymize command
    anonymize_parser = subparsers.add_parser('anonymize', help='Anonymize user data')
    anonymize_parser.add_argument('--user-id', required=True, help='User ID to anonymize')
    anonymize_parser.add_argument('--keep-structure', action='store_true', default=True,
                                 help='Keep data structure but anonymize content (default)')
    anonymize_parser.add_argument('--delete-completely', action='store_true',
                                 help='Delete user data completely')
    
    # Help command
    subparsers.add_parser('help', help='Show help message')
    
    args = parser.parse_args()
    
    if not args.command or args.command == 'help':
        parser.print_help()
        return
    
    success = False
    
    try:
        if args.command == 'db-migrate':
            success = run_db_migrations()
        
        elif args.command == 'migrate-projects':
            success = migrate_projects(
                user_email=args.user_email,
                create_default=not args.no_create_default
            )
        
        elif args.command == 'validate':
            success = validate_data()
        
        elif args.command == 'backup':
            success = create_backup(args.path)
        
        elif args.command == 'restore':
            success = restore_backup(args.path, args.timestamp)
        
        elif args.command == 'anonymize':
            keep_structure = not args.delete_completely
            success = anonymize_user(args.user_id, keep_structure)
        
        else:
            print(f"Unknown command: {args.command}")
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Unexpected error: {str(e)}")
        logger.exception("Unexpected error occurred")
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()