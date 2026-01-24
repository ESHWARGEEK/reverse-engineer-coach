#!/usr/bin/env pwsh

Write-Host "Debugging Registration Issue" -ForegroundColor Green
Write-Host "============================" -ForegroundColor Green

$backendUrl = "https://reverse-coach-backend.onrender.com"

# Test 1: Check if the debug endpoint exists
Write-Host "`n1. Testing debug registration endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$backendUrl/api/v1/auth/debug/test-registration" -Method POST
    Write-Host "✅ Debug endpoint response:" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json -Depth 3) -ForegroundColor Cyan
} catch {
    Write-Host "❌ Debug endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode
        Write-Host "   Status Code: $statusCode" -ForegroundColor Yellow
    }
}

# Test 2: Try registration with minimal data
Write-Host "`n2. Testing minimal registration data..." -ForegroundColor Yellow
$minimalData = @{
    email = "minimal@example.com"
    password = "TestPass123!"
} | ConvertTo-Json

try {
    $headers = @{
        "Content-Type" = "application/json"
        "User-Agent" = "PowerShell-Test/1.0"
    }
    
    $response = Invoke-RestMethod -Uri "$backendUrl/api/v1/auth/register" -Method POST -Body $minimalData -Headers $headers
    Write-Host "✅ Minimal registration successful!" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json -Depth 2) -ForegroundColor Cyan
} catch {
    Write-Host "❌ Minimal registration failed: $($_.Exception.Message)" -ForegroundColor Red
    
    # Try to get more details from the error response
    if ($_.Exception.Response) {
        try {
            $errorStream = $_.Exception.Response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($errorStream)
            $errorBody = $reader.ReadToEnd()
            Write-Host "   Error Response: $errorBody" -ForegroundColor Yellow
        } catch {
            Write-Host "   Could not read error response" -ForegroundColor Yellow
        }
    }
}

# Test 3: Check health endpoint
Write-Host "`n3. Checking backend health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$backendUrl/health"
    Write-Host "✅ Backend health:" -ForegroundColor Green
    Write-Host ($health | ConvertTo-Json -Depth 2) -ForegroundColor Cyan
} catch {
    Write-Host "❌ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n============================" -ForegroundColor Green