# Quick Deploy Script for Reverse Engineer Coach
# This script helps you deploy to the internet quickly

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("netlify", "railway", "render", "all")]
    [string]$Platform = "all",
    
    [Parameter(Mandatory=$false)]
    [string]$Domain = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$Help
)

if ($Help) {
    Write-Host "🚀 Quick Deploy Script for Reverse Engineer Coach" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage: .\quick-deploy.ps1 [-Platform <platform>] [-Domain <domain>]" -ForegroundColor White
    Write-Host ""
    Write-Host "Platforms:" -ForegroundColor Yellow
    Write-Host "  netlify  - Deploy frontend to Netlify (Free)" -ForegroundColor White
    Write-Host "  railway  - Deploy backend to Railway (Free tier)" -ForegroundColor White
    Write-Host "  render   - Deploy backend to Render (Free tier)" -ForegroundColor White
    Write-Host "  all      - Deploy to Netlify + Railway (Default)" -ForegroundColor White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\quick-deploy.ps1" -ForegroundColor Gray
    Write-Host "  .\quick-deploy.ps1 -Platform netlify" -ForegroundColor Gray
    Write-Host "  .\quick-deploy.ps1 -Platform all -Domain myapp.com" -ForegroundColor Gray
    exit 0
}

Write-Host "🌐 Quick Deploy - Reverse Engineer Coach" -ForegroundColor Green
Write-Host "Platform: $Platform" -ForegroundColor Yellow

# Check prerequisites
Write-Host "📋 Checking prerequisites..." -ForegroundColor Yellow

# Check Node.js
try {
    $nodeVersion = node --version
    Write-Host "✅ Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js not found. Please install Node.js 18+ from https://nodejs.org" -ForegroundColor Red
    exit 1
}

# Check if we're in the right directory
if (-not (Test-Path "frontend/package.json")) {
    Write-Host "❌ Please run this script from the project root directory" -ForegroundColor Red
    exit 1
}

# Check if code is committed to git
try {
    $gitStatus = git status --porcelain
    if ($gitStatus) {
        Write-Host "⚠️  You have uncommitted changes. Consider committing them first:" -ForegroundColor Yellow
        Write-Host "   git add ." -ForegroundColor Gray
        Write-Host "   git commit -m 'Prepare for deployment'" -ForegroundColor Gray
        Write-Host "   git push origin main" -ForegroundColor Gray
        Write-Host ""
        $continue = Read-Host "Continue anyway? (y/N)"
        if ($continue -ne "y" -and $continue -ne "Y") {
            exit 0
        }
    }
} catch {
    Write-Host "⚠️  Git not initialized. Some platforms require Git." -ForegroundColor Yellow
}

# Deploy to Netlify (Frontend)
if ($Platform -eq "netlify" -or $Platform -eq "all") {
    Write-Host "🎯 Deploying frontend to Netlify..." -ForegroundColor Cyan
    
    # Check if Netlify CLI is installed
    try {
        netlify --version | Out-Null
    } catch {
        Write-Host "Installing Netlify CLI..." -ForegroundColor Yellow
        npm install -g netlify-cli
    }
    
    # Build frontend
    Write-Host "Building frontend..." -ForegroundColor Yellow
    Set-Location frontend
    
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
        npm install
    }
    
    Write-Host "Building production bundle..." -ForegroundColor Yellow
    npm run build
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Frontend build failed!" -ForegroundColor Red
        Set-Location ..
        exit 1
    }
    
    # Check Netlify login status
    Write-Host "Checking Netlify authentication..." -ForegroundColor Yellow
    try {
        $netlifyStatus = netlify status 2>&1
        if ($netlifyStatus -match "Not logged in") {
            Write-Host "Logging into Netlify..." -ForegroundColor Yellow
            netlify login
        }
    } catch {
        Write-Host "Logging into Netlify..." -ForegroundColor Yellow
        netlify login
    }
    
    # Check if site is already linked
    try {
        $siteInfo = netlify status 2>&1
        if ($siteInfo -match "No site linked") {
            Write-Host "Initializing new Netlify site..." -ForegroundColor Yellow
            netlify init
        }
    } catch {
        Write-Host "Initializing new Netlify site..." -ForegroundColor Yellow
        netlify init
    }
    
    # Deploy to production
    Write-Host "Deploying to Netlify..." -ForegroundColor Yellow
    netlify deploy --prod
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Frontend deployed to Netlify!" -ForegroundColor Green
        
        # Get the site URL
        try {
            $siteUrl = netlify status | Select-String "Website URL:" | ForEach-Object { $_.ToString().Split(": ")[1].Trim() }
            Write-Host "🌐 Frontend URL: $siteUrl" -ForegroundColor Cyan
        } catch {
            Write-Host "🌐 Check your Netlify dashboard for the site URL" -ForegroundColor Cyan
        }
    } else {
        Write-Host "❌ Netlify deployment failed!" -ForegroundColor Red
    }
    
    Set-Location ..
}

