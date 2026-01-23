#!/usr/bin/env pwsh

# GitHub Push Helper Script
# Replace YOUR_USERNAME with your actual GitHub username

Write-Host "🚀 Pushing Code to GitHub" -ForegroundColor Green
Write-Host "=========================" -ForegroundColor Green
Write-Host ""

# Check if remote already exists
$remoteExists = git remote get-url origin 2>$null
if ($remoteExists) {
    Write-Host "✅ Remote origin already configured: $remoteExists" -ForegroundColor Green
} else {
    Write-Host "⚠️  Please run this command with your GitHub username:" -ForegroundColor Yellow
    Write-Host "git remote add origin https://github.com/YOUR_USERNAME/reverse-engineer-coach.git" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Replace YOUR_USERNAME with your actual GitHub username" -ForegroundColor Yellow
    Write-Host ""
    
    # Prompt for username
    $username = Read-Host "Enter your GitHub username"
    if ($username) {
        Write-Host "Adding remote origin..." -ForegroundColor Cyan
        git remote add origin "https://github.com/$username/reverse-engineer-coach.git"
        Write-Host "✅ Remote origin added!" -ForegroundColor Green
    } else {
        Write-Host "❌ Username required. Please run the git remote add command manually." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "📤 Pushing to GitHub..." -ForegroundColor Cyan

# Switch to main branch
Write-Host "Switching to main branch..." -ForegroundColor Cyan
git branch -M main

# Push to GitHub
Write-Host "Pushing code..." -ForegroundColor Cyan
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "🎉 Successfully pushed to GitHub!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Next Steps:" -ForegroundColor Cyan
    Write-Host "1. Go to https://render.com" -ForegroundColor White
    Write-Host "2. Sign up/Login with GitHub" -ForegroundColor White
    Write-Host "3. Create a new Web Service" -ForegroundColor White
    Write-Host "4. Connect your repository" -ForegroundColor White
    Write-Host ""
    Write-Host "📖 Follow the detailed guide in: DEPLOYMENT_NEXT_STEPS.md" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "❌ Push failed. Please check the error above." -ForegroundColor Red
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "- Repository doesn't exist on GitHub" -ForegroundColor White
    Write-Host "- Wrong username in the URL" -ForegroundColor White
    Write-Host "- Need to authenticate with GitHub" -ForegroundColor White
}