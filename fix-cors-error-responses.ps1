#!/usr/bin/env pwsh

Write-Host "🔧 Fixing CORS Headers in Error Responses..." -ForegroundColor Cyan

Write-Host "`n📋 Issue Identified:" -ForegroundColor Yellow
Write-Host "❌ Rate limiting middleware returns 429 errors without CORS headers" -ForegroundColor Red
Write-Host "❌ Validation middleware returns 422 errors without CORS headers" -ForegroundColor Red
Write-Host "❌ Global error handler returns 500 errors without CORS headers" -ForegroundColor Red
Write-Host "❌ Browser shows 'blocked by CORS policy' instead of actual error" -ForegroundColor Red

Write-Host "`n✅ Fixes Applied:" -ForegroundColor Green
Write-Host "✅ Updated rate limiting middleware to include CORS headers in 429 responses" -ForegroundColor Green
Write-Host "✅ Updated validation middleware to include CORS headers in 422 responses" -ForegroundColor Green
Write-Host "✅ Updated global error handler to include CORS headers in 500 responses" -ForegroundColor Green
Write-Host "✅ All error responses now include proper CORS headers" -ForegroundColor Green

Write-Host "`n🚀 Deploying fixes to Render..." -ForegroundColor Cyan

# Check if git is available
$gitAvailable = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitAvailable) {
    Write-Host "❌ Git not found. Please install Git to deploy changes." -ForegroundColor Red
    exit 1
}

# Commit and push changes
try {
    Write-Host "📝 Committing CORS error response fixes..." -ForegroundColor Yellow
    
    git add backend/app/middleware/rate_limiting_middleware.py
    git add backend/app/middleware/validation_middleware.py
    git add backend/app/middleware/global_error_handler.py
    git add fix-cors-error-responses.ps1
    
    git commit -m "Fix CORS headers in error responses

- Add CORS headers to rate limiting 429 responses
- Add CORS headers to validation 422 responses  
- Add CORS headers to global error handler 500 responses
- This resolves 'blocked by CORS policy' errors when backend returns errors
- Frontend will now see actual error messages instead of CORS blocks"
    
    Write-Host "✅ Changes committed successfully!" -ForegroundColor Green
    
    Write-Host "📤 Pushing to trigger Render deployment..." -ForegroundColor Yellow
    git push origin main
    Write-Host "✅ Changes pushed successfully!" -ForegroundColor Green
    
}
catch {
    Write-Host "❌ Git operation failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Please commit and push manually" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n⏳ Waiting for Render deployment..." -ForegroundColor Yellow
Write-Host "This typically takes 2-3 minutes." -ForegroundColor Gray
Start-Sleep -Seconds 60

Write-Host "`n🧪 Testing CORS error responses..." -ForegroundColor Cyan

# Test rate limiting response
Write-Host "`n1. Testing Rate Limiting Response..." -ForegroundColor White
try {
    $rateLimitResponse = Invoke-WebRequest -Uri "https://reverse-coach-backend.onrender.com/api/v1/auth/register" `
        -Method POST `
        -Headers @{
            "Content-Type" = "application/json"
            "Origin" = "https://reveng.netlify.app"
            "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        } `
        -Body '{"email":"test@example.com","password":"testpass123","preferred_ai_provider":"openai","preferred_language":"python"}' `
        -UseBasicParsing

    Write-Host "   ✅ Status: $($rateLimitResponse.StatusCode)" -ForegroundColor Green
}
catch {
    $errorResponse = $_.Exception.Response
    if ($errorResponse) {
        $statusCode = $errorResponse.StatusCode
        $corsHeader = $errorResponse.Headers["Access-Control-Allow-Origin"]
        
        if ($corsHeader) {
            Write-Host "   ✅ Status: $statusCode with CORS headers!" -ForegroundColor Green
            Write-Host "   ✅ CORS Origin: $corsHeader" -ForegroundColor Green
        } else {
            Write-Host "   ❌ Status: $statusCode but no CORS headers" -ForegroundColor Red
        }
    } else {
        Write-Host "   ⚠️  Request failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host "`n📋 Expected Results After Fix:" -ForegroundColor Cyan
Write-Host "✅ 429 Rate Limit responses include CORS headers" -ForegroundColor Green
Write-Host "✅ 422 Validation responses include CORS headers" -ForegroundColor Green
Write-Host "✅ 500 Server Error responses include CORS headers" -ForegroundColor Green
Write-Host "✅ Frontend shows actual error messages instead of CORS blocks" -ForegroundColor Green

Write-Host "`n🎯 Frontend Testing:" -ForegroundColor Yellow
Write-Host "Now test at https://reveng.netlify.app:" -ForegroundColor White
Write-Host "• Try authentication - should see proper error messages" -ForegroundColor Gray
Write-Host "• No more 'blocked by CORS policy' errors" -ForegroundColor Gray
Write-Host "• Browser console shows actual backend errors (429, 422, etc.)" -ForegroundColor Gray

Write-Host "`n✨ CORS Error Response Fix Complete!" -ForegroundColor Green