#!/usr/bin/env pwsh

# Render Deployment Status Checker
# This script helps monitor your Render deployment

Write-Host "🔍 Render Deployment Status Checker" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green
Write-Host ""

Write-Host "📋 Deployment Checklist:" -ForegroundColor Cyan
Write-Host ""

Write-Host "✅ Step 1: Code pushed to GitHub" -ForegroundColor Green
Write-Host "   Repository: https://github.com/ESHWARGEEK/reverse-engineer-coach" -ForegroundColor Gray
Write-Host ""

Write-Host "🔄 Step 2: Render Web Service Configuration" -ForegroundColor Yellow
Write-Host "   Expected settings:" -ForegroundColor Gray
Write-Host "   - Name: reverse-coach-backend" -ForegroundColor Gray
Write-Host "   - Environment: Python 3" -ForegroundColor Gray
Write-Host "   - Build Command: cd backend && pip install -r requirements.txt" -ForegroundColor Gray
Write-Host "   - Start Command: cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port `$PORT" -ForegroundColor Gray
Write-Host ""

Write-Host "🔄 Step 3: Environment Variables" -ForegroundColor Yellow
Write-Host "   Required variables (7 total):" -ForegroundColor Gray
Write-Host "   - JWT_SECRET_KEY" -ForegroundColor Gray
Write-Host "   - JWT_REFRESH_SECRET_KEY" -ForegroundColor Gray
Write-Host "   - ENCRYPTION_KEY" -ForegroundColor Gray
Write-Host "   - MASTER_ENCRYPTION_KEY" -ForegroundColor Gray
Write-Host "   - CORS_ORIGINS" -ForegroundColor Gray
Write-Host "   - ENVIRONMENT" -ForegroundColor Gray
Write-Host "   - DEBUG" -ForegroundColor Gray
Write-Host ""

Write-Host "🔄 Step 4: PostgreSQL Database" -ForegroundColor Yellow
Write-Host "   - Create PostgreSQL service in Render" -ForegroundColor Gray
Write-Host "   - Add DATABASE_URL to web service environment" -ForegroundColor Gray
Write-Host ""

Write-Host "🎯 Expected URLs after deployment:" -ForegroundColor Cyan
Write-Host "   Backend: https://reverse-coach-backend.onrender.com" -ForegroundColor Green
Write-Host "   API Docs: https://reverse-coach-backend.onrender.com/docs" -ForegroundColor Green
Write-Host "   Health Check: https://reverse-coach-backend.onrender.com/health" -ForegroundColor Green
Write-Host ""

Write-Host "🧪 Test Commands (run after deployment):" -ForegroundColor Cyan
Write-Host "   # Test health endpoint" -ForegroundColor Gray
Write-Host "   curl https://reverse-coach-backend.onrender.com/health" -ForegroundColor Green
Write-Host ""
Write-Host "   # Test API docs" -ForegroundColor Gray
Write-Host "   # Visit: https://reverse-coach-backend.onrender.com/docs" -ForegroundColor Green
Write-Host ""

Write-Host "⏱️  Deployment typically takes 5-10 minutes" -ForegroundColor Yellow
Write-Host ""

Write-Host "🆘 Common Issues:" -ForegroundColor Red
Write-Host "   - Build fails: Check that requirements.txt is in backend folder" -ForegroundColor White
Write-Host "   - Start fails: Verify the start command is correct" -ForegroundColor White
Write-Host "   - Database connection: Ensure DATABASE_URL is set correctly" -ForegroundColor White
Write-Host "   - CORS errors: Verify CORS_ORIGINS includes https://reveng.netlify.app" -ForegroundColor White
Write-Host ""

Write-Host "📖 Need help? Check these files:" -ForegroundColor Cyan
Write-Host "   - DEPLOYMENT_NEXT_STEPS.md" -ForegroundColor White
Write-Host "   - MANUAL_RENDER_DEPLOYMENT.md" -ForegroundColor White
Write-Host "   - render-environment-variables.txt" -ForegroundColor White
Write-Host ""

Write-Host "🚀 Once deployed, run the frontend connection script!" -ForegroundColor Green