#!/usr/bin/env pwsh

Write-Host "🚀 Redeploying with New Netlify Account" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

Write-Host "`n📋 Prerequisites Check:" -ForegroundColor Yellow
Write-Host "• New email address for Netlify account" -ForegroundColor White
Write-Host "• Backend running at: https://reverse-coach-backend.onrender.com" -ForegroundColor White
Write-Host "• Project code ready in current directory" -ForegroundColor White

Write-Host "`n🔧 Step 1: Clean Current Netlify Configuration" -ForegroundColor Green
Set-Location "frontend"

if (Test-Path ".netlify") {
    Write-Host "Removing existing .netlify configuration..." -ForegroundColor Yellow
    Remove-Item -Path ".netlify" -Recurse -Force
    Write-Host "✅ Cleaned existing configuration" -ForegroundColor Green
} else {
    Write-Host "✅ No existing configuration found" -ForegroundColor Green
}

Write-Host "`n🔧 Step 2: Check Netlify CLI Status" -ForegroundColor Green
try {
    $status = netlify status 2>&1
    Write-Host "Current status: $status" -ForegroundColor White
} catch {
    Write-Host "⚠️  Netlify CLI not found. Please install: npm install -g netlify-cli" -ForegroundColor Red
    exit 1
}

Write-Host "`n🔧 Step 3: Logout from Current Account" -ForegroundColor Green
Write-Host "Logging out from current Netlify account..." -ForegroundColor Yellow
netlify logout

Write-Host "`n🔧 Step 4: Login with New Account" -ForegroundColor Green
Write-Host "Opening browser for new account login..." -ForegroundColor Yellow
Write-Host "Please login with your NEW email address" -ForegroundColor Cyan
netlify login

Write-Host "`n🔧 Step 5: Verify New Login" -ForegroundColor Green
$newStatus = netlify status
Write-Host "New account status: $newStatus" -ForegroundColor White

Write-Host "`n🔧 Step 6: Install Dependencies" -ForegroundColor Green
Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
npm install --legacy-peer-deps

Write-Host "`n🔧 Step 7: Initialize New Site" -ForegroundColor Green
Write-Host "Initializing new Netlify site..." -ForegroundColor Yellow
Write-Host "Follow the prompts to create a new site" -ForegroundColor Cyan
netlify init

Write-Host "`n🔧 Step 8: Set Environment Variables" -ForegroundColor Green
Write-Host "Setting production environment variables..." -ForegroundColor Yellow

netlify env:set REACT_APP_API_URL "https://reverse-coach-backend.onrender.com"
netlify env:set REACT_APP_ENVIRONMENT "production"
netlify env:set CI "false"
netlify env:set GENERATE_SOURCEMAP "false"
netlify env:set SKIP_PREFLIGHT_CHECK "true"
netlify env:set DISABLE_ESLINT_PLUGIN "true"

Write-Host "✅ Environment variables set" -ForegroundColor Green

Write-Host "`n🔧 Step 9: Build Project" -ForegroundColor Green
Write-Host "Building production version..." -ForegroundColor Yellow
npm run build:prod

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Build successful" -ForegroundColor Green
} else {
    Write-Host "❌ Build failed. Check errors above." -ForegroundColor Red
    exit 1
}

Write-Host "`n🔧 Step 10: Deploy to Production" -ForegroundColor Green
Write-Host "Deploying to new Netlify site..." -ForegroundColor Yellow
netlify deploy --prod

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Deployment successful!" -ForegroundColor Green
} else {
    Write-Host "❌ Deployment failed. Check errors above." -ForegroundColor Red
    exit 1
}

Write-Host "`n🔧 Step 11: Get Site Information" -ForegroundColor Green
$siteInfo = netlify status
Write-Host $siteInfo -ForegroundColor White

Write-Host "`n🔧 Step 12: Test Backend Connection" -ForegroundColor Green
Write-Host "Testing backend connectivity..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "https://reverse-coach-backend.onrender.com/health" -Method GET
    Write-Host "✅ Backend is responding: $($response | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Backend test failed: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "This might be normal if backend is sleeping. It will wake up on first request." -ForegroundColor White
}

Write-Host "`n🎉 Deployment Complete!" -ForegroundColor Green
Write-Host "===================" -ForegroundColor Green

Write-Host "`n📊 Summary:" -ForegroundColor Yellow
Write-Host "• New Netlify account configured" -ForegroundColor Green
Write-Host "• Fresh site deployed with all latest fixes" -ForegroundColor Green
Write-Host "• Backend connection configured" -ForegroundColor Green
Write-Host "• Environment variables set" -ForegroundColor Green

Write-Host "`n🔗 URLs:" -ForegroundColor Yellow
Write-Host "• Frontend: Check netlify status output above" -ForegroundColor White
Write-Host "• Backend: https://reverse-coach-backend.onrender.com" -ForegroundColor White

Write-Host "`n✅ Features Included:" -ForegroundColor Yellow
Write-Host "• Fixed technology preference selector text visibility" -ForegroundColor Green
Write-Host "• Fixed continue button enabling logic" -ForegroundColor Green
Write-Host "• Dark theme compatibility" -ForegroundColor Green
Write-Host "• Enhanced workflow components" -ForegroundColor Green
Write-Host "• Authentication system" -ForegroundColor Green
Write-Host "• CORS configuration" -ForegroundColor Green

Write-Host "`n💡 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Test the application in your browser" -ForegroundColor White
Write-Host "2. Verify all functionality works" -ForegroundColor White
Write-Host "3. Update any bookmarks with new URL" -ForegroundColor White
Write-Host "4. Share new URL with users" -ForegroundColor White

Write-Host "`n🎯 Your fresh deployment is ready!" -ForegroundColor Green

Set-Location ".."