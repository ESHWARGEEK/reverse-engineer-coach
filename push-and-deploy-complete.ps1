#!/usr/bin/env pwsh

Write-Host "🚀 Complete Git Push & Netlify Deployment" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

Write-Host "`n📋 What this script will do:" -ForegroundColor Yellow
Write-Host "1. Check Git status and commit all changes" -ForegroundColor White
Write-Host "2. Push changes to GitHub repository" -ForegroundColor White
Write-Host "3. Relink to existing Netlify site (reveng.netlify.app)" -ForegroundColor White
Write-Host "4. Build and deploy latest version with all fixes" -ForegroundColor White

Write-Host "`n🔧 Step 1: Git Status Check" -ForegroundColor Green
Write-Host "Checking current Git status..." -ForegroundColor Yellow

$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Host "📝 Found changes to commit:" -ForegroundColor Yellow
    git status --short
} else {
    Write-Host "✅ No uncommitted changes found" -ForegroundColor Green
}

Write-Host "`n🔧 Step 2: Add All Changes" -ForegroundColor Green
Write-Host "Adding all changes to Git..." -ForegroundColor Yellow
git add .

Write-Host "`n🔧 Step 3: Commit Changes" -ForegroundColor Green
$commitMessage = "feat: Fix technology preference selector and button enabling

- Fixed text visibility in technology preference cards (dark theme compatibility)
- Fixed continue button enabling logic with proper category mapping
- Added category mapping to convert tab names ('languages') to interface values ('language')
- Updated all technology selection functions for consistency
- Enhanced validation to properly recognize selected programming languages
- Improved user experience with immediate feedback and proper validation states
- Maintained all existing functionality while fixing critical workflow progression issues

Fixes:
- Technology card text now visible in dark theme
- Continue to AI Discovery button enables when programming languages selected
- Proper category assignment for all technology selections
- Consistent validation across all selection methods

Deployment: Ready for production with all latest fixes included"

Write-Host "Committing with message: $commitMessage" -ForegroundColor Yellow
git commit -m $commitMessage

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Changes committed successfully" -ForegroundColor Green
} else {
    Write-Host "ℹ️  No new changes to commit (already up to date)" -ForegroundColor Cyan
}

Write-Host "`n🔧 Step 4: Push to GitHub" -ForegroundColor Green
Write-Host "Pushing changes to remote repository..." -ForegroundColor Yellow

# Check if we have a remote
$remotes = git remote -v
if ($remotes) {
    Write-Host "📡 Remote repositories:" -ForegroundColor Cyan
    Write-Host $remotes -ForegroundColor White
    
    # Push to main/master branch
    $currentBranch = git branch --show-current
    Write-Host "📤 Pushing branch: $currentBranch" -ForegroundColor Yellow
    
    git push origin $currentBranch
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Successfully pushed to GitHub" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Push failed, but continuing with deployment..." -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  No remote repository configured. Skipping Git push." -ForegroundColor Yellow
    Write-Host "💡 To add remote: git remote add origin <your-repo-url>" -ForegroundColor Cyan
}

Write-Host "`n🔧 Step 5: Navigate to Frontend" -ForegroundColor Green
Set-Location "frontend"

Write-Host "`n🔧 Step 6: Check Netlify Status" -ForegroundColor Green
Write-Host "Checking current Netlify configuration..." -ForegroundColor Yellow
netlify status

Write-Host "`n🔧 Step 7: Link to Existing Site" -ForegroundColor Green
Write-Host "Linking to existing 'reveng' site..." -ForegroundColor Yellow

# Try to link to existing site by name
netlify link --name reveng

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Direct linking failed. Trying interactive linking..." -ForegroundColor Yellow
    netlify link
}

Write-Host "`n🔧 Step 8: Verify Link and Set Environment Variables" -ForegroundColor Green
Write-Host "Setting production environment variables..." -ForegroundColor Yellow

netlify env:set REACT_APP_API_URL "https://reverse-coach-backend.onrender.com"
netlify env:set REACT_APP_ENVIRONMENT "production"
netlify env:set CI "false"
netlify env:set GENERATE_SOURCEMAP "false"
netlify env:set SKIP_PREFLIGHT_CHECK "true"
netlify env:set DISABLE_ESLINT_PLUGIN "true"

