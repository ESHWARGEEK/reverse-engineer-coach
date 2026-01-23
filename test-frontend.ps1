# Test Frontend Functionality
Write-Host "🧪 Testing Reverse Engineer Coach Frontend..." -ForegroundColor Green

try {
    # Test main page
    $response = Invoke-WebRequest -Uri "http://localhost:3000" -Method GET -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Frontend is accessible" -ForegroundColor Green
        
        # Check if the page contains expected content
        if ($response.Content -match "Reverse Engineer Coach" -or $response.Content -match "react") {
            Write-Host "✅ Page content looks correct" -ForegroundColor Green
        } else {
            Write-Host "⚠️ Page content might be incomplete" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "❌ Frontend test failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n📝 Note: TypeScript warnings in console are non-critical." -ForegroundColor Yellow
Write-Host "The application should work despite these warnings." -ForegroundColor Yellow
Write-Host "`n🌐 Open http://localhost:3000 in your browser to test the UI" -ForegroundColor Cyan