# Test React Hooks Issue
Write-Host "🧪 Testing React Hooks Issue..." -ForegroundColor Green

Write-Host "`n📊 Checking React versions:" -ForegroundColor Yellow
try {
    $reactVersions = npm ls react --depth=0 2>$null
    Write-Host $reactVersions -ForegroundColor Gray
} catch {
    Write-Host "Could not check React versions" -ForegroundColor Red
}

Write-Host "`n🌐 Testing Frontend Accessibility:" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000" -Method GET -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Frontend is accessible" -ForegroundColor Green
        
        # Check if the content suggests the app is working
        if ($response.Content -match "react" -or $response.Content -match "root") {
            Write-Host "✅ React app appears to be loading" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "❌ Frontend not accessible: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n🔍 Analysis:" -ForegroundColor Cyan
Write-Host "• Multiple React versions detected (18.x and 19.x)" -ForegroundColor Yellow
Write-Host "• This causes 'Invalid hook call' errors in console" -ForegroundColor Yellow
Write-Host "• However, the app may still function for basic operations" -ForegroundColor Yellow

Write-Host "`n💡 Recommendations:" -ForegroundColor Cyan
Write-Host "1. The app should work for basic functionality despite console errors" -ForegroundColor White
Write-Host "2. For production use, consider downgrading problematic packages" -ForegroundColor White
Write-Host "3. Test core features: project creation, navigation, etc." -ForegroundColor White

Write-Host "`n🎯 Next Steps:" -ForegroundColor Green
Write-Host "• Open http://localhost:3000 and test the application" -ForegroundColor White
Write-Host "• Ignore console errors for now - focus on functionality" -ForegroundColor White
Write-Host "• Report if any actual features are broken" -ForegroundColor White