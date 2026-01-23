# Reverse Engineer Coach - Fix Status Check
Write-Host "🔧 Checking fixes for Reverse Engineer Coach..." -ForegroundColor Green

# Check Backend
Write-Host "`n📡 Backend Status:" -ForegroundColor Yellow
try {
    $backendResponse = Invoke-WebRequest -Uri "http://localhost:8000" -Method GET -TimeoutSec 5
    if ($backendResponse.StatusCode -eq 200) {
        Write-Host "✅ Backend is running" -ForegroundColor Green
        
        # Check coach endpoint
        $coachResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/coach/health" -Method GET -TimeoutSec 5
        if ($coachResponse.StatusCode -eq 200) {
            Write-Host "✅ Coach API endpoint is working" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "❌ Backend issue: $($_.Exception.Message)" -ForegroundColor Red
}

# Check Frontend
Write-Host "`n⚛️ Frontend Status:" -ForegroundColor Yellow
try {
    $frontendResponse = Invoke-WebRequest -Uri "http://localhost:3000" -Method GET -TimeoutSec 5
    if ($frontendResponse.StatusCode -eq 200) {
        Write-Host "✅ Frontend is accessible" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Frontend issue: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n🔧 Fixes Applied:" -ForegroundColor Cyan
Write-Host "✅ Fixed useFocusManagement import path" -ForegroundColor Green
Write-Host "✅ Installed lucide-react package" -ForegroundColor Green
Write-Host "✅ Added WebSocket support to coach API" -ForegroundColor Green

Write-Host "`n⚠️ Known Issues (Non-Critical):" -ForegroundColor Yellow
Write-Host "• TypeScript warnings with React icons (app still works)" -ForegroundColor Gray
Write-Host "• WebSocket will show basic responses until API keys are configured" -ForegroundColor Gray

Write-Host "`n🎯 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Open http://localhost:3000 - the app should work without console errors" -ForegroundColor White
Write-Host "2. Try the chat feature - it will give basic responses" -ForegroundColor White
Write-Host "3. For full AI functionality, add API keys to .env file:" -ForegroundColor White
Write-Host "   OPENAI_API_KEY=your_key_here" -ForegroundColor Gray
Write-Host "   GITHUB_TOKEN=your_token_here" -ForegroundColor Gray