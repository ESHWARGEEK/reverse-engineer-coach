# Reverse Engineer Coach - Deployment Status Check
Write-Host "🔍 Checking Reverse Engineer Coach deployment status..." -ForegroundColor Green

# Check Backend
Write-Host "`n📡 Backend Status:" -ForegroundColor Yellow
try {
    $backendResponse = Invoke-WebRequest -Uri "http://localhost:8000" -Method GET -TimeoutSec 5
    if ($backendResponse.StatusCode -eq 200) {
        Write-Host "✅ Backend is running on http://localhost:8000" -ForegroundColor Green
        
        # Check health endpoint
        $healthResponse = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET -TimeoutSec 5
        $healthData = $healthResponse.Content | ConvertFrom-Json
        Write-Host "   Status: $($healthData.status)" -ForegroundColor $(if ($healthData.status -eq "healthy") { "Green" } else { "Yellow" })
    }
} catch {
    Write-Host "❌ Backend is not responding" -ForegroundColor Red
}

# Check Frontend
Write-Host "`n⚛️ Frontend Status:" -ForegroundColor Yellow
try {
    $frontendResponse = Invoke-WebRequest -Uri "http://localhost:3000" -Method GET -TimeoutSec 5
    if ($frontendResponse.StatusCode -eq 200) {
        Write-Host "✅ Frontend is running on http://localhost:3000" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Frontend is not responding" -ForegroundColor Red
}

# Check Database
Write-Host "`n🗄️ Database Status:" -ForegroundColor Yellow
if (Test-Path "backend/reverse_coach.db") {
    Write-Host "✅ SQLite database file exists" -ForegroundColor Green
} else {
    Write-Host "❌ Database file not found" -ForegroundColor Red
}

Write-Host "`n🎉 Deployment Summary:" -ForegroundColor Cyan
Write-Host "• Application: http://localhost:3000" -ForegroundColor White
Write-Host "• API Documentation: http://localhost:8000/docs" -ForegroundColor White
Write-Host "• API Health: http://localhost:8000/health" -ForegroundColor White

Write-Host "`n📝 Next Steps:" -ForegroundColor Yellow
Write-Host "1. Open http://localhost:3000 in your browser" -ForegroundColor Gray
Write-Host "2. Try creating a new learning project" -ForegroundColor Gray
Write-Host "3. For full functionality, add API keys to .env file:" -ForegroundColor Gray
Write-Host "   - OPENAI_API_KEY (for AI features)" -ForegroundColor Gray
Write-Host "   - GITHUB_TOKEN (for repository analysis)" -ForegroundColor Gray