#!/usr/bin/env pwsh

# Frontend-Backend Connection Script
# Run this after your backend is successfully deployed to Render

Write-Host "🔗 Connecting Frontend to Backend" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
Write-Host ""

$backendUrl = "https://reverse-coach-backend.onrender.com"

Write-Host "🧪 Testing Backend Deployment..." -ForegroundColor Cyan
Write-Host "Backend URL: $backendUrl" -ForegroundColor Gray
Write-Host ""

# Test if backend is accessible
try {
    Write-Host "Testing health endpoint..." -ForegroundColor Yellow
    $response = Invoke-RestMethod -Uri "$backendUrl/health" -Method GET -TimeoutSec 30
    Write-Host "✅ Backend is responding!" -ForegroundColor Green
    Write-Host "Status: $($response.status)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Backend not responding yet. Please wait for deployment to complete." -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "💡 Tips:" -ForegroundColor Yellow
    Write-Host "- Render deployments take 5-10 minutes" -ForegroundColor White
    Write-Host "- Check Render dashboard for build logs" -ForegroundColor White
    Write-Host "- Verify all environment variables are set" -ForegroundColor White
    Write-Host ""
    Write-Host "🔄 Run this script again once backend is deployed" -ForegroundColor Cyan
    exit 1
}

Write-Host ""
Write-Host "🌐 Updating Frontend Configuration..." -ForegroundColor Cyan
Write-Host ""

Write-Host "📋 Netlify Environment Variable Setup:" -ForegroundColor Yellow
Write-Host "1. Go to https://app.netlify.com" -ForegroundColor White
Write-Host "2. Click on your 'RevEng' site" -ForegroundColor White
Write-Host "3. Go to Site settings → Environment variables" -ForegroundColor White
Write-Host "4. Add this environment variable:" -ForegroundColor White
Write-Host ""
Write-Host "   Key: REACT_APP_API_URL" -ForegroundColor Green
Write-Host "   Value: $backendUrl" -ForegroundColor Green
Write-Host ""
Write-Host "5. Click 'Save'" -ForegroundColor White
Write-Host "6. Go to Deploys tab and click 'Trigger deploy'" -ForegroundColor White
Write-Host ""

Write-Host "🎯 Final Testing URLs:" -ForegroundColor Cyan
Write-Host "Frontend: https://reveng.netlify.app" -ForegroundColor Green
Write-Host "Backend: $backendUrl" -ForegroundColor Green
Write-Host "API Docs: $backendUrl/docs" -ForegroundColor Green
Write-Host "Health Check: $backendUrl/health" -ForegroundColor Green
Write-Host ""

Write-Host "✅ Next Steps:" -ForegroundColor Green
Write-Host "1. Add REACT_APP_API_URL to Netlify (instructions above)" -ForegroundColor White
Write-Host "2. Redeploy frontend on Netlify" -ForegroundColor White
Write-Host "3. Test the full application at https://reveng.netlify.app" -ForegroundColor White
Write-Host "4. Try creating an account and exploring features" -ForegroundColor White
Write-Host ""

Write-Host "🎉 Your AI-powered educational platform will be fully live!" -ForegroundColor Green
Write-Host ""

Write-Host "💰 Total Cost: $0/month (FREE forever)" -ForegroundColor Yellow
Write-Host "🚀 Features: User auth, AI analysis, project management, and more!" -ForegroundColor Yellow