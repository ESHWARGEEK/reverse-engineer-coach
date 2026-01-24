#!/usr/bin/env pwsh

Write-Host "🚀 Deploying CORS Fix to Render Backend..." -ForegroundColor Cyan

# Check if we're in the right directory
if (-not (Test-Path "backend/app/main.py")) {
    Write-Host "❌ Error: Please run this script from the project root directory" -ForegroundColor Red
    exit 1
}

Write-Host "`n📋 CORS Fix Summary:" -ForegroundColor Yellow
Write-Host "✅ Updated validation middleware to skip OPTIONS requests" -ForegroundColor Green
Write-Host "✅ Added https://reveng.netlify.app to CORS origins" -ForegroundColor Green
Write-Host "⏳ Need to deploy to Render production" -ForegroundColor Yellow

# Check if git is available
$gitAvailable = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitAvailable) {
    Write-Host "❌ Git not found. Please install Git to deploy changes." -ForegroundColor Red
    exit 1
}

# Check git status
Write-Host "`n🔍 Checking git status..." -ForegroundColor Cyan
try {
    $gitStatus = git status --porcelain
    if ($gitStatus) {
        Write-Host "📝 Found uncommitted changes:" -ForegroundColor Yellow
        git status --short
        
        Write-Host "`n💾 Committing CORS fix changes..." -ForegroundColor Cyan
        git add backend/app/middleware/validation_middleware.py
        git add backend/.env
        git add CORS_FIX_SUMMARY.md
        git add test-cors-fix.ps1
        git add update-cors-and-deploy.ps1
        git add test-frontend-auth.ps1
        
        git commit -m "Fix CORS issue: Skip validation for OPTIONS requests

- Updated validation middleware to allow CORS preflight requests
- Added https://reveng.netlify.app to CORS origins
- This resolves 'blocked by CORS policy' errors in frontend"
        
        Write-Host "✅ Changes committed successfully!" -ForegroundColor Green
    } else {
        Write-Host "✅ No uncommitted changes found" -ForegroundColor Green
    }
}
catch {
    Write-Host "❌ Git operation failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Check if we have a remote repository
Write-Host "`n🔗 Checking git remote..." -ForegroundColor Cyan
try {
    $remotes = git remote -v
    if (-not $remotes) {
        Write-Host "❌ No git remote found. Please set up a remote repository." -ForegroundColor Red
        Write-Host "Run: git remote add origin <your-repo-url>" -ForegroundColor Gray
        exit 1
    }
    
    Write-Host "✅ Git remote configured:" -ForegroundColor Green
    Write-Host $remotes -ForegroundColor Gray
}
catch {
    Write-Host "❌ Could not check git remote: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Push changes
Write-Host "`n📤 Pushing changes to trigger Render deployment..." -ForegroundColor Cyan
try {
    git push origin main
    Write-Host "✅ Changes pushed successfully!" -ForegroundColor Green
}
catch {
    Write-Host "❌ Git push failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Please push manually: git push origin main" -ForegroundColor Yellow
}

# Monitor deployment
Write-Host "`n⏳ Render will now automatically deploy the changes..." -ForegroundColor Yellow
Write-Host "This typically takes 2-3 minutes." -ForegroundColor Gray

Write-Host "`n🔍 Monitoring deployment progress..." -ForegroundColor Cyan
Write-Host "1. Go to https://dashboard.render.com" -ForegroundColor Gray
Write-Host "2. Find your 'reverse-coach-backend' service" -ForegroundColor Gray
Write-Host "3. Check the 'Events' tab for deployment status" -ForegroundColor Gray

# Wait and test
Write-Host "`n⏱️  Waiting 30 seconds before testing..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host "`n🧪 Testing CORS after deployment..." -ForegroundColor Cyan
$maxAttempts = 6
$attempt = 1

while ($attempt -le $maxAttempts) {
    Write-Host "Attempt $attempt/$maxAttempts..." -ForegroundColor Gray
    
    try {
        $response = Invoke-WebRequest -Uri "https://reverse-coach-backend.onrender.com/api/v1/auth/login" `
            -Method OPTIONS `
            -Headers @{
                "Origin" = "https://reveng.netlify.app"
                "Access-Control-Request-Method" = "POST"
                "Access-Control-Request-Headers" = "Content-Type,Authorization"
            } `
            -UseBasicParsing `
            -TimeoutSec 10

        if ($response.StatusCode -eq 200 -and $response.Headers["Access-Control-Allow-Origin"]) {
            Write-Host "✅ CORS fix deployed successfully!" -ForegroundColor Green
            Write-Host "Status Code: $($response.StatusCode)" -ForegroundColor Gray
            Write-Host "CORS Origin: $($response.Headers['Access-Control-Allow-Origin'])" -ForegroundColor Gray
            break
        } else {
            Write-Host "⚠️  Deployment still in progress..." -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "⚠️  Backend not ready yet..." -ForegroundColor Yellow
    }
    
    if ($attempt -lt $maxAttempts) {
        Write-Host "Waiting 30 seconds before next attempt..." -ForegroundColor Gray
        Start-Sleep -Seconds 30
    }
    
    $attempt++
}

if ($attempt -gt $maxAttempts) {
    Write-Host "⏳ Deployment is taking longer than expected." -ForegroundColor Yellow
    Write-Host "Please check Render dashboard for deployment status." -ForegroundColor Gray
}

Write-Host "`n📋 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Wait for Render deployment to complete" -ForegroundColor Gray
Write-Host "2. Test authentication at https://reveng.netlify.app" -ForegroundColor Gray
Write-Host "3. Verify no CORS errors in browser console" -ForegroundColor Gray

Write-Host "`n✨ CORS Fix Deployment Complete!" -ForegroundColor Green