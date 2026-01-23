#!/bin/bash

# Production Deployment Orchestration Script
# Comprehensive deployment with monitoring, validation, and rollback capabilities

set -e

# Configuration
ENVIRONMENT=${1:-production}
VERSION=${2:-latest}
DOMAIN=${3:-""}
SKIP_BACKUP=${SKIP_BACKUP:-false}
SKIP_VALIDATION=${SKIP_VALIDATION:-false}
DRY_RUN=${DRY_RUN:-false}
ROLLBACK=${ROLLBACK:-false}
ROLLBACK_VERSION=${ROLLBACK_VERSION:-""}

# Deployment configuration
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.${ENVIRONMENT}"
BACKUP_DIR="backups"
LOG_DIR="logs/deployment"
HEALTH_CHECK_TIMEOUT=300
VALIDATION_TIMEOUT=180
MONITORING_DURATION=600  # 10 minutes post-deployment monitoring

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging setup
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/deployment-$(date +%Y%m%d-%H%M%S).log"

log_message() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local log_entry="[$timestamp] [$level] $message"
    echo -e "$log_entry" | tee -a "$LOG_FILE"
}

log_info() { log_message "INFO" "$1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"; }

test_prerequisites() {
    log_info "Checking deployment prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "✗ Docker is not available"
        return 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "✗ Docker daemon is not running"
        return 1
    fi
    
    local docker_version=$(docker --version)
    log_info "✓ Docker available: $docker_version"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "✗ Docker Compose is not available"
        return 1
    fi
    
    local compose_version=$(docker-compose --version)
    log_info "✓ Docker Compose available: $compose_version"
    
    # Check environment file
    if [ ! -f "$ENV_FILE" ]; then
        log_error "✗ Environment file not found: $ENV_FILE"
        return 1
    fi
    log_info "✓ Environment file found: $ENV_FILE"
    
    # Check required environment variables
    local required_vars=("POSTGRES_PASSWORD" "SECRET_KEY" "JWT_SECRET_KEY" "ENCRYPTION_KEY" "MASTER_ENCRYPTION_KEY")
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "$ENV_FILE" || grep "^${var}=$" "$ENV_FILE" &> /dev/null; then
            log_error "✗ Required environment variable missing or empty: $var"
            return 1
        fi
    done
    log_info "✓ All required environment variables are set"
    
    return 0
}

backup_current_deployment() {
    if [ "$SKIP_BACKUP" = "true" ]; then
        log_warn "Skipping backup as requested"
        return 0
    fi
    
    log_info "Creating deployment backup..."
    
    local backup_timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_path="$BACKUP_DIR/$backup_timestamp"
    
    mkdir -p "$backup_path"
    
    # Backup database
    log_info "Backing up database..."
    if ! docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_dump -U postgres reverse_coach > "$backup_path/database.sql"; then
        log_error "✗ Database backup failed"
        return 1
    fi
    
    # Backup Redis data
    log_info "Backing up Redis data..."
    docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli BGSAVE
    sleep 5
    
    local redis_container=$(docker-compose -f "$COMPOSE_FILE" ps -q redis)
    if [ -n "$redis_container" ]; then
        docker cp "$redis_container:/data/dump.rdb" "$backup_path/redis-dump.rdb"
    fi
    
    # Backup configuration files
    log_info "Backing up configuration..."
    cp "$ENV_FILE" "$backup_path/"
    cp "$COMPOSE_FILE" "$backup_path/"
    
    # Create backup manifest
    cat > "$backup_path/manifest.json" << EOF
{
    "timestamp": "$backup_timestamp",
    "environment": "$ENVIRONMENT",
    "version": "$VERSION",
    "files": [
        "database.sql",
        "redis-dump.rdb",
        "$(basename "$ENV_FILE")",
        "$(basename "$COMPOSE_FILE")"
    ]
}
EOF
    
    log_success "✓ Backup completed: $backup_path"
    return 0
}

deploy_application() {
    log_info "Starting application deployment..."
    
    if [ "$DRY_RUN" = "true" ]; then
        log_info "[DRY RUN] Would deploy version $VERSION to $ENVIRONMENT"
        return 0
    fi
    
    # Load environment variables
    export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
    
    # Pull latest images
    log_info "Pulling Docker images..."
    docker-compose -f "$COMPOSE_FILE" pull
    
    # Stop existing containers gracefully
    log_info "Stopping existing containers..."
    docker-compose -f "$COMPOSE_FILE" down --timeout 30
    
    # Start new containers
    log_info "Starting new containers..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # Wait for services to be healthy
    log_info "Waiting for services to become healthy..."
    local timeout=$HEALTH_CHECK_TIMEOUT
    local elapsed=0
    
    while [ $elapsed -lt $timeout ]; do
        local unhealthy_services=$(docker-compose -f "$COMPOSE_FILE" ps --filter "health=unhealthy" -q)
        local starting_services=$(docker-compose -f "$COMPOSE_FILE" ps --filter "health=starting" -q)
        
        if [ -z "$unhealthy_services" ] && [ -z "$starting_services" ]; then
            log_success "✓ All services are healthy"
            break
        fi
        
        log_info "Waiting for services to start... ($elapsed/$timeout seconds)"
        sleep 10
        elapsed=$((elapsed + 10))
    done
    
    if [ $elapsed -ge $timeout ]; then
        log_error "✗ Services failed to become healthy within timeout"
        return 1
    fi
    
    # Run database migrations
    log_info "Running database migrations..."
    docker-compose -f "$COMPOSE_FILE" exec -T backend alembic upgrade head
    
    log_success "✓ Application deployment completed"
    return 0
}

