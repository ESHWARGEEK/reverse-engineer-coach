#!/usr/bin/env pwsh

# Backend Deployment Script for Render
# This script helps deploy the backend to Render.com (FREE tier)

Write-Host "🚀 Backend Deployment to Render" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host ""

# Check if git is configured
$gitUser = git config user.name
$gitEmail = git config user.email

if (-not $gitUser -or -not $gitEmail) {
    Write-Host "⚠️  Git not configured. Please set up git first:" -ForegroundColor Yellow
    Write-Host "   git config --global user.name 'Your Name'"
    Write-Host "   git config --global user.email 'your.email@example.com'"
    Write-Host ""
}

# Check current git status
Write-Host "📋 Current Git Status:" -ForegroundColor Cyan
git status --short

# Generate secure environment variables
Write-Host ""
Write-Host "🔐 Generating Secure Environment Variables:" -ForegroundColor Cyan
Write-Host "Copy these to your Render environment variables:" -ForegroundColor Yellow
Write-Host ""

$jwtSecret = [System.Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
$jwtRefreshSecret = [System.Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
$encryptionKey = [System.Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
$masterKey = [System.Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))

Write-Host "JWT_SECRET_KEY=$jwtSecret" -ForegroundColor Green
Write-Host "JWT_REFRESH_SECRET_KEY=$jwtRefreshSecret" -ForegroundColor Green
Write-Host "ENCRYPTION_KEY=$encryptionKey" -ForegroundColor Green
Write-Host "MASTER_ENCRYPTION_KEY=$masterKey" -ForegroundColor Green
Write-Host "CORS_ORIGINS=https://reveng.netlify.app" -ForegroundColor Green
Write-Host "ENVIRONMENT=production" -ForegroundColor Green
Write-Host "DEBUG=false" -ForegroundColor Green
Write-Host ""

# Save environment variables to a file for reference
$envContent = @"
# Environment Variables for Render Deployment
# Copy these to your Render web service environment variables

JWT_SECRET_KEY=$jwtSecret
JWT_REFRESH_SECRET_KEY=$jwtRefreshSecret
ENCRYPTION_KEY=$encryptionKey
MASTER_ENCRYPTION_KEY=$masterKey
CORS_ORIGINS=https://reveng.netlify.app
ENVIRONMENT=production
DEBUG=false

# Database URL will be automatically provided by Render PostgreSQL
# DATABASE_URL=postgresql://user:pass@hostname:5432/dbname
"@

$envContent | Out-File -FilePath "render-environment-variables.txt" -Encoding UTF8
Write-Host "💾 Environment variables saved to: render-environment-variables.txt" -ForegroundColor Green
Write-Host ""

# Instructions for deployment
Write-Host "📝 Deployment Instructions:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. 🐙 Create GitHub Repository:" -ForegroundColor Yellow
Write-Host "   - Go to https://github.com/new"
Write-Host "   - Name: reverse-engineer-coach"
Write-Host "   - Make it public (required for free Render)"
Write-Host "   - Don't initialize with README"
Write-Host ""

Write-Host "2. 📤 Push Code to GitHub:" -ForegroundColor Yellow
Write-Host "   git remote add origin https://github.com/YOUR_USERNAME/reverse-engineer-coach.git"
Write-Host "   git branch -M main"
Write-Host "   git push -u origin main"
Write-Host ""

Write-Host "3. 🌐 Deploy to Render:" -ForegroundColor Yellow
Write-Host "   - Go to https://render.com"
Write-Host "   - Sign up/Login with GitHub"
Write-Host "   - Click 'New +' → 'Web Service'"
Write-Host "   - Connect your GitHub repository"
Write-Host "   - Use these settings:"
Write-Host "     Name: reverse-coach-backend"
Write-Host "     Environment: Python 3"
Write-Host "     Build Command: cd backend && pip install -r requirements.txt"
Write-Host "     Start Command: cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port `$PORT"
Write-Host ""

Write-Host "4. 🗄️ Add PostgreSQL Database:" -ForegroundColor Yellow
Write-Host "   - Click 'New +' → 'PostgreSQL'"
Write-Host "   - Name: reverse-coach-db"
Write-Host "   - Copy the connection string"
Write-Host "   - Add DATABASE_URL to your web service environment variables"
Write-Host ""

Write-Host "5. 🔗 Connect Frontend to Backend:" -ForegroundColor Yellow
Write-Host "   - Your backend URL will be: https://reverse-coach-backend.onrender.com"
Write-Host "   - Go to Netlify dashboard: https://app.netlify.com"
Write-Host "   - Add environment variable: REACT_APP_API_URL=https://reverse-coach-backend.onrender.com"
Write-Host "   - Redeploy frontend"
Write-Host ""

Write-Host "✅ Ready for Deployment!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Checklist:" -ForegroundColor Cyan
Write-Host "□ Create GitHub repository" -ForegroundColor White
Write-Host "□ Push code to GitHub" -ForegroundColor White
Write-Host "□ Deploy to Render" -ForegroundColor White
Write-Host "□ Add PostgreSQL database" -ForegroundColor White
Write-Host "□ Set environment variables" -ForegroundColor White
Write-Host "□ Connect frontend to backend" -ForegroundColor White
Write-Host "□ Test the application" -ForegroundColor White
Write-Host ""

Write-Host "🎯 Your Live URLs:" -ForegroundColor Cyan
Write-Host "Frontend: https://reveng.netlify.app (✅ Already deployed)" -ForegroundColor Green
Write-Host "Backend: https://reverse-coach-backend.onrender.com (🔄 Deploy next)" -ForegroundColor Yellow
Write-Host ""

Write-Host "💰 Total Cost: $0/month (FREE tier)" -ForegroundColor Green
Write-Host ""

# Test backend locally before deployment
Write-Host "🧪 Test Backend Locally (Optional):" -ForegroundColor Cyan
Write-Host "cd backend && python -m uvicorn app.main:app --reload"
Write-Host "Visit: http://localhost:8000/docs"
Write-Host ""

Write-Host "Need help? Check these files:" -ForegroundColor Cyan
Write-Host "- MANUAL_RENDER_DEPLOYMENT.md"
Write-Host "- render-environment-variables.txt"
Write-Host "- render.yaml (deployment configuration)"
Write-Host ""

Write-Host "🚀 Happy Deploying!" -ForegroundColor Green