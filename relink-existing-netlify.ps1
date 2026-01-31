#!/usr/bin/env pwsh

Write-Host "🔗 Relinking to Existing Netlify Site" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan

Write-Host "`n📋 Current Status:" -ForegroundColor Yellow
Write-Host "• Account: r64955208@gmail.com (Eshwar T)" -ForegroundColor White
Write-Host "• Existing Site: https://reveng.netlify.app" -ForegroundColor White
Write-Host "• Status: Project not linked locally" -ForegroundColor White

Set-Location "frontend"

Write-Host "`n🔧 Step 1: Check Current Login" -ForegroundColor Green
netlify status

Write-Host "`n🔧 Step 2: Link to Existing Site" -ForegroundColor Green
Write-Host "Linking to existing 'reveng' site..." -ForegroundColor Yellow

# Try to link to existing site by name
netlify link --name reveng

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Successfully linked to existing site!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Direct linking failed. Trying interactive linking..." -ForegroundColor Yellow
    netlify link
}

Write-Host "`n🔧 Step 3: Verify Link" -ForegroundColor Green
netlify status

Write-Host "`n🔧 Step 4: Check Environment Variables" -ForegroundColor Green
Write-Host "Current environment variables:" -ForegroundColor Yellow
netlify env:list

Write-Host "`n🔧 Step 5: Set Missing Environment Variables (if needed)" -ForegroundColor Green
Write-Host "Setting production environment variables..." -ForegroundColor Yellow

netlify env:set REACT_APP_API_URL "https://reverse-coach-backend.onrender.com"
netlify env:set REACT_APP_ENVIRONMENT "production"
netlify env:set CI "false"
netlify env:set GENERATE_SOURCEMAP "false"
netlify env:set SKIP_PREFLIGHT_CHECK "true"
netlify env:set DISABLE_ESLINT_PLUGIN "true"

Write-Host "`n🔧 Step 6: Build and Deploy" -ForegroundColor Green
Write-Host "Building latest version with all fixes..." -ForegroundColor Yellow
npm run build:prod

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Build successful" -ForegroundColor Green
    
    Write-Host "`nDeploying to production..." -ForegroundColor Yellow
    netlify deploy --prod
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Deployment successful!" -ForegroundColor Green
    } else {
        Write-Host "❌ Deployment failed" -ForegroundColor Red
    }
} else {
    Write-Host "❌ Build failed" -ForegroundColor Red
}

Write-Host "`n🎉 Relink Complete!" -ForegroundColor Green
Write-Host "==================" -ForegroundColor Green

Write-Host "`n📊 Final Status:" -ForegroundColor Yellow
netlify status

Write-Host "`n🔗 Your Site:" -ForegroundColor Yellow
Write-Host "• URL: https://reveng.netlify.app" -ForegroundColor Green
Write-Host "• Backend: https://reverse-coach-backend.onrender.com" -ForegroundColor Green
Write-Host "• All fixes included: Technology preference selector, button enabling, dark theme" -ForegroundColor Green

Write-Host "`n💡 Benefits of Relinking:" -ForegroundColor Cyan
Write-Host "• Keep existing URL (no need to update bookmarks)" -ForegroundColor White
Write-Host "• Maintain deployment history" -ForegroundColor White
Write-Host "• No backend CORS changes needed" -ForegroundColor White
Write-Host "• Use remaining credits on current account" -ForegroundColor White

Set-Location ".."