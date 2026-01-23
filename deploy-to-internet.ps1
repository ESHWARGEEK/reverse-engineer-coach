# One-Click Internet Deployment Script
# This script helps you deploy to various cloud platforms

param(
    [string]$Platform = "vercel",
    [string]$Domain = "",
    [switch]$Help
)

if ($Help) {
    Write-Host "🚀 One-Click Internet Deployment" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage: .\deploy-to-internet.ps1 -Platform <platform> [-Domain <domain>]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Platforms:" -ForegroundColor Cyan
    Write-Host "  vercel     - Deploy to Vercel (Free)" -ForegroundColor White
    Write-Host "  netlify    - Deploy to Netlify (Free)" -ForegroundColor White
    Write-Host "  railway    - Deploy to Railway ($5/month)" -ForegroundColor White
    Write-Host "  render     - Deploy to Render (Free tier available)" -ForegroundColor White
    Write-Host "  heroku     - Deploy to Heroku ($7/month)" -ForegroundColor White
    Write-Host "  docker     - Deploy to your own server with Docker" -ForegroundColor White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Cyan
    Write-Host "  .\deploy-to-internet.ps1 -Platform vercel" -ForegroundColor Gray
    Write-Host "  .\deploy-to-internet.ps1 -Platform railway -Domain myapp.com" -ForegroundColor Gray
    Write-Host "  .\deploy-to-internet.ps1 -Platform docker -Domain myapp.com" -ForegroundColor Gray
    exit 0
}

Write-Host "🌐 Deploying Reverse Engineer Coach to the Internet" -ForegroundColor Green
Write-Host "Platform: $Platform" -ForegroundColor Yellow

