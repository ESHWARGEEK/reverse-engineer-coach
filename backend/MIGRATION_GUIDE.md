# Database Migration and Data Handling Guide

This guide covers the database migration and data handling utilities for the Enhanced User System.

## Overview

The Enhanced User System includes comprehensive migration and data handling tools:

1. **Database Migration Scripts** - Alembic migrations for schema changes
2. **Data Migration Utilities** - Tools for migrating existing data to user accounts
3. **Data Validation Services** - Comprehensive data integrity checking
4. **Backup and Restore Services** - Complete data backup and recovery

## Database Migrations

### Running Migrations

Use the CLI tool to run database migrations:

```bash
# Run all pending migrations
python migrate_data.py db-migrate
```

Or use Alembic directly:

```bash
# Check current migration status
alembic current

# Run migrations to latest version
alembic upgrade head

# Rollback to previous version
alembic downgrade -1
```

### Migration Files

- `004_complete_user_system_migration.py` - Complete user system schema
- `005_add_performance_indexes.py` - Performance optimization indexes

## Data Migration

### Migrating Existing Projects

If you have existing projects without user associations, migrate them:

```bash
# Create default user and migrate all orphaned projects
python migrate_data.py migrate-projects

# Migrate to specific user
python migrate_data.py migrate-projects --user-email admin@example.com

# Don't create default user if target user doesn't exist
python migrate_data.py migrate-projects --user-email admin@example.com --no-create-default
```

### Migration Results

The migration will provide detailed statistics:
- Projects migrated
- Specs migrated  
- Tasks migrated
- Files migrated
- Chat messages migrated
- Any errors encountered

## Data Validation

### Running Validation

Validate data integrity and consistency:

```bash
# Run comprehensive validation
python migrate_data.py validate
```

### Validation Checks

The validation performs these checks:

1. **User Data Validation**
   - Email format validation
   - Password hash validation
   - API credentials encryption check
   - JSON field format validation

2. **Project Data Validation**
   - Required fields presence
   - User association validation
   - Status validation
   - Progress tracking consistency

3. **Foreign Key Integrity**
   - Projects → Users references
   - Specs → Projects references
   - Tasks → Specs references
   - Credentials → Users references

4. **Data Isolation**
   - No orphaned projects
   - Unique user emails
   - Proper user data separation

## Backup and Restore

### Creating Backups

Create comprehensive data backups:

```bash
# Create full system backup
python migrate_data.py backup --path ./backups

# The backup will be compressed and timestamped
```

### Backup Contents

Full backups include:
- All user accounts and credentials
- All learning projects and specs
- All tasks and reference snippets
- All project files and chat history
- Repository analyses and cache data

### Restoring from Backup

```bash
# Restore from backup (timestamp from backup filename)
python migrate_data.py restore --path ./backups --timestamp 20260123_120000
```

## User Data Anonymization

### Anonymizing User Data

For privacy compliance, anonymize user data:

```bash
# Anonymize user data while keeping structure
python migrate_data.py anonymize --user-id 12345 --keep-structure

# Completely delete user data
python migrate_data.py anonymize --user-id 12345 --delete-completely
```

### Anonymization Process

When keeping structure:
- Email → `anonymized_user_HASH@example.com`
- Password → New secure hash
- API keys → Removed
- Project titles → `Anonymized Project ID`
- File contents → `// Anonymized content for file ID`
- Chat messages → `Anonymized user message`

## Programmatic Usage

### Data Migration Utility

```python
from app.database import get_db
from app.utils.data_migration import DataMigrationUtility

db = next(get_db())
utility = DataMigrationUtility(db)

# Migrate projects to user
results = utility.migrate_existing_projects_to_user(user_id)

# Validate data integrity
validation = utility.validate_data_integrity()

# Create backup
backup_results = utility.create_backup("./backups")

# Anonymize user data
anon_results = utility.anonymize_user_data(user_id, keep_structure=True)
```

### Data Validation Service

```python
from app.services.data_validation_service import DataValidationService

validation_service = DataValidationService(db)

# Run comprehensive validation
results = validation_service.run_comprehensive_validation()

# Validate specific user
user_results = validation_service.validate_user_data(user_id)

# Check foreign key integrity
fk_results = validation_service.validate_foreign_key_integrity()
```

### Backup and Restore Service

```python
from app.services.backup_restore_service import BackupRestoreService

backup_service = BackupRestoreService(db)

# Create full backup
backup_results = backup_service.create_full_backup("./backups", compress=True)

# Create user-specific backup
user_backup = backup_service.create_user_backup(user_id, "./backups")

# List available backups
backups = backup_service.list_backups("./backups")

# Verify backup integrity
verification = backup_service.verify_backup_integrity("./backups", backup_id)
```

## Best Practices

### Before Migration

1. **Create a backup** of your existing database
2. **Run validation** to identify any existing issues
3. **Test migrations** on a copy of production data
4. **Plan downtime** for production migration

### During Migration

1. **Monitor progress** using the CLI output
2. **Check for errors** in migration results
3. **Validate data** after migration completes
4. **Test functionality** with migrated data

### After Migration

1. **Run comprehensive validation** to ensure data integrity
2. **Test user authentication** and project access
3. **Verify API functionality** with user credentials
4. **Monitor system performance** with new indexes

## Troubleshooting

### Common Issues

1. **Migration Fails**
   - Check database connectivity
   - Verify Alembic configuration
   - Check for conflicting schema changes

2. **Validation Errors**
   - Review specific error messages
   - Fix data issues before proceeding
   - Consider data cleanup scripts

3. **Backup/Restore Issues**
   - Verify file permissions
   - Check disk space availability
   - Ensure backup file integrity

### Recovery Procedures

1. **Failed Migration**
   ```bash
   # Rollback to previous version
   alembic downgrade -1
   
   # Restore from backup if needed
   python migrate_data.py restore --path ./backups --timestamp BACKUP_TIME
   ```

2. **Data Corruption**
   ```bash
   # Restore from latest backup
   python migrate_data.py restore --path ./backups --timestamp LATEST_BACKUP
   
   # Re-run validation
   python migrate_data.py validate
   ```

## Security Considerations

1. **Backup Security**
   - Store backups in secure locations
   - Encrypt backup files for sensitive data
   - Limit access to backup directories

2. **Migration Security**
   - Use secure database connections
   - Validate all input data
   - Monitor for unauthorized access

3. **Data Privacy**
   - Use anonymization for non-production environments
   - Follow data retention policies
   - Ensure GDPR compliance for user data

## Support

For issues with migration or data handling:

1. Check the logs for detailed error messages
2. Run validation to identify specific problems
3. Consult this guide for troubleshooting steps
4. Create backups before attempting fixes