#!/usr/bin/env pwsh

Write-Host "Deploying Simplified Authentication System" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green

# Check if we're in the right directory
if (-not (Test-Path "backend/app/services/auth_service.py")) {
    Write-Host "❌ Please run this script from the project root directory" -ForegroundColor Red
    exit 1
}

Write-Host "`n1. Checking git status..." -ForegroundColor Yellow
git status --porcelain

Write-Host "`n2. Adding changes to git..." -ForegroundColor Yellow
git add .

Write-Host "`n3. Committing changes..." -ForegroundColor Yellow
$commitMessage = "Simplify authentication: remove API key requirements from registration

- Remove GitHub token and AI API key from user registration
- Use system-wide credentials from environment variables
- Simplify frontend to only send email/password
- Add system credentials service for centralized API key management
- Update default AI provider to Gemini
- Add debug endpoints for testing

This resolves the 400 error during registration by removing complex
credential handling that was causing validation failures."

git commit -m $commitMessage

Write-Host "`n4. Pushing to GitHub..." -ForegroundColor Yellow
git push origin main

Write-Host "`n5. Waiting for Render deployment..." -ForegroundColor Yellow
Write-Host "   Render will automatically deploy from GitHub..." -ForegroundColor Cyan
Write-Host "   This usually takes 2-3 minutes..." -ForegroundColor Cyan

# Wait a bit for deployment to start
Start-Sleep -Seconds 30

Write-Host "`n6. Checking deployment status..." -ForegroundColor Yellow
$maxAttempts = 12  # 6 minutes total
$attempt = 0

do {
    $attempt++
    Write-Host "   Attempt $attempt/$maxAttempts - Checking backend health..." -ForegroundColor Cyan
    
    try {
        $response = Invoke-RestMethod -Uri "https://reverse-coach-backend.onrender.com/health" -TimeoutSec 10
        if ($response.status -eq "healthy") {
            Write-Host "✅ Backend is healthy!" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "   Backend not ready yet..." -ForegroundColor Yellow
    }
    
    if ($attempt -lt $maxAttempts) {
        Start-Sleep -Seconds 30
    }
} while ($attempt -lt $maxAttempts)

if ($attempt -ge $maxAttempts) {
    Write-Host "⚠️  Deployment may still be in progress. Check Render dashboard." -ForegroundColor Yellow
} else {
    Write-Host "`n7. Testing simplified authentication..." -ForegroundColor Yellow
    & "./test-simplified-auth.ps1"
}

Write-Host "`n=========================================" -ForegroundColor Green
Write-Host "Deployment completed!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. Set your actual GitHub token and Gemini API key in Render environment variables:" -ForegroundColor White
Write-Host "   SYSTEM_GITHUB_TOKEN=your_actual_github_token" -ForegroundColor Gray
Write-Host "   SYSTEM_GEMINI_API_KEY=your_actual_gemini_api_key" -ForegroundColor Gray
Write-Host "2. Test registration at https://reveng.netlify.app" -ForegroundColor White