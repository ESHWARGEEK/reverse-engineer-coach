#!/usr/bin/env pwsh

Write-Host "Testing Frontend Status..." -ForegroundColor Green

# Check if frontend is running on port 3000
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 10 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Frontend is running successfully on http://localhost:3000" -ForegroundColor Green
        Write-Host "✅ Status Code: $($response.StatusCode)" -ForegroundColor Green
        
        # Check if the response contains React content
        if ($response.Content -match "react" -or $response.Content -match "root") {
            Write-Host "✅ React app appears to be loaded correctly" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Response received but may not be React app" -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ Frontend returned status code: $($response.StatusCode)" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Could not connect to frontend: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Make sure the frontend is running with 'npm start' in the frontend directory" -ForegroundColor Yellow
}

Write-Host "`nFrontend test completed." -ForegroundColor Cyan