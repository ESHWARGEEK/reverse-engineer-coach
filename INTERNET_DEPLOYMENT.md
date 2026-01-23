# Internet Deployment Guide

This comprehensive guide covers deploying the Reverse Engineer Coach application to the internet using various platforms and methods.

## Quick Start Options

### 🚀 One-Click Deployment Script

Use our automated deployment script for the fastest setup:

```powershell
# Windows
.\deploy-to-internet.ps1 -Platform vercel

# Or with custom domain
.\deploy-to-internet.ps1 -Platform railway -Domain myapp.com
```

```bash
# Linux/Mac
chmod +x deploy-to-internet.sh
./deploy-to-internet.sh --platform vercel
```

### 📋 Platform Comparison

| Platform | Cost | Complexity | Full-Stack | Best For |
|----------|------|------------|------------|----------|
| **Vercel** | Free tier | ⭐ Easy | Frontend only | Quick demos |
| **Netlify** | Free tier | ⭐ Easy | Frontend only | Static sites |
| **Railway** | $5/month | ⭐⭐ Medium | ✅ Yes | Full applications |
| **Render** | Free tier | ⭐⭐ Medium | ✅ Yes | Production apps |
| **Heroku** | $7/month | ⭐⭐ Medium | ✅ Yes | Traditional hosting |
| **DigitalOcean** | $6/month | ⭐⭐⭐ Hard | ✅ Yes | Custom control |
| **AWS/GCP** | Variable | ⭐⭐⭐⭐ Expert | ✅ Yes | Enterprise scale |

## Method 1: Vercel (Frontend Only) - FREE

**Best for**: Quick demos, frontend-only deployments

### Prerequisites
- GitHub account
- Node.js installed locally

### Steps

1. **Prepare Frontend**
   ```bash
   cd frontend
   npm install
   npm run build
   ```

2. **Deploy to Vercel**
   ```bash
   # Install Vercel CLI
   npm install -g vercel
   
   # Deploy
   vercel --prod
   ```

3. **Configure Environment**
   - Add environment variables in Vercel dashboard
   - Set `REACT_APP_API_URL` to your backend URL

### Limitations
- Frontend only - you'll need separate backend hosting
- No database included
- Limited to static site functionality

---

## Method 2: Railway (Full-Stack) - $5/month

**Best for**: Complete applications with database

### Prerequisites
- GitHub account
- Railway account

### Steps

1. **Install Railway CLI**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login and Initialize**
   ```bash
   railway login
   railway init
   ```

3. **Deploy**
   ```bash
   railway up
   ```

4. **Configure Services**
   - Railway will automatically detect your Docker setup
   - Add environment variables in Railway dashboard
   - Connect PostgreSQL database (included)

### Features
- ✅ Full-stack deployment
- ✅ PostgreSQL database included
- ✅ Automatic SSL certificates
- ✅ Custom domains supported
- ✅ Git-based deployments

---

## Method 3: Render (Full-Stack) - FREE tier available

**Best for**: Production applications with free tier

### Prerequisites
- GitHub account
- Render account

### Steps

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Prepare for Render deployment"
   git push origin main
   ```

2. **Create Services on Render**
   
   **Backend Service:**
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     - Build Command: `cd backend && pip install -r requirements.txt`
     - Start Command: `cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
     - Environment: Add all required variables

   **Frontend Service:**
   - Click "New +" → "Static Site"
   - Connect your GitHub repository
   - Configure:
     - Build Command: `cd frontend && npm install && npm run build`
     - Publish Directory: `frontend/build`

   **Database:**
   - Click "New +" → "PostgreSQL"
   - Note the connection details for backend configuration

### Features
- ✅ Free tier available
- ✅ Automatic deployments from Git
- ✅ SSL certificates included
- ✅ PostgreSQL database
- ✅ Custom domains (paid plans)

---

## Method 4: DigitalOcean Droplet (VPS) - $6/month

**Best for**: Full control, custom configurations

### Prerequisites
- DigitalOcean account
- Basic Linux knowledge
- Domain name (optional)

### Steps

1. **Create Droplet**
   - Choose Ubuntu 22.04 LTS
   - Select $6/month basic plan
   - Add SSH key for security