# Deploy to Railway (Backend)
if ($Platform -eq "railway" -or $Platform -eq "all") {
    Write-Host "🚂 Deploying backend to Railway..." -ForegroundColor Cyan
    
    # Check if Railway CLI is installed
    try {
        railway --version | Out-Null
    } catch {
        Write-Host "Installing Railway CLI..." -ForegroundColor Yellow
        npm install -g @railway/cli
    }
    
    # Login to Railway
    Write-Host "Checking Railway authentication..." -ForegroundColor Yellow
    try {
        $railwayStatus = railway status 2>&1
        if ($railwayStatus -match "not logged in" -or $railwayStatus -match "No project linked") {
            Write-Host "Logging into Railway..." -ForegroundColor Yellow
            railway login
        }
    } catch {
        Write-Host "Logging into Railway..." -ForegroundColor Yellow
        railway login
    }
    
    # Initialize Railway project if needed
    try {
        $projectStatus = railway status 2>&1
        if ($projectStatus -match "No project linked") {
            Write-Host "Initializing Railway project..." -ForegroundColor Yellow
            railway init
        }
    } catch {
        Write-Host "Initializing Railway project..." -ForegroundColor Yellow
        railway init
    }
    
    # Deploy to Railway
    Write-Host "Deploying to Railway..." -ForegroundColor Yellow
    railway up
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Backend deployed to Railway!" -ForegroundColor Green
        Write-Host "🌐 Check your Railway dashboard for the backend URL" -ForegroundColor Cyan
        Write-Host "⚙️  Don't forget to add environment variables in Railway dashboard:" -ForegroundColor Yellow
        Write-Host "   - CORS_ORIGINS (your Netlify URL)" -ForegroundColor Gray
        Write-Host "   - JWT_SECRET_KEY" -ForegroundColor Gray
        Write-Host "   - Other required variables" -ForegroundColor Gray
    } else {
        Write-Host "❌ Railway deployment failed!" -ForegroundColor Red
    }
}

# Deploy to Render (Backend alternative)
if ($Platform -eq "render") {
    Write-Host "🎨 Setting up Render deployment..." -ForegroundColor Cyan
    Write-Host "For Render deployment:" -ForegroundColor Yellow
    Write-Host "1. Push your code to GitHub if not already done" -ForegroundColor White
    Write-Host "2. Go to https://render.com" -ForegroundColor White
    Write-Host "3. Connect your GitHub repository" -ForegroundColor White
    Write-Host "4. Create a Web Service with these settings:" -ForegroundColor White
    Write-Host "   - Build Command: cd backend && pip install -r requirements.txt" -ForegroundColor Gray
    Write-Host "   - Start Command: cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port `$PORT" -ForegroundColor Gray
    Write-Host "5. Add environment variables in Render dashboard" -ForegroundColor White
    Write-Host "6. Create a PostgreSQL database and link it" -ForegroundColor White
}

Write-Host ""
Write-Host "🎉 Deployment process completed!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Yellow
Write-Host "1. Test your deployed application" -ForegroundColor White
Write-Host "2. Add environment variables in platform dashboards" -ForegroundColor White
Write-Host "3. Connect frontend to backend by updating REACT_APP_API_URL" -ForegroundColor White
Write-Host "4. Add your API keys (GitHub, OpenAI, etc.) for full functionality" -ForegroundColor White
Write-Host ""
Write-Host "📊 Monitor your deployment:" -ForegroundColor Yellow
Write-Host "   python scripts/deployment-status-dashboard.py" -ForegroundColor Gray
Write-Host ""
Write-Host "📖 For detailed instructions, see:" -ForegroundColor Yellow
Write-Host "   DEPLOY_TO_INTERNET_GUIDE.md" -ForegroundColor Gray