test_deployment_health() {
    log_info "Performing deployment health checks..."
    
    if [ "$SKIP_VALIDATION" = "true" ]; then
        log_warn "Skipping validation as requested"
        return 0
    fi
    
    # Basic health check
    local base_url
    if [ -n "$DOMAIN" ]; then
        base_url="https://$DOMAIN"
    else
        base_url="http://localhost"
    fi
    
    log_info "Testing basic connectivity..."
    local response=$(curl -s --max-time 30 "$base_url/health" || echo "")
    
    if echo "$response" | jq -r '.status' 2>/dev/null | grep -q "healthy"; then
        log_success "✓ Basic health check passed"
    else
        log_error "✗ Basic health check failed"
        return 1
    fi
    
    # Run comprehensive health checks
    log_info "Running comprehensive health checks..."
    local health_check_script
    if [ -n "$DOMAIN" ]; then
        export API_BASE_URL="https://$DOMAIN"
        export FRONTEND_URL="https://$DOMAIN"
    else
        export API_BASE_URL="http://localhost:8000"
        export FRONTEND_URL="http://localhost"
    fi
    
    if ./scripts/health-checks.sh; then
        log_success "✓ Comprehensive health checks passed"
    else
        log_error "✗ Some health checks failed"
        return 1
    fi
    
    return 0
}

start_post_deployment_monitoring() {
    log_info "Starting post-deployment monitoring..."
    
    local monitoring_end_time=$(($(date +%s) + MONITORING_DURATION))
    local base_url
    if [ -n "$DOMAIN" ]; then
        base_url="https://$DOMAIN"
    else
        base_url="http://localhost"
    fi
    
    local successful_requests=0
    local failed_requests=0
    local total_response_time=0
    local max_response_time=0
    local min_response_time=999999
    
    log_info "Monitoring for $MONITORING_DURATION seconds..."
    
    while [ $(date +%s) -lt $monitoring_end_time ]; do
        local start_time=$(date +%s%N)
        
        if curl -f -s --max-time 10 "$base_url/health" > /dev/null; then
            local end_time=$(date +%s%N)
            local response_time=$(( (end_time - start_time) / 1000000 )) # Convert to milliseconds
            
            successful_requests=$((successful_requests + 1))
            total_response_time=$((total_response_time + response_time))
            
            if [ $response_time -gt $max_response_time ]; then
                max_response_time=$response_time
            fi
            
            if [ $response_time -lt $min_response_time ]; then
                min_response_time=$response_time
            fi
        else
            failed_requests=$((failed_requests + 1))
            log_warn "Health check failed during monitoring"
        fi
        
        sleep 30
    done
    
    # Calculate and report metrics
    local total_requests=$((successful_requests + failed_requests))
    local success_rate=0
    local avg_response_time=0
    
    if [ $total_requests -gt 0 ]; then
        success_rate=$(( (successful_requests * 100) / total_requests ))
    fi
    
    if [ $successful_requests -gt 0 ]; then
        avg_response_time=$((total_response_time / successful_requests))
    fi
    
    log_info "=== Post-Deployment Monitoring Results ==="
    log_info "Total requests: $total_requests"
    log_info "Successful requests: $successful_requests"
    log_info "Failed requests: $failed_requests"
    log_info "Success rate: $success_rate%"
    log_info "Average response time: ${avg_response_time}ms"
    log_info "Min response time: ${min_response_time}ms"
    log_info "Max response time: ${max_response_time}ms"
    
    # Determine if monitoring results are acceptable
    if [ $success_rate -ge 95 ] && [ $avg_response_time -lt 2000 ]; then
        log_success "✓ Post-deployment monitoring shows healthy system"
        return 0
    elif [ $success_rate -ge 90 ]; then
        log_warn "⚠ Post-deployment monitoring shows acceptable but not optimal performance"
        return 0
    else
        log_error "✗ Post-deployment monitoring shows poor system health"
        return 1
    fi
}

