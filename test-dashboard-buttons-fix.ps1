#!/usr/bin/env pwsh

Write-Host "🔧 Testing Dashboard Button Functionality Fix" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Test URLs
$frontendUrl = "https://reveng.netlify.app"
$backendUrl = "https://reverse-coach-backend.onrender.com"

Write-Host "📍 Testing URLs:" -ForegroundColor Yellow
Write-Host "   Frontend: $frontendUrl" -ForegroundColor White
Write-Host "   Backend:  $backendUrl" -ForegroundColor White
Write-Host ""

# Test backend health
Write-Host "🏥 Testing Backend Health..." -ForegroundColor Green
try {
    $backendResponse = Invoke-RestMethod -Uri "$backendUrl/health" -Method GET -TimeoutSec 10
    Write-Host "   ✅ Backend is healthy: $($backendResponse.status)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Backend health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test frontend accessibility
Write-Host "🌐 Testing Frontend Accessibility..." -ForegroundColor Green
try {
    $frontendResponse = Invoke-WebRequest -Uri $frontendUrl -Method GET -TimeoutSec 10
    if ($frontendResponse.StatusCode -eq 200) {
        Write-Host "   ✅ Frontend is accessible (Status: $($frontendResponse.StatusCode))" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Frontend returned status: $($frontendResponse.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ❌ Frontend accessibility test failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Manual testing instructions
Write-Host "🧪 Manual Testing Instructions:" -ForegroundColor Magenta
Write-Host "================================" -ForegroundColor Magenta
Write-Host ""

Write-Host "1. 🔐 Authentication Test:" -ForegroundColor Yellow
Write-Host "   • Visit: $frontendUrl" -ForegroundColor White
Write-Host "   • Should redirect to auth page automatically" -ForegroundColor Gray
Write-Host "   • Login with your credentials" -ForegroundColor Gray
Write-Host "   • Should redirect to dashboard after successful login" -ForegroundColor Gray
Write-Host ""

Write-Host "2. 🎛️  Dashboard Button Tests:" -ForegroundColor Yellow
Write-Host "   After logging in, test each button:" -ForegroundColor White
Write-Host ""
Write-Host "   📝 Create Project Button:" -ForegroundColor Cyan
Write-Host "      • Click 'Create Project' button" -ForegroundColor Gray
Write-Host "      • Should navigate to home page (/) for project creation" -ForegroundColor Gray
Write-Host "      • Should show concept input form" -ForegroundColor Gray
Write-Host ""
Write-Host "   🔍 Browse Repositories Button:" -ForegroundColor Cyan
Write-Host "      • Click 'Browse Repositories' button" -ForegroundColor Gray
Write-Host "      • Should navigate to /discovery page" -ForegroundColor Gray
Write-Host "      • Should show repository search interface" -ForegroundColor Gray
Write-Host ""
Write-Host "   📚 View Resources Button:" -ForegroundColor Cyan
Write-Host "      • Click 'View Resources' button" -ForegroundColor Gray
Write-Host "      • Should navigate to /resources page" -ForegroundColor Gray
Write-Host "      • Should show learning resources with categories" -ForegroundColor Gray
Write-Host ""

Write-Host "3. 🧭 Navigation Tests:" -ForegroundColor Yellow
Write-Host "   • Test 'Back to Dashboard' buttons on each page" -ForegroundColor Gray
Write-Host "   • Verify breadcrumb navigation works" -ForegroundColor Gray
Write-Host "   • Test browser back/forward buttons" -ForegroundColor Gray
Write-Host ""

Write-Host "4. 🎯 Expected Results:" -ForegroundColor Yellow
Write-Host "   ✅ No JavaScript errors in browser console" -ForegroundColor Green
Write-Host "   ✅ All buttons respond to clicks immediately" -ForegroundColor Green
Write-Host "   ✅ Navigation works smoothly between pages" -ForegroundColor Green
Write-Host "   ✅ Authentication state persists across navigation" -ForegroundColor Green
Write-Host "   ✅ Learning resources page displays categorized content" -ForegroundColor Green
Write-Host "   ✅ Repository discovery page shows search interface" -ForegroundColor Green
Write-Host ""

Write-Host "🚀 Quick Test Links:" -ForegroundColor Magenta
Write-Host "===================" -ForegroundColor Magenta
Write-Host "• Main App:      $frontendUrl" -ForegroundColor White
Write-Host "• Dashboard:     $frontendUrl#/dashboard" -ForegroundColor White
Write-Host "• Resources:     $frontendUrl#/resources" -ForegroundColor White
Write-Host "• Discovery:     $frontendUrl#/discovery" -ForegroundColor White
Write-Host ""

Write-Host "📊 What Was Fixed:" -ForegroundColor Magenta
Write-Host "==================" -ForegroundColor Magenta
Write-Host "✅ Added onClick handlers to all dashboard buttons" -ForegroundColor Green
Write-Host "✅ Created LearningResourcesPage with categorized content" -ForegroundColor Green
Write-Host "✅ Created RepositoryDiscoveryPage with search interface" -ForegroundColor Green
Write-Host "✅ Updated AppRouter with new routes (/resources, /discovery)" -ForegroundColor Green
Write-Host "✅ Added proper navigation and breadcrumbs" -ForegroundColor Green
Write-Host "✅ Maintained authentication state across navigation" -ForegroundColor Green
Write-Host ""

Write-Host "🎉 The dashboard buttons should now work correctly!" -ForegroundColor Green
Write-Host "   If you encounter any issues, check the browser console for errors." -ForegroundColor Gray
Write-Host ""

# Open the frontend in default browser
Write-Host "🌐 Opening frontend in your default browser..." -ForegroundColor Cyan
Start-Process $frontendUrl

Write-Host ""
Write-Host "✨ Test completed! Please verify the button functionality manually." -ForegroundColor Green