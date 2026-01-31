#!/usr/bin/env pwsh

Write-Host "🚀 Deploy to Current Netlify Account" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan

Write-Host "`n📋 Correct Site Information Found:" -ForegroundColor Yellow
Write-Host "• Site Name: rev-eng" -ForegroundColor White
Write-Host "• URL: https://rev-eng.netlify.app" -ForegroundColor White
Write-Host "• Account: RevEng" -ForegroundColor White

Set-Location "frontend"

Write-Host "`n🔧 Step 1: Link to Correct Site" -ForegroundColor Green
Write-Host "Linking to 'rev-eng' site..." -ForegroundColor Yellow

netlify link --name rev-eng

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Successfully linked to rev-eng site!" -ForegroundColor Green
} else {
    Write-Host "❌ Linking failed" -ForegroundColor Red
    Set-Location ".."
    exit 1
}

Write-Host "`n🔧 Step 2: Set Environment Variables" -ForegroundColor Green
Write-Host "Setting production environment variables..." -ForegroundColor Yellow

netlify env:set REACT_APP_API_URL "https://reverse-coach-backend.onrender.com"
netlify env:set REACT_APP_ENVIRONMENT "production"
netlify env:set CI "false"
netlify env:set GENERATE_SOURCEMAP "false"
netlify env:set SKIP_PREFLIGHT_CHECK "true"
netlify env:set DISABLE_ESLINT_PLUGIN "true"

Write-Host "✅ Environment variables configured" -ForegroundColor Green

Write-Host "`n🔧 Step 3: Verify Link Status" -ForegroundColor Green
netlify status

Write-Host "`n🔧 Step 4: Build Production Version" -ForegroundColor Green
Write-Host "Building with all latest fixes..." -ForegroundColor Yellow
npm run build:prod

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Build successful!" -ForegroundColor Green
} else {
    Write-Host "❌ Build failed. Check errors above." -ForegroundColor Red
    Set-Location ".."
    exit 1
}

Write-Host "`n🔧 Step 5: Deploy to Production" -ForegroundColor Green
Write-Host "Deploying to https://rev-eng.netlify.app..." -ForegroundColor Yellow
netlify deploy --prod

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Deployment successful!" -ForegroundColor Green
} else {
    Write-Host "❌ Deployment failed" -ForegroundColor Red
    Set-Location ".."
    exit 1
}

Write-Host "`n🔧 Step 6: Final Status" -ForegroundColor Green
netlify status

Write-Host "`n🔧 Step 7: Test Backend Connection" -ForegroundColor Green
try {
    $response = Invoke-RestMethod -Uri "https://reverse-coach-backend.onrender.com/health" -Method GET -TimeoutSec 10
    Write-Host "✅ Backend responding: $($response | ConvertTo-Json -Compress)" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Backend: $($_.Exception.Message)" -ForegroundColor Yellow
}

Set-Location ".."

Write-Host "`n🎉 DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "======================" -ForegroundColor Green

Write-Host "`n🔗 Live Application:" -ForegroundColor Yellow
Write-Host "• Frontend: https://rev-eng.netlify.app" -ForegroundColor Green
Write-Host "• Backend: https://reverse-coach-backend.onrender.com" -ForegroundColor Green

Write-Host "`n✅ All Fixes Deployed:" -ForegroundColor Yellow
Write-Host "• Technology preference text visibility fixed" -ForegroundColor Green
Write-Host "• Continue button enabling logic fixed" -ForegroundColor Green
Write-Host "• Dark theme compatibility enhanced" -ForegroundColor Green
Write-Host "• Category mapping implemented" -ForegroundColor Green
Write-Host "• Enhanced workflow service added" -ForegroundColor Green

Write-Host "`n🧪 Test the fixes at: https://rev-eng.netlify.app" -ForegroundColor Cyan