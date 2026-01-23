#!/bin/bash

# Restore script for Reverse Engineer Coach
set -e

# Configuration
BACKUP_DIR="/backups/reverse-coach"
COMPOSE_FILE="docker-compose.prod.yml"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <timestamp>"
    echo "Available backups:"
    ls -la $BACKUP_DIR/ | grep -E "(postgres|redis|app_data)_[0-9]{8}_[0-9]{6}\.(sql\.gz|rdb|tar\.gz)$" | awk '{print $9}' | sort -u
    exit 1
fi

TIMESTAMP=$1

echo "🔄 Starting restore process for timestamp: $TIMESTAMP"

# Verify backup files exist
POSTGRES_BACKUP="$BACKUP_DIR/postgres_${TIMESTAMP}.sql.gz"
REDIS_BACKUP="$BACKUP_DIR/redis_${TIMESTAMP}.rdb"
APP_DATA_BACKUP="$BACKUP_DIR/app_data_${TIMESTAMP}.tar.gz"

if [ ! -f "$POSTGRES_BACKUP" ]; then
    echo "❌ PostgreSQL backup not found: $POSTGRES_BACKUP"
    exit 1
fi

# Stop services
echo "🛑 Stopping services..."
docker-compose -f $COMPOSE_FILE down

# Restore PostgreSQL database
echo "🗄️ Restoring PostgreSQL database..."
docker-compose -f $COMPOSE_FILE up -d postgres
sleep 10

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
timeout=60
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker-compose -f $COMPOSE_FILE exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

# Drop and recreate database
docker-compose -f $COMPOSE_FILE exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS reverse_coach;"
docker-compose -f $COMPOSE_FILE exec -T postgres psql -U postgres -c "CREATE DATABASE reverse_coach;"

# Restore database
zcat "$POSTGRES_BACKUP" | docker-compose -f $COMPOSE_FILE exec -T postgres psql -U postgres -d reverse_coach

# Restore Redis data
if [ -f "$REDIS_BACKUP" ]; then
    echo "📦 Restoring Redis data..."
    docker-compose -f $COMPOSE_FILE up -d redis
    sleep 5
    docker cp "$REDIS_BACKUP" reverse-coach-redis-prod:/data/dump.rdb
    docker-compose -f $COMPOSE_FILE restart redis
fi

# Restore application data
if [ -f "$APP_DATA_BACKUP" ]; then
    echo "📁 Restoring application data..."
    tar -xzf "$APP_DATA_BACKUP"
fi

# Start all services
echo "🚀 Starting all services..."
docker-compose -f $COMPOSE_FILE up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 30

# Health check
echo "🏥 Performing health check..."
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo "✅ Restore completed successfully! Application is healthy."
else
    echo "❌ Health check failed after restore!"
    docker-compose -f $COMPOSE_FILE logs --tail=50
    exit 1
fi

echo "🎉 Restore completed successfully!"