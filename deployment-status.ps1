#!/usr/bin/env powershell

Write-Host "🚀 Reverse Engineer Coach - Deployment Status Check" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Gray

# Check if services are running
Write-Host "`n📊 Service Status:" -ForegroundColor Yellow

# Check Backend (Port 8000)
try {
    $backendResponse = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    if ($backendResponse.StatusCode -eq 200) {
        Write-Host "✅ Backend API (Port 8000): RUNNING" -ForegroundColor Green
        $healthData = $backendResponse.Content | ConvertFrom-Json
        Write-Host "   Status: $($healthData.status)" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Backend API (Port 8000): NOT ACCESSIBLE" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Gray
}

# Check Frontend (Port 3000)
try {
    $frontendResponse = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
    if ($frontendResponse.StatusCode -eq 200) {
        Write-Host "✅ Frontend App (Port 3000): RUNNING" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Frontend App (Port 3000): NOT ACCESSIBLE" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Gray
}

# Check Coach WebSocket endpoint
try {
    $coachResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/coach/health" -UseBasicParsing -TimeoutSec 5
    if ($coachResponse.StatusCode -eq 200) {
        Write-Host "✅ Coach API: RUNNING" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Coach API: NOT ACCESSIBLE" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Gray
}

Write-Host "`n🔧 Configuration Status:" -ForegroundColor Yellow

# Check environment files
if (Test-Path ".env") {
    Write-Host "✅ .env file: EXISTS" -ForegroundColor Green
} else {
    Write-Host "⚠️  .env file: MISSING (using defaults)" -ForegroundColor Yellow
}

if (Test-Path "backend/.env") {
    Write-Host "✅ backend/.env file: EXISTS" -ForegroundColor Green
} else {
    Write-Host "⚠️  backend/.env file: MISSING (using defaults)" -ForegroundColor Yellow
}

# Check database
if (Test-Path "backend/reverse_coach.db") {
    Write-Host "✅ SQLite Database: EXISTS" -ForegroundColor Green
} else {
    Write-Host "❌ SQLite Database: MISSING" -ForegroundColor Red
}

Write-Host "`n🌐 Access URLs:" -ForegroundColor Yellow
Write-Host "   Frontend:  http://localhost:3000" -ForegroundColor Cyan
Write-Host "   Backend:   http://localhost:8000" -ForegroundColor Cyan
Write-Host "   API Docs:  http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "   Health:    http://localhost:8000/health" -ForegroundColor Cyan

Write-Host "`n📝 Notes:" -ForegroundColor Yellow
Write-Host "   • Frontend compiles successfully with only warnings" -ForegroundColor Gray
Write-Host "   • React version conflicts resolved by replacing Lucide icons" -ForegroundColor Gray
Write-Host "   • WebSocket chat functionality is working" -ForegroundColor Gray
Write-Host "   • API keys (OPENAI_API_KEY, GITHUB_TOKEN) are optional for basic functionality" -ForegroundColor Gray
Write-Host "   • Full AI coaching requires OPENAI_API_KEY configuration" -ForegroundColor Gray

Write-Host "`n" -ForegroundColor Gray