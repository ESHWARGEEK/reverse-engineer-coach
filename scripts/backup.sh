#!/bin/bash

# Backup script for Reverse Engineer Coach
set -e

# Configuration
BACKUP_DIR="/backups/reverse-coach"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
COMPOSE_FILE="docker-compose.prod.yml"

echo "💾 Starting backup process..."

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
echo "🗄️ Backing up PostgreSQL database..."
docker-compose -f $COMPOSE_FILE exec -T postgres pg_dump -U postgres reverse_coach | gzip > "$BACKUP_DIR/postgres_${TIMESTAMP}.sql.gz"

# Redis backup
echo "📦 Backing up Redis data..."
docker-compose -f $COMPOSE_FILE exec -T redis redis-cli BGSAVE
sleep 5
docker cp reverse-coach-redis-prod:/data/dump.rdb "$BACKUP_DIR/redis_${TIMESTAMP}.rdb"

# Application data backup (if any persistent volumes)
echo "📁 Backing up application data..."
if [ -d "data" ]; then
    tar -czf "$BACKUP_DIR/app_data_${TIMESTAMP}.tar.gz" data/
fi

# Configuration backup
echo "⚙️ Backing up configuration files..."
tar -czf "$BACKUP_DIR/config_${TIMESTAMP}.tar.gz" \
    .env.production \
    docker-compose.prod.yml \
    nginx/ \
    k8s/ \
    monitoring/ \
    --exclude="*.log" \
    --exclude="ssl/*.key" 2>/dev/null || true

# Clean up old backups (keep last 7 days)
echo "🧹 Cleaning up old backups..."
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +7 -delete

# Verify backups
echo "✅ Verifying backups..."
for backup in "$BACKUP_DIR"/*_${TIMESTAMP}.*; do
    if [ -f "$backup" ] && [ -s "$backup" ]; then
        echo "✓ $(basename $backup) - $(du -h $backup | cut -f1)"
    else
        echo "❌ $(basename $backup) - FAILED"
    fi
done

echo "💾 Backup completed successfully!"
echo "📁 Backups stored in: $BACKUP_DIR"