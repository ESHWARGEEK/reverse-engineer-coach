#!/usr/bin/env pwsh

Write-Host "Testing registration with unique email..." -ForegroundColor Green

# Generate a unique email
$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$uniqueEmail = "test$timestamp@example.com"

Write-Host "Using email: $uniqueEmail" -ForegroundColor Yellow

# Test registration
$registrationData = @{
    email = $uniqueEmail
    password = "TestPassword123!"
    preferred_ai_provider = "openai"
    preferred_language = "python"
} | ConvertTo-Json

Write-Host "Attempting registration..." -ForegroundColor Blue

try {
    $response = Invoke-RestMethod -Uri "https://reverse-coach-backend.onrender.com/api/v1/auth/register" `
        -Method POST `
        -Headers @{
            "Content-Type" = "application/json"
            "Accept" = "application/json"
        } `
        -Body $registrationData `
        -ErrorAction Stop

    Write-Host "✅ Registration successful!" -ForegroundColor Green
    Write-Host "User ID: $($response.user_id)" -ForegroundColor Cyan
    Write-Host "Email: $($response.email)" -ForegroundColor Cyan
    Write-Host "Token received: $($response.access_token.Substring(0, 20))..." -ForegroundColor Cyan

} catch {
    $errorDetails = $_.Exception.Response
    if ($errorDetails) {
        $statusCode = $errorDetails.StatusCode
        $errorBody = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue
        
        Write-Host "❌ Registration failed with status: $statusCode" -ForegroundColor Red
        
        if ($errorBody) {
            Write-Host "Error: $($errorBody.detail)" -ForegroundColor Red
            if ($errorBody.retry_after) {
                Write-Host "Retry after: $($errorBody.retry_after) seconds" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "❌ Registration failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`nTest completed." -ForegroundColor Green