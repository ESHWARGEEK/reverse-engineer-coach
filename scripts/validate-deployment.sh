#!/bin/bash

# Deployment validation script
set -e

echo "🔍 Validating deployment..."

# Configuration
BASE_URL=${1:-"http://localhost"}
TIMEOUT=30

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test function
test_endpoint() {
    local endpoint=$1
    local expected_status=${2:-200}
    local description=$3
    
    echo -n "Testing $description... "
    
    response=$(curl -s -w "%{http_code}" -o /dev/null --max-time $TIMEOUT "$BASE_URL$endpoint" || echo "000")
    
    if [ "$response" = "$expected_status" ]; then
        echo -e "${GREEN}✓ PASS${NC} ($response)"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected: $expected_status, Got: $response)"
        return 1
    fi
}

# Test JSON endpoint
test_json_endpoint() {
    local endpoint=$1
    local description=$2
    
    echo -n "Testing $description... "
    
    response=$(curl -s --max-time $TIMEOUT "$BASE_URL$endpoint" || echo "")
    
    if echo "$response" | jq . >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC} (Valid JSON)"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Invalid JSON or no response)"
        return 1
    fi
}

# Initialize counters
total_tests=0
passed_tests=0

# Core application tests
echo -e "\n${YELLOW}=== Core Application Tests ===${NC}"

tests=(
    "/ Root endpoint"
    "/health Health check"
    "/docs API documentation"
    "/metrics Metrics endpoint"
)

for test in "${tests[@]}"; do
    endpoint=$(echo $test | cut -d' ' -f1)
    description=$(echo $test | cut -d' ' -f2-)
    
    total_tests=$((total_tests + 1))
    if test_endpoint "$endpoint" 200 "$description"; then
        passed_tests=$((passed_tests + 1))
    fi
done

# API endpoints tests
echo -e "\n${YELLOW}=== API Endpoints Tests ===${NC}"

api_tests=(
    "/api/v1/projects Projects API"
    "/api/v1/github GitHub API"
)

for test in "${api_tests[@]}"; do
    endpoint=$(echo $test | cut -d' ' -f1)
    description=$(echo $test | cut -d' ' -f2-)
    
    total_tests=$((total_tests + 1))
    # API endpoints might return 404 or 422 for GET without params, which is acceptable
    response=$(curl -s -w "%{http_code}" -o /dev/null --max-time $TIMEOUT "$BASE_URL$endpoint" || echo "000")
    if [[ "$response" =~ ^(200|404|422)$ ]]; then
        echo -e "Testing $description... ${GREEN}✓ PASS${NC} ($response)"
        passed_tests=$((passed_tests + 1))
    else
        echo -e "Testing $description... ${RED}✗ FAIL${NC} (Got: $response)"
    fi
done

# JSON response tests
echo -e "\n${YELLOW}=== JSON Response Tests ===${NC}"

json_tests=(
    "/health Health check JSON"
    "/ Root endpoint JSON"
)

for test in "${json_tests[@]}"; do
    endpoint=$(echo $test | cut -d' ' -f1)
    description=$(echo $test | cut -d' ' -f2-)
    
    total_tests=$((total_tests + 1))
    if test_json_endpoint "$endpoint" "$description"; then
        passed_tests=$((passed_tests + 1))
    fi
done

# Service health tests
echo -e "\n${YELLOW}=== Service Health Tests ===${NC}"

# Test database connectivity through health endpoint
total_tests=$((total_tests + 1))
echo -n "Testing database connectivity... "
health_response=$(curl -s --max-time $TIMEOUT "$BASE_URL/health" || echo "")
if echo "$health_response" | jq -r '.services.database.status' 2>/dev/null | grep -q "healthy"; then
    echo -e "${GREEN}✓ PASS${NC}"
    passed_tests=$((passed_tests + 1))
else
    echo -e "${RED}✗ FAIL${NC}"
fi

# Test cache connectivity through health endpoint
total_tests=$((total_tests + 1))
echo -n "Testing cache connectivity... "
if echo "$health_response" | jq -r '.services.cache.status' 2>/dev/null | grep -q "healthy"; then
    echo -e "${GREEN}✓ PASS${NC}"
    passed_tests=$((passed_tests + 1))
else
    echo -e "${RED}✗ FAIL${NC}"
fi

# Performance tests
echo -e "\n${YELLOW}=== Performance Tests ===${NC}"

# Response time test
total_tests=$((total_tests + 1))
echo -n "Testing response time... "
response_time=$(curl -s -w "%{time_total}" -o /dev/null --max-time $TIMEOUT "$BASE_URL/health" || echo "999")
if (( $(echo "$response_time < 2.0" | bc -l) )); then
    echo -e "${GREEN}✓ PASS${NC} (${response_time}s)"
    passed_tests=$((passed_tests + 1))
else
    echo -e "${RED}✗ FAIL${NC} (${response_time}s - too slow)"
fi

# Security tests
echo -e "\n${YELLOW}=== Security Tests ===${NC}"

# HTTPS redirect test (if not localhost)
if [[ "$BASE_URL" != "http://localhost"* ]]; then
    total_tests=$((total_tests + 1))
    echo -n "Testing HTTPS redirect... "
    http_url=$(echo "$BASE_URL" | sed 's/https:/http:/')
    redirect_response=$(curl -s -w "%{http_code}" -o /dev/null --max-time $TIMEOUT "$http_url" || echo "000")
    if [[ "$redirect_response" =~ ^(301|302|308)$ ]]; then
        echo -e "${GREEN}✓ PASS${NC} ($redirect_response)"
        passed_tests=$((passed_tests + 1))
    else
        echo -e "${RED}✗ FAIL${NC} (Expected redirect, got: $redirect_response)"
    fi
fi

# Security headers test
total_tests=$((total_tests + 1))
echo -n "Testing security headers... "
headers=$(curl -s -I --max-time $TIMEOUT "$BASE_URL/" || echo "")
if echo "$headers" | grep -qi "x-frame-options\|x-content-type-options"; then
    echo -e "${GREEN}✓ PASS${NC}"
    passed_tests=$((passed_tests + 1))
else
    echo -e "${YELLOW}⚠ WARN${NC} (Some security headers missing)"
fi

# Summary
echo -e "\n${YELLOW}=== Validation Summary ===${NC}"
echo "Total tests: $total_tests"
echo "Passed: $passed_tests"
echo "Failed: $((total_tests - passed_tests))"

success_rate=$(( (passed_tests * 100) / total_tests ))
echo "Success rate: $success_rate%"

if [ $passed_tests -eq $total_tests ]; then
    echo -e "\n${GREEN}🎉 All tests passed! Deployment is healthy.${NC}"
    exit 0
elif [ $success_rate -ge 80 ]; then
    echo -e "\n${YELLOW}⚠ Most tests passed. Deployment is functional but may have issues.${NC}"
    exit 0
else
    echo -e "\n${RED}❌ Many tests failed. Deployment has significant issues.${NC}"
    exit 1
fi