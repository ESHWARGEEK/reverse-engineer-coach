#!/usr/bin/env pwsh

Write-Host "🧪 Testing Frontend Build..." -ForegroundColor Green

# Navigate to frontend directory
Set-Location frontend

Write-Host "🧹 Cleaning previous build..." -ForegroundColor Yellow
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}

Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
npm ci

Write-Host "🔨 Testing build process..." -ForegroundColor Yellow
$env:SKIP_PREFLIGHT_CHECK = "true"
$env:GENERATE_SOURCEMAP = "false"
$env:CI = "false"
$env:REACT_APP_API_URL = "https://reverse-coach-backend.onrender.com"
$env:REACT_APP_ENVIRONMENT = "production"

npm run build

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Build test successful!" -ForegroundColor Green
    
    # Check build output
    if (Test-Path "build/index.html") {
        Write-Host "✅ index.html created" -ForegroundColor Green
    } else {
        Write-Host "❌ index.html missing" -ForegroundColor Red
    }
    
    if (Test-Path "build/static") {
        Write-Host "✅ Static assets created" -ForegroundColor Green
    } else {
        Write-Host "❌ Static assets missing" -ForegroundColor Red
    }
    
    $buildSize = (Get-ChildItem "build" -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host "📊 Build size: $([math]::Round($buildSize, 2)) MB" -ForegroundColor Cyan
    
} else {
    Write-Host "❌ Build test failed!" -ForegroundColor Red
    exit 1
}

# Return to root directory
Set-Location ..