2. **Initial Server Setup**
   ```bash
   # SSH into your server
   ssh root@your-server-ip
   
   # Update system
   apt update && apt upgrade -y
   
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   
   # Install Docker Compose
   apt install docker-compose -y
   ```

3. **Deploy Application**
   ```bash
   # Clone your repository
   git clone https://github.com/yourusername/reverse-engineer-coach.git
   cd reverse-engineer-coach
   
   # Create production environment
   cp .env.example .env.production
   # Edit .env.production with your settings
   
   # Deploy
   python scripts/complete-production-deployment.py --domain your-domain.com
   ```

4. **Configure Domain (Optional)**
   ```bash
   # Point your domain to server IP in DNS settings
   # SSL will be automatically configured
   ```

### Features
- ✅ Full control over server
- ✅ Custom configurations
- ✅ Multiple applications on one server
- ✅ Root access
- ✅ Backup control

---

## Method 5: AWS/Google Cloud (Enterprise) - Variable cost

**Best for**: Enterprise applications, high scalability

### AWS Deployment

1. **Use AWS App Runner (Easiest)**
   ```bash
   # Build and push to ECR
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin your-account.dkr.ecr.us-east-1.amazonaws.com
   
   # Build and tag images
   docker build -t reverse-coach-backend ./backend
   docker tag reverse-coach-backend:latest your-account.dkr.ecr.us-east-1.amazonaws.com/reverse-coach-backend:latest
   
   # Push to ECR
   docker push your-account.dkr.ecr.us-east-1.amazonaws.com/reverse-coach-backend:latest
   ```

2. **Create App Runner Service**
   - Go to AWS App Runner console
   - Create service from ECR image
   - Configure environment variables
   - Add RDS PostgreSQL database

### Google Cloud Deployment

1. **Use Cloud Run**
   ```bash
   # Build and deploy
   gcloud builds submit --tag gcr.io/your-project/reverse-coach-backend ./backend
   gcloud run deploy --image gcr.io/your-project/reverse-coach-backend --platform managed
   ```

### Features
- ✅ Enterprise-grade scalability
- ✅ Global CDN
- ✅ Advanced monitoring
- ✅ High availability
- ✅ Professional support

---

## Environment Configuration

### Required Environment Variables

Create `.env.production` with these variables:

```env
# Database
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_USER=postgres
POSTGRES_DB=reverse_coach

# Security Keys (Generate unique values)
SECRET_KEY=your_secret_key_minimum_32_characters_long
JWT_SECRET_KEY=your_jwt_secret_key_here
JWT_REFRESH_SECRET_KEY=your_jwt_refresh_secret_key_here
ENCRYPTION_KEY=your_encryption_key_here
MASTER_ENCRYPTION_KEY=your_master_encryption_key_here

# API Configuration
CORS_ORIGINS=https://your-domain.com
REACT_APP_API_URL=https://your-domain.com/api

# Optional: API Keys (Users can add their own)
# GITHUB_TOKEN=ghp_your_github_token
# OPENAI_API_KEY=sk-your_openai_key
# ANTHROPIC_API_KEY=sk-ant-your_anthropic_key

# SSL Configuration (for custom domains)
SSL_ENABLED=true
FORCE_HTTPS=true
```

### Generating Secure Keys

```bash
# Generate secure random keys
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('JWT_REFRESH_SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('MASTER_ENCRYPTION_KEY=' + secrets.token_urlsafe(32))"
```

---

## Custom Domain Setup

### DNS Configuration

1. **Point Domain to Your Service**
   ```
   # For most platforms, add these DNS records:
   Type: A
   Name: @
   Value: [Your service IP]
   
   Type: CNAME
   Name: www
   Value: your-domain.com
   ```

2. **Platform-Specific Instructions**

   **Railway:**
   - Go to Railway dashboard
   - Click on your service → Settings → Domains
   - Add your custom domain

   **Render:**
   - Go to Render dashboard
   - Click on your service → Settings → Custom Domains
   - Add your domain and verify

   **DigitalOcean:**
   - SSL is automatically configured by our deployment script
   - Just point your domain to the server IP

### SSL Certificates

Most platforms provide automatic SSL certificates. For custom setups:

```bash
# Our deployment script handles SSL automatically
python scripts/complete-production-deployment.py --domain your-domain.com
```

---

## Monitoring and Maintenance

### Health Monitoring

After deployment, monitor your application:

