#!/usr/bin/env pwsh

# Backend Deployment Status Checker
# This script checks if the backend is properly deployed and accessible

Write-Host "🔍 Checking Backend Deployment Status..." -ForegroundColor Cyan
Write-Host ""

# Configuration
$BACKEND_URL = "https://reverse-coach-backend.onrender.com"
$FRONTEND_URL = "https://reveng.netlify.app"

# Function to test URL
function Test-Endpoint {
    param(
        [string]$Url,
        [string]$Name
    )
    
    try {
        Write-Host "Testing $Name..." -NoNewline
        $response = Invoke-RestMethod -Uri $Url -Method GET -TimeoutSec 10
        Write-Host " ✅ SUCCESS" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host " ❌ FAILED" -ForegroundColor Red
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
        return $false
    }
}

# Test backend endpoints
Write-Host "🚀 Backend Tests:" -ForegroundColor Yellow
$healthOk = Test-Endpoint "$BACKEND_URL/health" "Health Check"
$rootOk = Test-Endpoint "$BACKEND_URL/" "Root Endpoint"

Write-Host ""
Write-Host "🌐 Frontend Test:" -ForegroundColor Yellow
$frontendOk = Test-Endpoint $FRONTEND_URL "Frontend"

Write-Host ""
Write-Host "📊 Summary:" -ForegroundColor Cyan

if ($healthOk -and $rootOk) {
    Write-Host "✅ Backend: DEPLOYED & WORKING" -ForegroundColor Green
    Write-Host "   URL: $BACKEND_URL" -ForegroundColor Gray
} else {
    Write-Host "❌ Backend: NOT WORKING" -ForegroundColor Red
    Write-Host "   Check Render deployment logs" -ForegroundColor Yellow
}

if ($frontendOk) {
    Write-Host "✅ Frontend: DEPLOYED & WORKING" -ForegroundColor Green
    Write-Host "   URL: $FRONTEND_URL" -ForegroundColor Gray
} else {
    Write-Host "❌ Frontend: NOT WORKING" -ForegroundColor Red
}

Write-Host ""

if ($healthOk -and $rootOk -and $frontendOk) {
    Write-Host "🎉 DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
    Write-Host "Both frontend and backend are working correctly." -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Test user registration at: $FRONTEND_URL" -ForegroundColor Gray
    Write-Host "2. Test authentication flow" -ForegroundColor Gray
    Write-Host "3. Verify all features work end-to-end" -ForegroundColor Gray
} else {
    Write-Host "⚠️  DEPLOYMENT INCOMPLETE" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Troubleshooting steps:" -ForegroundColor Cyan
    
    if (-not $healthOk -or -not $rootOk) {
        Write-Host "Backend Issues:" -ForegroundColor Red
        Write-Host "1. Check Render deployment logs" -ForegroundColor Gray
        Write-Host "2. Verify all environment variables are set" -ForegroundColor Gray
        Write-Host "3. Ensure PostgreSQL database is created and connected" -ForegroundColor Gray
        Write-Host "4. Check build and start commands are correct" -ForegroundColor Gray
    }
    
    if (-not $frontendOk) {
        Write-Host "Frontend Issues:" -ForegroundColor Red
        Write-Host "1. Check Netlify deployment status" -ForegroundColor Gray
        Write-Host "2. Verify build completed successfully" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "For detailed troubleshooting, see:" -ForegroundColor Cyan
Write-Host "- DEPLOYMENT_FIX_STATUS.md" -ForegroundColor Gray
Write-Host "- RENDER_TROUBLESHOOTING_GUIDE.md" -ForegroundColor Gray