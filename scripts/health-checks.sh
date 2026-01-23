#!/bin/bash

# Health Check Scripts for Production Deployment
# This script performs comprehensive health checks after deployment

set -e

# Configuration
API_BASE_URL="${API_BASE_URL:-https://api.your-domain.com}"
FRONTEND_URL="${FRONTEND_URL:-https://your-domain.com}"
TIMEOUT=30
MAX_RETRIES=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Health check functions
check_api_health() {
    log_info "Checking API health..."
    
    local retries=0
    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -f -s --max-time $TIMEOUT "$API_BASE_URL/api/monitoring/health" > /dev/null; then
            log_info "✓ API health check passed"
            return 0
        fi
        
        retries=$((retries + 1))
        log_warn "API health check failed (attempt $retries/$MAX_RETRIES)"
        sleep 5
    done
    
    log_error "✗ API health check failed after $MAX_RETRIES attempts"
    return 1
}

check_api_detailed_health() {
    log_info "Checking detailed API health..."
    
    local response=$(curl -f -s --max-time $TIMEOUT "$API_BASE_URL/api/monitoring/health/detailed")
    local status=$(echo "$response" | jq -r '.status // "unknown"')
    
    if [ "$status" = "healthy" ]; then
        log_info "✓ Detailed API health check passed"
        
        # Check individual components
        local db_status=$(echo "$response" | jq -r '.checks.database.status // "unknown"')
        local redis_status=$(echo "$response" | jq -r '.checks.redis.status // "unknown"')
        
        if [ "$db_status" = "healthy" ]; then
            log_info "  ✓ Database connection healthy"
        else
            log_error "  ✗ Database connection unhealthy: $db_status"
            return 1
        fi
        
        if [ "$redis_status" = "healthy" ]; then
            log_info "  ✓ Redis connection healthy"
        else
            log_warn "  ⚠ Redis connection status: $redis_status"
        fi
        
        return 0
    else
        log_error "✗ Detailed API health check failed: $status"
        return 1
    fi
}

check_frontend_health() {
    log_info "Checking frontend health..."
    
    local retries=0
    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -f -s --max-time $TIMEOUT "$FRONTEND_URL" > /dev/null; then
            log_info "✓ Frontend health check passed"
            return 0
        fi
        
        retries=$((retries + 1))
        log_warn "Frontend health check failed (attempt $retries/$MAX_RETRIES)"
        sleep 5
    done
    
    log_error "✗ Frontend health check failed after $MAX_RETRIES attempts"
    return 1
}

check_authentication_endpoints() {
    log_info "Checking authentication endpoints..."
    
    # Test registration endpoint (should return validation error for empty request)
    local reg_response=$(curl -s -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d '{}' \
        "$API_BASE_URL/api/auth/register" \
        --max-time $TIMEOUT)
    
    local reg_status_code="${reg_response: -3}"
    
    if [ "$reg_status_code" = "422" ] || [ "$reg_status_code" = "400" ]; then
        log_info "✓ Registration endpoint responding correctly"
    else
        log_error "✗ Registration endpoint unexpected response: $reg_status_code"
        return 1
    fi
    
    # Test login endpoint (should return validation error for empty request)
    local login_response=$(curl -s -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d '{}' \
        "$API_BASE_URL/api/auth/login" \
        --max-time $TIMEOUT)
    
    local login_status_code="${login_response: -3}"
    
    if [ "$login_status_code" = "422" ] || [ "$login_status_code" = "400" ]; then
        log_info "✓ Login endpoint responding correctly"
    else
        log_error "✗ Login endpoint unexpected response: $login_status_code"
        return 1
    fi
}

check_discovery_endpoints() {
    log_info "Checking discovery endpoints..."
    
    # Test discovery endpoint (should require authentication)
    local discovery_response=$(curl -s -w "%{http_code}" \
        "$API_BASE_URL/api/discover/repositories?concept=microservices" \
        --max-time $TIMEOUT)
    
    local discovery_status_code="${discovery_response: -3}"
    
    if [ "$discovery_status_code" = "401" ] || [ "$discovery_status_code" = "403" ]; then
        log_info "✓ Discovery endpoint properly protected"
    else
        log_warn "⚠ Discovery endpoint response: $discovery_status_code (expected 401/403)"
    fi
}

