#!/usr/bin/env pwsh

Write-Host "Testing Simplified Authentication System" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green

$backendUrl = "https://reverse-coach-backend.onrender.com"

# Test 1: Simple endpoint
Write-Host "`n1. Testing simple endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$backendUrl/api/v1/auth/debug/test-simple" -Method POST
    Write-Host "✅ Simple endpoint works: $($response.message)" -ForegroundColor Green
} catch {
    Write-Host "❌ Simple endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Debug registration
Write-Host "`n2. Testing debug registration..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$backendUrl/api/v1/auth/debug/test-registration" -Method POST
    if ($response.success) {
        Write-Host "✅ Debug registration works!" -ForegroundColor Green
    } else {
        Write-Host "❌ Debug registration failed: $($response.error)" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Debug registration request failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Actual registration with simplified data
Write-Host "`n3. Testing actual registration..." -ForegroundColor Yellow
$testEmail = "test$(Get-Random)@example.com"
$registrationData = @{
    email = $testEmail
    password = "TestPassword123!"
    preferred_ai_provider = "gemini"
    preferred_language = "python"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$backendUrl/api/v1/auth/register" -Method POST -Body $registrationData -ContentType "application/json"
    Write-Host "✅ Registration successful!" -ForegroundColor Green
    Write-Host "   User ID: $($response.user_id)" -ForegroundColor Cyan
    Write-Host "   Email: $($response.email)" -ForegroundColor Cyan
    Write-Host "   Token Type: $($response.token_type)" -ForegroundColor Cyan
    
    # Test 4: Login with the same credentials
    Write-Host "`n4. Testing login..." -ForegroundColor Yellow
    $loginData = @{
        email = $testEmail
        password = "TestPassword123!"
    } | ConvertTo-Json
    
    $loginResponse = Invoke-RestMethod -Uri "$backendUrl/api/v1/auth/login" -Method POST -Body $loginData -ContentType "application/json"
    Write-Host "✅ Login successful!" -ForegroundColor Green
    Write-Host "   User ID: $($loginResponse.user_id)" -ForegroundColor Cyan
    Write-Host "   Last Login: $($loginResponse.last_login)" -ForegroundColor Cyan
    
} catch {
    $errorDetails = $_.Exception.Message
    if ($_.Exception.Response) {
        try {
            $errorStream = $_.Exception.Response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($errorStream)
            $errorBody = $reader.ReadToEnd()
            $errorDetails += " - Response: $errorBody"
        } catch {
            # Ignore error reading response
        }
    }
    Write-Host "❌ Registration/Login failed: $errorDetails" -ForegroundColor Red
}

Write-Host "`n=======================================" -ForegroundColor Green
Write-Host "Authentication test completed!" -ForegroundColor Green