#!/usr/bin/env pwsh

# Frontend Repository Setup Script
# This script helps set up a GitHub repository for the frontend

Write-Host "🚀 Frontend Repository Setup" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "frontend")) {
    Write-Host "❌ Error: frontend directory not found" -ForegroundColor Red
    Write-Host "Please run this script from the project root directory" -ForegroundColor Yellow
    exit 1
}

Write-Host "📋 Steps to create frontend repository:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Go to https://github.com/new" -ForegroundColor White
Write-Host "2. Repository name: reverse-engineer-coach-frontend" -ForegroundColor White
Write-Host "3. Make it PUBLIC (required for free Netlify)" -ForegroundColor White
Write-Host "4. Don't initialize with README" -ForegroundColor White
Write-Host "5. Click 'Create repository'" -ForegroundColor White
Write-Host ""

$continue = Read-Host "Have you created the GitHub repository? (y/n)"

if ($continue -ne "y" -and $continue -ne "Y") {
    Write-Host "Please create the repository first, then run this script again." -ForegroundColor Yellow
    exit 0
}

$username = Read-Host "Enter your GitHub username"
$repoUrl = "https://github.com/$username/reverse-engineer-coach-frontend.git"

Write-Host ""
Write-Host "🔧 Setting up git repository..." -ForegroundColor Cyan

# Navigate to frontend directory
Set-Location frontend

# Initialize git if not already done
if (-not (Test-Path ".git")) {
    Write-Host "Initializing git repository..." -ForegroundColor Gray
    git init
    git branch -M main
}

# Add all files
Write-Host "Adding files..." -ForegroundColor Gray
git add .

# Commit
Write-Host "Creating initial commit..." -ForegroundColor Gray
git commit -m "Initial frontend commit with React fixes and production config"

# Add remote
Write-Host "Adding remote origin..." -ForegroundColor Gray
git remote add origin $repoUrl

# Push to GitHub
Write-Host "Pushing to GitHub..." -ForegroundColor Gray
try {
    git push -u origin main
    Write-Host "✅ Successfully pushed to GitHub!" -ForegroundColor Green
} catch {
    Write-Host "❌ Error pushing to GitHub. Please check:" -ForegroundColor Red
    Write-Host "- Repository URL is correct" -ForegroundColor Yellow
    Write-Host "- You have push permissions" -ForegroundColor Yellow
    Write-Host "- Repository exists and is public" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🌐 Next steps:" -ForegroundColor Cyan
Write-Host "1. Go to https://app.netlify.com" -ForegroundColor White
Write-Host "2. Click 'Add new site' → 'Import an existing project'" -ForegroundColor White
Write-Host "3. Choose GitHub and select your repository" -ForegroundColor White
Write-Host "4. Build settings:" -ForegroundColor White
Write-Host "   - Build command: npm run build" -ForegroundColor Gray
Write-Host "   - Publish directory: build" -ForegroundColor Gray
Write-Host "5. Add environment variables:" -ForegroundColor White
Write-Host "   - REACT_APP_API_URL=https://reverse-coach-backend.onrender.com" -ForegroundColor Gray
Write-Host "   - REACT_APP_ENVIRONMENT=production" -ForegroundColor Gray
Write-Host "6. Deploy!" -ForegroundColor White

Write-Host ""
Write-Host "🎉 This will fix the React useRef error!" -ForegroundColor Green

# Return to original directory
Set-Location ..

Write-Host ""
Write-Host "Repository URL: $repoUrl" -ForegroundColor Cyan