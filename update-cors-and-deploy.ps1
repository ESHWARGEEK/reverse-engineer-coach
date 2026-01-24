#!/usr/bin/env pwsh

Write-Host "🔧 Updating CORS Configuration and Redeploying Backend..." -ForegroundColor Cyan

# Check if we're in the right directory
if (-not (Test-Path "backend/app/main.py")) {
    Write-Host "❌ Error: Please run this script from the project root directory" -ForegroundColor Red
    exit 1
}

Write-Host "📋 Current CORS Configuration:" -ForegroundColor Yellow
Write-Host "Local Development: http://localhost:3000, http://127.0.0.1:3000" -ForegroundColor Gray
Write-Host "Production: https://reveng.netlify.app" -ForegroundColor Gray

# Check if Render CLI is available
$renderAvailable = Get-Command render -ErrorAction SilentlyContinue
if (-not $renderAvailable) {
    Write-Host "⚠️  Render CLI not found. Please install it or deploy manually through Render dashboard." -ForegroundColor Yellow
    Write-Host "Manual deployment steps:" -ForegroundColor Cyan
    Write-Host "1. Go to https://dashboard.render.com" -ForegroundColor Gray
    Write-Host "2. Find your 'reverse-coach-backend' service" -ForegroundColor Gray
    Write-Host "3. Click 'Manual Deploy' -> 'Deploy latest commit'" -ForegroundColor Gray
    Write-Host "4. Wait for deployment to complete" -ForegroundColor Gray
    
    # Test the current backend
    Write-Host "`n🧪 Testing current backend CORS configuration..." -ForegroundColor Cyan
    
    try {
        $response = Invoke-RestMethod -Uri "https://reverse-coach-backend.onrender.com/health" -Method GET -TimeoutSec 10
        Write-Host "✅ Backend is responding: $($response.status)" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Backend health check failed: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host "`n📝 Environment Variables to Verify on Render:" -ForegroundColor Yellow
    Write-Host "CORS_ORIGINS=https://reveng.netlify.app" -ForegroundColor Gray
    Write-Host "ENVIRONMENT=production" -ForegroundColor Gray
    Write-Host "DEBUG=false" -ForegroundColor Gray
    
    exit 0
}

# If Render CLI is available, attempt deployment
Write-Host "🚀 Attempting to redeploy backend service..." -ForegroundColor Cyan

try {
    # Get service info
    $services = render services list --format json | ConvertFrom-Json
    $backendService = $services | Where-Object { $_.name -like "*backend*" -or $_.name -like "*reverse-coach*" }
    
    if ($backendService) {
        Write-Host "📦 Found backend service: $($backendService.name)" -ForegroundColor Green
        
        # Trigger deployment
        render deploy --service-id $backendService.id
        
        Write-Host "✅ Deployment triggered successfully!" -ForegroundColor Green
        Write-Host "⏳ Please wait 2-3 minutes for deployment to complete..." -ForegroundColor Yellow
    }
    else {
        Write-Host "❌ Could not find backend service. Please deploy manually." -ForegroundColor Red
    }
}
catch {
    Write-Host "❌ Render CLI deployment failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Please deploy manually through Render dashboard." -ForegroundColor Yellow
}

Write-Host "`n🔍 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Wait for backend deployment to complete" -ForegroundColor Gray
Write-Host "2. Test authentication at https://reveng.netlify.app" -ForegroundColor Gray
Write-Host "3. Check browser console for any remaining CORS errors" -ForegroundColor Gray

Write-Host "`n✨ CORS Update Complete!" -ForegroundColor Green