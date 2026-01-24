#!/usr/bin/env pwsh

Write-Host "🔧 Testing CORS Fix for Frontend-Backend Communication..." -ForegroundColor Cyan

# Test CORS preflight request
Write-Host "`n🧪 Testing CORS preflight request..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "https://reverse-coach-backend.onrender.com/api/v1/auth/login" `
        -Method OPTIONS `
        -Headers @{
            "Origin" = "https://reveng.netlify.app"
            "Access-Control-Request-Method" = "POST"
            "Access-Control-Request-Headers" = "Content-Type,Authorization"
        } `
        -UseBasicParsing

    Write-Host "✅ CORS preflight response received!" -ForegroundColor Green
    Write-Host "Status Code: $($response.StatusCode)" -ForegroundColor Gray
    
    # Check for CORS headers
    $corsHeaders = @(
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Methods", 
        "Access-Control-Allow-Headers",
        "Access-Control-Allow-Credentials"
    )
    
    $foundHeaders = @()
    foreach ($header in $corsHeaders) {
        if ($response.Headers[$header]) {
            $foundHeaders += "${header}: $($response.Headers[$header])"
        }
    }
    
    if ($foundHeaders.Count -gt 0) {
        Write-Host "✅ CORS headers found:" -ForegroundColor Green
        foreach ($header in $foundHeaders) {
            Write-Host "  $header" -ForegroundColor Gray
        }
    } else {
        Write-Host "❌ No CORS headers found in response" -ForegroundColor Red
    }
}
catch {
    Write-Host "❌ CORS preflight test failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test actual login request
Write-Host "`n🧪 Testing actual login request..." -ForegroundColor Yellow

try {
    $loginData = @{
        email = "test@example.com"
        password = "testpassword123"
    } | ConvertTo-Json

    $response = Invoke-WebRequest -Uri "https://reverse-coach-backend.onrender.com/api/v1/auth/login" `
        -Method POST `
        -Headers @{
            "Content-Type" = "application/json"
            "Origin" = "https://reveng.netlify.app"
            "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        } `
        -Body $loginData `
        -UseBasicParsing

    Write-Host "✅ Login request completed!" -ForegroundColor Green
    Write-Host "Status Code: $($response.StatusCode)" -ForegroundColor Gray
    
    # Parse response
    $responseData = $response.Content | ConvertFrom-Json
    if ($responseData.detail) {
        Write-Host "Response: $($responseData.detail)" -ForegroundColor Gray
    }
}
catch {
    $errorResponse = $_.Exception.Response
    if ($errorResponse) {
        $statusCode = $errorResponse.StatusCode
        Write-Host "Login request returned: $statusCode" -ForegroundColor Yellow
        
        try {
            $errorContent = $errorResponse.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($errorContent)
            $errorText = $reader.ReadToEnd()
            $errorData = $errorText | ConvertFrom-Json
            Write-Host "Error: $($errorData.detail)" -ForegroundColor Gray
        }
        catch {
            Write-Host "Could not parse error response" -ForegroundColor Gray
        }
    } else {
        Write-Host "❌ Login request failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Test frontend authentication flow
Write-Host "`n🧪 Testing frontend authentication flow..." -ForegroundColor Yellow

Write-Host "1. Open https://reveng.netlify.app in your browser" -ForegroundColor Gray
Write-Host "2. Try to sign in or register" -ForegroundColor Gray
Write-Host "3. Check browser console for CORS errors" -ForegroundColor Gray

Write-Host "`n📋 Expected Results:" -ForegroundColor Cyan
Write-Host "✅ No CORS errors in browser console" -ForegroundColor Green
Write-Host "✅ Authentication requests reach the backend" -ForegroundColor Green
Write-Host "✅ Proper error messages for invalid credentials" -ForegroundColor Green
Write-Host "✅ Successful login redirects to dashboard" -ForegroundColor Green

Write-Host "`n🔍 If CORS errors persist:" -ForegroundColor Yellow
Write-Host "1. Check that backend deployment includes the CORS fix" -ForegroundColor Gray
Write-Host "2. Verify CORS_ORIGINS environment variable on Render" -ForegroundColor Gray
Write-Host "3. Ensure validation middleware skips OPTIONS requests" -ForegroundColor Gray

Write-Host "`n✨ CORS Test Complete!" -ForegroundColor Green