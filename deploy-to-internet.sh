#!/bin/bash

# One-Click Internet Deployment Script
# This script helps you deploy to various cloud platforms

set -e

# Default values
PLATFORM="vercel"
DOMAIN=""
HELP=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --platform)
            PLATFORM="$2"
            shift 2
            ;;
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --help|-h)
            HELP=true
            shift
            ;;
        *)
            echo "Unknown option $1"
            exit 1
            ;;
    esac
done

if [ "$HELP" = true ]; then
    echo "🚀 One-Click Internet Deployment"
    echo ""
    echo "Usage: ./deploy-to-internet.sh --platform <platform> [--domain <domain>]"
    echo ""
    echo "Platforms:"
    echo "  vercel     - Deploy to Vercel (Free)"
    echo "  netlify    - Deploy to Netlify (Free)"
    echo "  railway    - Deploy to Railway (\$5/month)"
    echo "  render     - Deploy to Render (Free tier available)"
    echo "  heroku     - Deploy to Heroku (\$7/month)"
    echo "  docker     - Deploy to your own server with Docker"
    echo ""
    echo "Examples:"
    echo "  ./deploy-to-internet.sh --platform vercel"
    echo "  ./deploy-to-internet.sh --platform railway --domain myapp.com"
    echo "  ./deploy-to-internet.sh --platform docker --domain myapp.com"
    exit 0
fi

echo "🌐 Deploying Reverse Engineer Coach to the Internet"
echo "Platform: $PLATFORM"

case "${PLATFORM,,}" in
    "vercel")
        echo "🔥 Deploying to Vercel..."
        
        # Check if Vercel CLI is installed
        if ! command -v vercel &> /dev/null; then
            echo "Installing Vercel CLI..."
            npm install -g vercel
        fi
        
        # Build and deploy frontend
        echo "Building frontend..."
        cd frontend
        npm install
        npm run build
        
        echo "Deploying to Vercel..."
        vercel --prod
        
        echo "✅ Frontend deployed to Vercel!"
        echo "⚠️  Note: You'll need to deploy the backend separately (try Railway or Render)"
        ;;
        
    "netlify")
        echo "🎯 Deploying to Netlify..."
        
        # Check if Netlify CLI is installed
        if ! command -v netlify &> /dev/null; then
            echo "Installing Netlify CLI..."
            npm install -g netlify-cli
        fi
        
        # Build and deploy frontend
        echo "Building frontend..."
        cd frontend
        npm install
        npm run build
        
        echo "Deploying to Netlify..."
        netlify deploy --prod --dir=build
        
        echo "✅ Frontend deployed to Netlify!"
        echo "⚠️  Note: You'll need to deploy the backend separately"
        ;;
        
    "railway")
        echo "🚂 Deploying to Railway..."
        
        # Check if Railway CLI is installed
        if ! command -v railway &> /dev/null; then
            echo "Installing Railway CLI..."
            npm install -g @railway/cli
        fi
        
        echo "Logging into Railway..."
        railway login
        
        echo "Initializing Railway project..."
        railway init
        
        echo "Deploying to Railway..."
        railway up
        
        echo "✅ Application deployed to Railway!"
        ;;
        
    "render")
        echo "🎨 Setting up Render deployment..."
        echo "1. Push your code to GitHub"
        echo "2. Go to https://render.com"
        echo "3. Connect your GitHub repository"
        echo "4. Create a Web Service for the backend"
        echo "5. Create a Static Site for the frontend"
        echo ""
        echo "Render will automatically deploy when you push to GitHub!"
        ;;
        
    "heroku")
        echo "🟣 Deploying to Heroku..."
        
        # Check if Heroku CLI is installed
        if ! command -v heroku &> /dev/null; then
            echo "Please install Heroku CLI from https://devcenter.heroku.com/articles/heroku-cli"
            exit 1
        fi
        
        echo "Logging into Heroku..."
        heroku login
        
        echo "Creating Heroku apps..."
        if [ -n "$DOMAIN" ]; then
            APP_NAME=$(echo "$DOMAIN" | sed 's/\./-/g')
        else
            APP_NAME="reverse-coach-$RANDOM"
        fi
        
        heroku create "$APP_NAME-backend"
        heroku create "$APP_NAME-frontend"
        
        echo "Deploying backend..."
        cd backend
        git init
        git add .
        git commit -m "Deploy to Heroku"
        heroku git:remote -a "$APP_NAME-backend"
        git push heroku main
        
        echo "✅ Deployed to Heroku!"
        ;;
        
    "docker")
        echo "🐳 Preparing Docker deployment..."
        
        if [ -z "$DOMAIN" ]; then
            echo "❌ Domain is required for Docker deployment"
            echo "Usage: ./deploy-to-internet.sh --platform docker --domain your-domain.com"
            exit 1
        fi
        
        # Create production environment file
        echo "Creating production configuration..."
        
        cat > .env.production << EOF
# Production Environment Configuration
POSTGRES_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -base64 32)
JWT_SECRET_KEY=$(openssl rand -base64 32)
JWT_REFRESH_SECRET_KEY=$(openssl rand -base64 32)
ENCRYPTION_KEY=$(openssl rand -base64 32)
MASTER_ENCRYPTION_KEY=$(openssl rand -base64 32)

# Domain Configuration
DOMAIN_NAME=$DOMAIN
CORS_ORIGINS=https://$DOMAIN
REACT_APP_API_URL=https://$DOMAIN/api

# SSL Configuration
SSL_ENABLED=true
FORCE_HTTPS=true

# Add your API keys here
# GITHUB_TOKEN=your_github_token
# OPENAI_API_KEY=your_openai_key
# ANTHROPIC_API_KEY=your_anthropic_key
EOF
        
        echo "✅ Created .env.production"
        echo ""
        echo "🚀 Next steps for Docker deployment:"
        echo "1. Get a VPS (DigitalOcean, Linode, etc.)"
        echo "2. Point your domain to the server IP"
        echo "3. SSH into your server and run:"
        echo "   git clone <your-repo>"
        echo "   cd <your-repo>"
        echo "   python scripts/complete-production-deployment.py --domain $DOMAIN"
        echo ""
        echo "📋 Your production config is ready in .env.production"
        ;;
        
    *)
        echo "❌ Unknown platform: $PLATFORM"
        echo "Run with --help to see available platforms"
        exit 1
        ;;
esac

echo ""
echo "🎉 Deployment process completed!"
echo "📊 Monitor your deployment with:"
echo "   python scripts/deployment-status-dashboard.py"