switch ($Platform.ToLower()) {
    "vercel" {
        Write-Host "🔥 Deploying to Vercel..." -ForegroundColor Cyan
        
        # Check if Vercel CLI is installed
        try {
            vercel --version | Out-Null
        } catch {
            Write-Host "Installing Vercel CLI..." -ForegroundColor Yellow
            npm install -g vercel
        }
        
        # Build and deploy frontend
        Write-Host "Building frontend..." -ForegroundColor Yellow
        Set-Location frontend
        npm install
        npm run build
        
        Write-Host "Deploying to Vercel..." -ForegroundColor Yellow
        vercel --prod
        
        Write-Host "✅ Frontend deployed to Vercel!" -ForegroundColor Green
        Write-Host "⚠️  Note: You'll need to deploy the backend separately (try Railway or Render)" -ForegroundColor Yellow
    }
    
    "netlify" {
        Write-Host "🎯 Deploying to Netlify..." -ForegroundColor Cyan
        
        # Check if Netlify CLI is installed
        try {
            netlify --version | Out-Null
        } catch {
            Write-Host "Installing Netlify CLI..." -ForegroundColor Yellow
            npm install -g netlify-cli
        }
        
        # Build and deploy frontend
        Write-Host "Building frontend..." -ForegroundColor Yellow
        Set-Location frontend
        npm install
        npm run build
        
        Write-Host "Deploying to Netlify..." -ForegroundColor Yellow
        netlify deploy --prod --dir=build
        
        Write-Host "✅ Frontend deployed to Netlify!" -ForegroundColor Green
        Write-Host "⚠️  Note: You'll need to deploy the backend separately" -ForegroundColor Yellow
    }
    
    "railway" {
        Write-Host "🚂 Deploying to Railway..." -ForegroundColor Cyan
        
        # Check if Railway CLI is installed
        try {
            railway --version | Out-Null
        } catch {
            Write-Host "Installing Railway CLI..." -ForegroundColor Yellow
            npm install -g @railway/cli
        }
        
        Write-Host "Logging into Railway..." -ForegroundColor Yellow
        railway login
        
        Write-Host "Initializing Railway project..." -ForegroundColor Yellow
        railway init
        
        Write-Host "Deploying to Railway..." -ForegroundColor Yellow
        railway up
        
        Write-Host "✅ Application deployed to Railway!" -ForegroundColor Green
    }
    
    "render" {
        Write-Host "🎨 Setting up Render deployment..." -ForegroundColor Cyan
        Write-Host "1. Push your code to GitHub" -ForegroundColor Yellow
        Write-Host "2. Go to https://render.com" -ForegroundColor Yellow
        Write-Host "3. Connect your GitHub repository" -ForegroundColor Yellow
        Write-Host "4. Create a Web Service for the backend" -ForegroundColor Yellow
        Write-Host "5. Create a Static Site for the frontend" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Render will automatically deploy when you push to GitHub!" -ForegroundColor Green
    }
    
    "heroku" {
        Write-Host "🟣 Deploying to Heroku..." -ForegroundColor Cyan
        
        # Check if Heroku CLI is installed
        try {
            heroku --version | Out-Null
        } catch {
            Write-Host "Please install Heroku CLI from https://devcenter.heroku.com/articles/heroku-cli" -ForegroundColor Red
            exit 1
        }
        
        Write-Host "Logging into Heroku..." -ForegroundColor Yellow
        heroku login
        
        Write-Host "Creating Heroku apps..." -ForegroundColor Yellow
        $appName = if ($Domain) { $Domain.Replace(".", "-") } else { "reverse-coach-$(Get-Random)" }
        
        heroku create "$appName-backend"
        heroku create "$appName-frontend"
        
        Write-Host "Deploying backend..." -ForegroundColor Yellow
        Set-Location backend
        git init
        git add .
        git commit -m "Deploy to Heroku"
        heroku git:remote -a "$appName-backend"
        git push heroku main
        
        Write-Host "✅ Deployed to Heroku!" -ForegroundColor Green
    }
    
    "docker" {
        Write-Host "🐳 Preparing Docker deployment..." -ForegroundColor Cyan
        
        if (-not $Domain) {
            Write-Host "❌ Domain is required for Docker deployment" -ForegroundColor Red
            Write-Host "Usage: .\deploy-to-internet.ps1 -Platform docker -Domain your-domain.com" -ForegroundColor Yellow
            exit 1
        }
        
        # Create production environment file
        Write-Host "Creating production configuration..." -ForegroundColor Yellow
        
        $prodEnv = @"
# Production Environment Configuration
POSTGRES_PASSWORD=$(New-Guid)
SECRET_KEY=$(New-Guid)
JWT_SECRET_KEY=$(New-Guid)
JWT_REFRESH_SECRET_KEY=$(New-Guid)
ENCRYPTION_KEY=$(New-Guid)
MASTER_ENCRYPTION_KEY=$(New-Guid)

# Domain Configuration
DOMAIN_NAME=$Domain
CORS_ORIGINS=https://$Domain
REACT_APP_API_URL=https://$Domain/api

# SSL Configuration
SSL_ENABLED=true
FORCE_HTTPS=true

# Add your API keys here
# GITHUB_TOKEN=your_github_token
# OPENAI_API_KEY=your_openai_key
# ANTHROPIC_API_KEY=your_anthropic_key
"@
        
        $prodEnv | Out-File -FilePath ".env.production" -Encoding UTF8
        
        Write-Host "✅ Created .env.production" -ForegroundColor Green
        Write-Host ""
        Write-Host "🚀 Next steps for Docker deployment:" -ForegroundColor Cyan
        Write-Host "1. Get a VPS (DigitalOcean, Linode, etc.)" -ForegroundColor White
        Write-Host "2. Point your domain to the server IP" -ForegroundColor White
        Write-Host "3. SSH into your server and run:" -ForegroundColor White
        Write-Host "   git clone <your-repo>" -ForegroundColor Gray
        Write-Host "   cd <your-repo>" -ForegroundColor Gray
        Write-Host "   python scripts/complete-production-deployment.py --domain $Domain" -ForegroundColor Gray
        Write-Host ""
        Write-Host "📋 Your production config is ready in .env.production" -ForegroundColor Green
    }
    
    default {
        Write-Host "❌ Unknown platform: $Platform" -ForegroundColor Red
        Write-Host "Run with -Help to see available platforms" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""
Write-Host "🎉 Deployment process completed!" -ForegroundColor Green
Write-Host "📊 Monitor your deployment with:" -ForegroundColor Cyan
Write-Host "   python scripts/deployment-status-dashboard.py" -ForegroundColor Gray