check_rate_limiting() {
    log_info "Checking rate limiting..."
    
    local success_count=0
    local rate_limited_count=0
    
    # Make multiple rapid requests to test rate limiting
    for i in {1..10}; do
        local response=$(curl -s -w "%{http_code}" \
            "$API_BASE_URL/api/monitoring/health" \
            --max-time 5)
        
        local status_code="${response: -3}"
        
        if [ "$status_code" = "200" ]; then
            success_count=$((success_count + 1))
        elif [ "$status_code" = "429" ]; then
            rate_limited_count=$((rate_limited_count + 1))
        fi
        
        sleep 0.1
    done
    
    if [ $success_count -gt 0 ]; then
        log_info "✓ Rate limiting configured (successful requests: $success_count, rate limited: $rate_limited_count)"
    else
        log_error "✗ No successful requests - possible rate limiting issue"
        return 1
    fi
}

check_ssl_certificate() {
    log_info "Checking SSL certificate..."
    
    local domain=$(echo "$API_BASE_URL" | sed 's|https://||' | sed 's|/.*||')
    
    if echo | openssl s_client -servername "$domain" -connect "$domain:443" 2>/dev/null | \
       openssl x509 -noout -dates 2>/dev/null; then
        log_info "✓ SSL certificate is valid"
    else
        log_error "✗ SSL certificate check failed"
        return 1
    fi
}

check_security_headers() {
    log_info "Checking security headers..."
    
    local headers=$(curl -s -I "$FRONTEND_URL" --max-time $TIMEOUT)
    
    # Check for important security headers
    if echo "$headers" | grep -i "strict-transport-security" > /dev/null; then
        log_info "✓ HSTS header present"
    else
        log_warn "⚠ HSTS header missing"
    fi
    
    if echo "$headers" | grep -i "x-frame-options" > /dev/null; then
        log_info "✓ X-Frame-Options header present"
    else
        log_warn "⚠ X-Frame-Options header missing"
    fi
    
    if echo "$headers" | grep -i "x-content-type-options" > /dev/null; then
        log_info "✓ X-Content-Type-Options header present"
    else
        log_warn "⚠ X-Content-Type-Options header missing"
    fi
}

run_performance_test() {
    log_info "Running basic performance test..."
    
    local start_time=$(date +%s%N)
    
    if curl -f -s --max-time $TIMEOUT "$API_BASE_URL/api/monitoring/health" > /dev/null; then
        local end_time=$(date +%s%N)
        local duration=$(( (end_time - start_time) / 1000000 )) # Convert to milliseconds
        
        if [ $duration -lt 1000 ]; then
            log_info "✓ API response time: ${duration}ms (excellent)"
        elif [ $duration -lt 2000 ]; then
            log_info "✓ API response time: ${duration}ms (good)"
        elif [ $duration -lt 5000 ]; then
            log_warn "⚠ API response time: ${duration}ms (acceptable)"
        else
            log_error "✗ API response time: ${duration}ms (slow)"
            return 1
        fi
    else
        log_error "✗ Performance test failed - API not responding"
        return 1
    fi
}

# Main execution
main() {
    log_info "Starting comprehensive health checks..."
    log_info "API Base URL: $API_BASE_URL"
    log_info "Frontend URL: $FRONTEND_URL"
    echo
    
    local failed_checks=0
    
    # Run all health checks
    check_api_health || failed_checks=$((failed_checks + 1))
    check_api_detailed_health || failed_checks=$((failed_checks + 1))
    check_frontend_health || failed_checks=$((failed_checks + 1))
    check_authentication_endpoints || failed_checks=$((failed_checks + 1))
    check_discovery_endpoints || failed_checks=$((failed_checks + 1))
    check_rate_limiting || failed_checks=$((failed_checks + 1))
    check_ssl_certificate || failed_checks=$((failed_checks + 1))
    check_security_headers || failed_checks=$((failed_checks + 1))
    run_performance_test || failed_checks=$((failed_checks + 1))
    
    echo
    if [ $failed_checks -eq 0 ]; then
        log_info "🎉 All health checks passed successfully!"
        exit 0
    else
        log_error "❌ $failed_checks health check(s) failed"
        exit 1
    fi
}

# Check if required tools are available
if ! command -v curl &> /dev/null; then
    log_error "curl is required but not installed"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    log_warn "jq is not installed - some checks will be limited"
fi

# Run main function
main "$@"