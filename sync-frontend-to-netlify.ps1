#!/usr/bin/env pwsh

Write-Host "🔄 Syncing Frontend Changes to Netlify Repository..." -ForegroundColor Green

# Check if we have the frontend directory
if (-not (Test-Path "frontend")) {
    Write-Host "❌ Error: frontend directory not found" -ForegroundColor Red
    exit 1
}

# Create a temporary directory for the frontend repo
$tempDir = "temp-frontend-repo"
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}

Write-Host "📥 Cloning frontend repository..." -ForegroundColor Yellow
git clone https://github.com/ESHWARGEEK/reverse-engineer-coach-frontend.git $tempDir

if (-not (Test-Path $tempDir)) {
    Write-Host "❌ Failed to clone frontend repository" -ForegroundColor Red
    Write-Host "💡 The repository might not exist or you don't have access" -ForegroundColor Yellow
    Write-Host "🔧 Alternative: Reconfigure Netlify to use the main repository" -ForegroundColor Cyan
    exit 1
}

Write-Host "📋 Copying updated files..." -ForegroundColor Yellow

# Copy all frontend files to the temp repo
Copy-Item -Path "frontend/*" -Destination $tempDir -Recurse -Force

# Navigate to temp repo
Set-Location $tempDir

Write-Host "📝 Committing changes..." -ForegroundColor Yellow
git add .
git commit -m "Fix Netlify deployment: Remove terser patch, add cross-env, update build config

- Removed problematic postinstall script that was patching terser-webpack-plugin
- Added cross-env for cross-platform environment variable support  
- Updated package.json with build:prod script
- Added production environment variables
- Fixed React compatibility issues"

Write-Host "📤 Pushing to frontend repository..." -ForegroundColor Yellow
git push origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Successfully synced changes to frontend repository!" -ForegroundColor Green
    Write-Host "🌐 Netlify will automatically deploy the updated code" -ForegroundColor Cyan
} else {
    Write-Host "❌ Failed to push changes" -ForegroundColor Red
    Write-Host "💡 You may need to configure git credentials or check repository permissions" -ForegroundColor Yellow
}

# Clean up
Set-Location ..
Remove-Item -Recurse -Force $tempDir

Write-Host ""
Write-Host "🔍 Monitor deployment at: https://app.netlify.com" -ForegroundColor Cyan