```bash
# Check deployment status
python scripts/deployment-status-dashboard.py

# View real-time monitoring
# Visit: http://your-domain.com:5000 (if dashboard enabled)
```

### Performance Optimization

1. **Enable Caching**
   - Redis is included in all full-stack deployments
   - CDN caching for static assets

2. **Database Optimization**
   - Connection pooling enabled
   - Optimized queries
   - Regular maintenance

3. **Monitoring Alerts**
   - Response time monitoring
   - Error rate tracking
   - Resource usage alerts

### Backup Strategy

```bash
# Automated backups (included in deployment)
python scripts/complete-production-deployment.py --backup-only

# Manual backup
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres reverse_coach > backup.sql
```

---

## Troubleshooting

### Common Issues

**1. Build Failures**
```bash
# Check build logs
docker-compose -f docker-compose.prod.yml logs backend
docker-compose -f docker-compose.prod.yml logs frontend
```

**2. Database Connection Issues**
```bash
# Verify database connectivity
docker-compose -f docker-compose.prod.yml exec postgres pg_isready
```

**3. Environment Variable Issues**
```bash
# Verify environment variables are loaded
docker-compose -f docker-compose.prod.yml exec backend env | grep -E "(SECRET|JWT|POSTGRES)"
```

**4. SSL Certificate Issues**
```bash
# Check SSL certificate status
curl -I https://your-domain.com
```

### Getting Help

1. **Check Logs**
   - Platform-specific logging dashboards
   - Application logs via Docker commands

2. **Health Checks**
   ```bash
   # Test API endpoints
   curl https://your-domain.com/api/health
   curl https://your-domain.com/api/auth/health
   ```

3. **Performance Issues**
   ```bash
   # Run performance diagnostics
   python scripts/deployment-monitoring.py --action report
   ```

---

## Cost Optimization

### Free Tier Options

**Completely Free:**
- Vercel (frontend) + Railway PostgreSQL (free tier)
- Netlify (frontend) + Render (backend free tier)
- GitHub Pages (frontend) + Railway (backend)

**Low Cost ($5-10/month):**
- Railway full-stack: $5/month
- DigitalOcean Droplet: $6/month
- Render Pro: $7/month

### Scaling Considerations

**Traffic Growth:**
- Start with free/low-cost options
- Monitor usage and performance
- Upgrade when needed

**Feature Requirements:**
- Custom domains: Upgrade to paid plans
- High availability: Use enterprise platforms
- Global CDN: AWS/GCP for worldwide users

---

## Security Best Practices

### Production Security Checklist

- ✅ Use HTTPS everywhere
- ✅ Secure environment variables
- ✅ Regular security updates
- ✅ Database encryption
- ✅ API rate limiting
- ✅ Input validation
- ✅ CORS configuration
- ✅ Security headers

### API Key Management

```env
# Users should add their own API keys after deployment
# Never commit real API keys to version control

# GitHub Token (for repository analysis)
GITHUB_TOKEN=ghp_your_personal_access_token

# AI API Keys (for enhanced features)
OPENAI_API_KEY=sk-your_openai_api_key
ANTHROPIC_API_KEY=sk-ant-your_anthropic_api_key
```

### User Data Protection

- All user data encrypted at rest
- API credentials encrypted with user-specific keys
- No shared API keys between users
- GDPR compliance features included

---

## Next Steps

After successful deployment:

1. **Test Your Application**
   - Create a test account
   - Try the repository analysis feature
   - Test the learning workflow

2. **Configure API Keys**
   - Add your GitHub token for repository access
   - Add AI API keys for enhanced features

3. **Monitor Performance**
   - Use the built-in dashboard
   - Set up alerts for issues
   - Monitor user adoption

4. **Customize and Extend**
   - Add your branding
   - Customize the learning content
   - Integrate with your existing tools

---

## Support

### Documentation
- [Main README](README.md) - Project overview
- [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) - Advanced deployment
- [API Documentation](docs/api/README.md) - API reference

### Community
- GitHub Issues for bug reports
- GitHub Discussions for questions
- Documentation contributions welcome

### Professional Support
- Custom deployment assistance available
- Enterprise features and support
- Training and onboarding services

---

*This guide covers the most common deployment scenarios. For specific requirements or enterprise deployments, refer to the platform-specific documentation or contact support.*