#!/usr/bin/env pwsh

Write-Host "🔧 Updating Render CORS Configuration" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan

Write-Host "`n📋 What this script will do:" -ForegroundColor Yellow
Write-Host "1. Update CORS_ORIGINS environment variable on Render" -ForegroundColor White
Write-Host "2. Include both rev-eng.netlify.app and reveng.netlify.app" -ForegroundColor White
Write-Host "3. Trigger a redeploy to apply the changes" -ForegroundColor White

Write-Host "`n🔧 Step 1: Environment Variable Update" -ForegroundColor Green
Write-Host "The CORS_ORIGINS should be updated to:" -ForegroundColor Yellow
Write-Host "CORS_ORIGINS=https://rev-eng.netlify.app,https://reveng.netlify.app" -ForegroundColor Cyan

Write-Host "`n📝 Manual Steps Required:" -ForegroundColor Yellow
Write-Host "1. Go to https://dashboard.render.com" -ForegroundColor White
Write-Host "2. Navigate to your 'reverse-coach-backend' service" -ForegroundColor White
Write-Host "3. Go to Environment tab" -ForegroundColor White
Write-Host "4. Update CORS_ORIGINS to: https://rev-eng.netlify.app,https://reveng.netlify.app" -ForegroundColor White
Write-Host "5. Click 'Save Changes' to trigger automatic redeploy" -ForegroundColor White

Write-Host "`n🔧 Step 2: Test CORS After Update" -ForegroundColor Green
Write-Host "Testing current CORS configuration..." -ForegroundColor Yellow

try {
    $headers = @{ 
        'Origin' = 'https://rev-eng.netlify.app'
        'Access-Control-Request-Method' = 'POST'
        'Access-Control-Request-Headers' = 'Content-Type,Authorization'
    }
    
    $response = Invoke-WebRequest -Uri "https://reverse-coach-backend.onrender.com/api/v1/auth/login" -Method OPTIONS -Headers $headers -TimeoutSec 10
    
    Write-Host "✅ CORS preflight successful: $($response.StatusCode)" -ForegroundColor Green
    
    # Check for CORS headers
    $corsHeaders = @()
    if ($response.Headers['Access-Control-Allow-Origin']) {
        $corsHeaders += "Access-Control-Allow-Origin: $($response.Headers['Access-Control-Allow-Origin'])"
    }
    if ($response.Headers['Access-Control-Allow-Methods']) {
        $corsHeaders += "Access-Control-Allow-Methods: $($response.Headers['Access-Control-Allow-Methods'])"
    }
    if ($response.Headers['Access-Control-Allow-Headers']) {
        $corsHeaders += "Access-Control-Allow-Headers: $($response.Headers['Access-Control-Allow-Headers'])"
    }
    
    if ($corsHeaders.Count -gt 0) {
        Write-Host "✅ CORS headers present:" -ForegroundColor Green
        foreach ($header in $corsHeaders) {
            Write-Host "   $header" -ForegroundColor Cyan
        }
    } else {
        Write-Host "⚠️  No CORS headers found in response" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "❌ CORS preflight failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "💡 This is expected if CORS_ORIGINS hasn't been updated yet" -ForegroundColor Cyan
}

Write-Host "`n🔧 Step 3: Test Authentication Endpoint" -ForegroundColor Green
Write-Host "Testing auth endpoint accessibility..." -ForegroundColor Yellow

try {
    $testData = @{
        email = "test@example.com"
        password = "testpassword"
    } | ConvertTo-Json
    
    $headers = @{
        'Content-Type' = 'application/json'
        'Origin' = 'https://rev-eng.netlify.app'
    }
    
    # This should fail with 401 (unauthorized) but not CORS error
    $response = Invoke-RestMethod -Uri "https://reverse-coach-backend.onrender.com/api/v1/auth/login" -Method POST -Body $testData -Headers $headers -TimeoutSec 10
    
} catch {
    $errorMessage = $_.Exception.Message
    if ($errorMessage -like "*CORS*" -or $errorMessage -like "*Access-Control*") {
        Write-Host "❌ CORS error still present: $errorMessage" -ForegroundColor Red
        Write-Host "💡 Please update CORS_ORIGINS on Render dashboard" -ForegroundColor Yellow
    } elseif ($errorMessage -like "*401*" -or $errorMessage -like "*Unauthorized*") {
        Write-Host "✅ CORS working! Got expected 401 Unauthorized (correct behavior)" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Unexpected error: $errorMessage" -ForegroundColor Yellow
    }
}

Write-Host "`n📊 Summary:" -ForegroundColor Yellow
Write-Host "Current Netlify URL: https://rev-eng.netlify.app" -ForegroundColor Cyan
Write-Host "Required CORS_ORIGINS: https://rev-eng.netlify.app,https://reveng.netlify.app" -ForegroundColor Cyan
Write-Host "Backend URL: https://reverse-coach-backend.onrender.com" -ForegroundColor Cyan

Write-Host "`n🎯 Next Steps:" -ForegroundColor Green
Write-Host "1. Update CORS_ORIGINS on Render dashboard (manual step required)" -ForegroundColor White
Write-Host "2. Wait for automatic redeploy (2-3 minutes)" -ForegroundColor White
Write-Host "3. Test the frontend authentication again" -ForegroundColor White
Write-Host "4. Run this script again to verify CORS is working" -ForegroundColor White

Write-Host "`n🔗 Render Dashboard: https://dashboard.render.com" -ForegroundColor Cyan
Write-Host "🔗 Frontend URL: https://rev-eng.netlify.app" -ForegroundColor Cyan