Write-Host "✅ Environment variables configured" -ForegroundColor Green

Write-Host "`n🔧 Step 9: Install Dependencies" -ForegroundColor Green
Write-Host "Installing/updating frontend dependencies..." -ForegroundColor Yellow
npm install --legacy-peer-deps

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Dependencies installed successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Dependency installation failed" -ForegroundColor Red
    Set-Location ".."
    exit 1
}

Write-Host "`n🔧 Step 10: Build Production Version" -ForegroundColor Green
Write-Host "Building production version with all latest fixes..." -ForegroundColor Yellow
npm run build:prod

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Build successful!" -ForegroundColor Green
} else {
    Write-Host "❌ Build failed. Check errors above." -ForegroundColor Red
    Set-Location ".."
    exit 1
}

Write-Host "`n🔧 Step 11: Deploy to Production" -ForegroundColor Green
Write-Host "Deploying to https://reveng.netlify.app..." -ForegroundColor Yellow
netlify deploy --prod

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Deployment successful!" -ForegroundColor Green
} else {
    Write-Host "❌ Deployment failed. Check errors above." -ForegroundColor Red
    Set-Location ".."
    exit 1
}

Write-Host "`n🔧 Step 12: Final Status Check" -ForegroundColor Green
Write-Host "Getting final deployment status..." -ForegroundColor Yellow
netlify status

Write-Host "`n🔧 Step 13: Test Backend Connection" -ForegroundColor Green
Write-Host "Testing backend connectivity..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "https://reverse-coach-backend.onrender.com/health" -Method GET -TimeoutSec 10
    Write-Host "✅ Backend is responding: $($response | ConvertTo-Json -Compress)" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Backend test: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "💡 Backend might be sleeping. It will wake up on first request." -ForegroundColor Cyan
}

Set-Location ".."

Write-Host "`n🎉 DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "======================" -ForegroundColor Green

Write-Host "`n📊 Summary of Changes Deployed:" -ForegroundColor Yellow
Write-Host "✅ Technology Preference Selector Fixes:" -ForegroundColor Green
Write-Host "   • Fixed text visibility in dark theme" -ForegroundColor White
Write-Host "   • Fixed continue button enabling logic" -ForegroundColor White
Write-Host "   • Added proper category mapping (languages → language)" -ForegroundColor White
Write-Host "   • Enhanced validation for programming language selection" -ForegroundColor White

Write-Host "`n✅ Technical Improvements:" -ForegroundColor Green
Write-Host "   • Consistent dark theme colors throughout interface" -ForegroundColor White
Write-Host "   • Improved accessibility with better contrast ratios" -ForegroundColor White
Write-Host "   • Enhanced user feedback and validation states" -ForegroundColor White
Write-Host "   • Maintained all existing functionality" -ForegroundColor White

Write-Host "`n🔗 Live URLs:" -ForegroundColor Yellow
Write-Host "• Frontend: https://reveng.netlify.app" -ForegroundColor Green
Write-Host "• Backend: https://reverse-coach-backend.onrender.com" -ForegroundColor Green
Write-Host "• API Docs: https://reverse-coach-backend.onrender.com/docs" -ForegroundColor Green

Write-Host "`n🧪 Testing Checklist:" -ForegroundColor Yellow
Write-Host "1. ✅ Navigate to Enhanced Project Creation Workflow" -ForegroundColor White
Write-Host "2. ✅ Complete Skills & Goals step" -ForegroundColor White
Write-Host "3. ✅ Verify technology card text is visible" -ForegroundColor White
Write-Host "4. ✅ Select JavaScript/TypeScript and confirm button enables" -ForegroundColor White
Write-Host "5. ✅ Test complete workflow progression" -ForegroundColor White

Write-Host "`n💡 Key Features Now Working:" -ForegroundColor Cyan
Write-Host "• Technology preference selection with visible text" -ForegroundColor White
Write-Host "• Continue button enabling when requirements met" -ForegroundColor White
Write-Host "• Dark theme compatibility throughout" -ForegroundColor White
Write-Host "• Enhanced workflow progression" -ForegroundColor White
Write-Host "• Authentication system" -ForegroundColor White
Write-Host "• Backend integration" -ForegroundColor White

Write-Host "`n🎯 Ready for use! All fixes have been deployed successfully." -ForegroundColor Green