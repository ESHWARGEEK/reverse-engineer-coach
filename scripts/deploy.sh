#!/bin/bash

# Deployment script for Reverse Engineer Coach
set -e

# Configuration
ENVIRONMENT=${1:-production}
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.${ENVIRONMENT}"

echo "🚀 Deploying Reverse Engineer Coach to ${ENVIRONMENT} environment..."

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Environment file $ENV_FILE not found!"
    echo "Please create the environment file with required variables."
    exit 1
fi

# Load environment variables
export $(cat $ENV_FILE | grep -v '^#' | xargs)

# Validate required environment variables
required_vars=(
    "POSTGRES_PASSWORD"
    "SECRET_KEY"
    "GITHUB_TOKEN"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable $var is not set!"
        exit 1
    fi
done

# Create necessary directories
mkdir -p nginx/ssl
mkdir -p logs

# Pull latest images
echo "📦 Pulling latest Docker images..."
docker-compose -f $COMPOSE_FILE pull

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f $COMPOSE_FILE down

# Start services
echo "🔄 Starting services..."
docker-compose -f $COMPOSE_FILE up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
timeout=300
elapsed=0

while [ $elapsed -lt $timeout ]; do
    if docker-compose -f $COMPOSE_FILE ps | grep -q "unhealthy\|starting"; then
        echo "Waiting for services to start... (${elapsed}s)"
        sleep 10
        elapsed=$((elapsed + 10))
    else
        break
    fi
done

# Check if all services are running
if docker-compose -f $COMPOSE_FILE ps | grep -q "Exit\|unhealthy"; then
    echo "❌ Some services failed to start properly!"
    docker-compose -f $COMPOSE_FILE logs --tail=50
    exit 1
fi

# Run database migrations
echo "🗄️ Running database migrations..."
docker-compose -f $COMPOSE_FILE exec -T backend alembic upgrade head

# Health check
echo "🏥 Performing health check..."
sleep 10
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo "✅ Deployment successful! Application is healthy."
else
    echo "❌ Health check failed!"
    docker-compose -f $COMPOSE_FILE logs --tail=50
    exit 1
fi

echo "🎉 Deployment completed successfully!"
echo "📊 Access the application at: http://localhost"
echo "📈 Monitor logs with: docker-compose -f $COMPOSE_FILE logs -f"