invoke_rollback() {
    if [ "$ROLLBACK" != "true" ]; then
        return 0
    fi
    
    log_warn "Initiating rollback procedure..."
    
    if [ -z "$ROLLBACK_VERSION" ]; then
        # Find the most recent backup
        local latest_backup=$(ls -1 "$BACKUP_DIR" | sort -r | head -n 1)
        if [ -z "$latest_backup" ]; then
            log_error "✗ No backups available for rollback"
            return 1
        fi
        ROLLBACK_VERSION="$latest_backup"
    fi
    
    local rollback_path="$BACKUP_DIR/$ROLLBACK_VERSION"
    
    if [ ! -d "$rollback_path" ]; then
        log_error "✗ Rollback version not found: $rollback_path"
        return 1
    fi
    
    log_info "Rolling back to version: $ROLLBACK_VERSION"
    
    # Stop current services
    docker-compose -f "$COMPOSE_FILE" down
    
    # Restore database
    log_info "Restoring database..."
    docker-compose -f "$COMPOSE_FILE" up -d postgres
    sleep 10
    cat "$rollback_path/database.sql" | docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d reverse_coach
    
    # Restore Redis
    log_info "Restoring Redis data..."
    docker-compose -f "$COMPOSE_FILE" up -d redis
    sleep 5
    local redis_container=$(docker-compose -f "$COMPOSE_FILE" ps -q redis)
    if [ -n "$redis_container" ]; then
        docker cp "$rollback_path/redis-dump.rdb" "$redis_container:/data/dump.rdb"
        docker-compose -f "$COMPOSE_FILE" restart redis
    fi
    
    # Start all services
    log_info "Starting all services..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    log_success "✓ Rollback completed successfully"
    return 0
}

send_deployment_notification() {
    local success=$1
    local message=$2
    
    local status
    local emoji
    
    if [ "$success" = "true" ]; then
        status="SUCCESS"
        emoji="🎉"
    else
        status="FAILED"
        emoji="❌"
    fi
    
    log_message "NOTIFICATION" "$emoji Deployment $status: $message"
    
    # Example: Send to webhook (uncomment and configure as needed)
    # if [ -n "$DEPLOYMENT_WEBHOOK_URL" ]; then
    #     local payload=$(cat << EOF
    # {
    #     "text": "$emoji Production Deployment $status",
    #     "attachments": [{
    #         "color": "$([ "$success" = "true" ] && echo "good" || echo "danger")",
    #         "fields": [
    #             {"title": "Environment", "value": "$ENVIRONMENT", "short": true},
    #             {"title": "Version", "value": "$VERSION", "short": true},
    #             {"title": "Message", "value": "$message", "short": false}
    #         ]
    #     }]
    # }
    # EOF
    #     )
    #     curl -X POST -H "Content-Type: application/json" -d "$payload" "$DEPLOYMENT_WEBHOOK_URL"
    # fi
}

# Main execution
main() {
    log_info "=== Production Deployment Started ==="
    log_info "Environment: $ENVIRONMENT"
    log_info "Version: $VERSION"
    log_info "Domain: ${DOMAIN:-localhost}"
    log_info "Dry Run: $DRY_RUN"
    log_info "Skip Backup: $SKIP_BACKUP"
    log_info "Skip Validation: $SKIP_VALIDATION"
    log_info "Rollback: $ROLLBACK"
    log_info "Log File: $LOG_FILE"
    echo
    
    local deployment_success=false
    
    # Handle rollback request
    if [ "$ROLLBACK" = "true" ]; then
        if invoke_rollback; then
            send_deployment_notification true "Rollback to version $ROLLBACK_VERSION"
            exit 0
        else
            send_deployment_notification false "Rollback to version $ROLLBACK_VERSION failed"
            exit 1
        fi
    fi
    
    # Pre-deployment checks
    if ! test_prerequisites; then
        log_error "❌ Prerequisites check failed"
        send_deployment_notification false "Prerequisites check failed"
        exit 1
    fi
    
    # Create backup
    if ! backup_current_deployment; then
        log_error "❌ Backup creation failed"
        send_deployment_notification false "Backup creation failed"
        exit 1
    fi
    
    # Deploy application
    if ! deploy_application; then
        log_error "❌ Application deployment failed"
        send_deployment_notification false "Application deployment failed"
        exit 1
    fi
    
    # Validate deployment
    if ! test_deployment_health; then
        log_error "❌ Deployment health validation failed"
        send_deployment_notification false "Deployment health validation failed"
        exit 1
    fi
    
    # Start monitoring
    if ! start_post_deployment_monitoring; then
        log_warn "Post-deployment monitoring detected issues, but deployment will continue"
    fi
    
    deployment_success=true
    log_success "🎉 Production deployment completed successfully!"
    send_deployment_notification true "Deployment completed successfully"
    
    log_info "=== Deployment Log Available: $LOG_FILE ==="
    exit 0
}

# Check if required tools are available
if ! command -v curl &> /dev/null; then
    log_error "curl is required but not installed"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    log_warn "jq is not installed - some checks will be limited"
fi

# Execute main function
main "$@"