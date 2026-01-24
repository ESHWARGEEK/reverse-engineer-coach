#!/usr/bin/env pwsh

Write-Host "🚀 Deploying Frontend to Netlify..." -ForegroundColor Green

# Navigate to frontend directory
Set-Location frontend

Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
npm ci

Write-Host "🔨 Building React app..." -ForegroundColor Yellow
$env:SKIP_PREFLIGHT_CHECK = "true"
$env:GENERATE_SOURCEMAP = "false"
$env:CI = "false"
npm run build

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Build successful!" -ForegroundColor Green
    Write-Host "📁 Build files are in: frontend/build" -ForegroundColor Cyan
    
    # Check if build directory exists and has files
    if (Test-Path "build" -PathType Container) {
        $fileCount = (Get-ChildItem "build" -Recurse -File).Count
        Write-Host "📊 Build contains $fileCount files" -ForegroundColor Cyan
        
        Write-Host "🌐 Ready for Netlify deployment!" -ForegroundColor Green
        Write-Host "💡 Push to GitHub to trigger automatic Netlify deployment" -ForegroundColor Yellow
    } else {
        Write-Host "❌ Build directory not found!" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}

# Return to root directory
Set-Location ..