#!/usr/bin/env pwsh

Write-Host "🚀 Deploying Netlify Fix..." -ForegroundColor Green

# Test build locally first
Write-Host "🧪 Testing build locally..." -ForegroundColor Yellow
Set-Location frontend
npm run build:prod

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Local build failed! Fix issues before deploying." -ForegroundColor Red
    Set-Location ..
    exit 1
}

Write-Host "✅ Local build successful!" -ForegroundColor Green
Set-Location ..

# Commit and push changes
Write-Host "📝 Committing changes..." -ForegroundColor Yellow
git add .
git commit -m "Fix Netlify deployment: Remove terser patch, add cross-env, update build config"

Write-Host "📤 Pushing to GitHub..." -ForegroundColor Yellow
git push origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Changes pushed successfully!" -ForegroundColor Green
    Write-Host "🌐 Netlify will automatically start deployment..." -ForegroundColor Cyan
    Write-Host "📊 Check deployment status at: https://app.netlify.com" -ForegroundColor Yellow
    Write-Host "⏱️  Deployment typically takes 2-5 minutes" -ForegroundColor Cyan
} else {
    Write-Host "❌ Failed to push changes!" -ForegroundColor Red
    exit 1
}