# Deployment Guide

This guide covers the deployment configuration and procedures for the Reverse Engineer Coach platform.

## Overview

The platform supports multiple deployment strategies:
- **Docker Compose** (recommended for single-server deployments)
- **Kubernetes** (recommended for scalable, production deployments)
- **Development** (local development with hot reload)

## Prerequisites

### System Requirements
- **CPU**: 2+ cores (4+ recommended for production)
- **RAM**: 4GB minimum (8GB+ recommended for production)
- **Storage**: 20GB minimum (SSD recommended)
- **Network**: Stable internet connection for API integrations

### Software Dependencies
- Docker 20.10+
- Docker Compose 2.0+
- Git
- (Optional) Kubernetes 1.20+ for K8s deployments

## Environment Configuration

### 1. Environment Files

Create environment-specific configuration files:

```bash
# Production
cp .env.example .env.production

# Staging
cp .env.example .env.staging
```

### 2. Required Environment Variables

**Database Configuration:**
```env
POSTGRES_DB=reverse_coach
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_here
```

**Application Security:**
```env
SECRET_KEY=your_secret_key_minimum_32_characters
ENVIRONMENT=production
LOG_LEVEL=INFO
```

**API Keys:**
```env
GITHUB_TOKEN=your_github_token_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

**CORS and Frontend:**
```env
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
REACT_APP_API_URL=https://your-domain.com/api
```

## Deployment Methods

### Method 1: Docker Compose (Recommended)

#### Quick Start
```bash
# 1. Clone repository
git clone <repository-url>
cd reverse-engineer-coach

# 2. Configure environment
cp .env.example .env.production
# Edit .env.production with your values

# 3. Deploy
./scripts/deploy.sh production
# Or on Windows:
# .\scripts\deploy.ps1 production
```

#### Manual Steps
```bash
# 1. Pull latest images
docker-compose -f docker-compose.prod.yml pull

# 2. Start services
docker-compose -f docker-compose.prod.yml up -d

# 3. Run migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 4. Verify deployment
curl http://localhost/health
```

### Method 2: Kubernetes

#### Prerequisites
```bash
# Install kubectl and configure cluster access
kubectl cluster-info

# Create namespace
kubectl apply -f k8s/namespace.yml
```

#### Deploy to Kubernetes
```bash
# 1. Configure secrets (base64 encode your values)
kubectl apply -f k8s/secrets.yml

# 2. Deploy infrastructure
kubectl apply -f k8s/configmap.yml
kubectl apply -f k8s/postgres.yml
kubectl apply -f k8s/redis.yml

# 3. Deploy application
kubectl apply -f k8s/backend.yml
kubectl apply -f k8s/frontend.yml

# 4. Configure ingress
kubectl apply -f k8s/ingress.yml

# 5. Verify deployment
kubectl get pods -n reverse-coach
kubectl get services -n reverse-coach
```

## SSL/TLS Configuration

### Automatic SSL with Let's Encrypt
```bash
# Run SSL setup script
./scripts/setup-ssl.sh your-domain.com admin@your-domain.com

# Update environment variables
# Edit .env.production to include your domain
```

### Manual SSL Configuration
1. Obtain SSL certificates from your provider
2. Place certificates in `nginx/ssl/`:
   - `cert.pem` (certificate chain)
   - `key.pem` (private key)
3. Update `nginx/nginx.conf` with your domain
4. Restart nginx service

## Monitoring and Logging

### Enable Monitoring Stack
```bash
# Start monitoring services
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# Access dashboards
# Grafana: http://localhost:3001 (admin/admin)
# Prometheus: http://localhost:9090
# Alertmanager: http://localhost:9093
```

### Log Management
```bash
# View application logs
docker-compose -f docker-compose.prod.yml logs -f

# View specific service logs
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f frontend

# Export logs for analysis
docker-compose -f docker-compose.prod.yml logs --since 24h > logs/app-$(date +%Y%m%d).log
```

## Backup and Recovery

### Automated Backups
```bash
# Run backup script
./scripts/backup.sh

# Schedule daily backups (crontab)
0 2 * * * /path/to/scripts/backup.sh
```

### Manual Backup
```bash
# Database backup
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres reverse_coach > backup.sql

# Redis backup
docker-compose -f docker-compose.prod.yml exec redis redis-cli BGSAVE
```

### Restore from Backup
```bash
# Restore using script
./scripts/restore.sh 20240121_020000

# Manual restore
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d reverse_coach < backup.sql
```

## Scaling and Performance

### Horizontal Scaling (Kubernetes)
```bash
# Scale backend pods
kubectl scale deployment backend --replicas=5 -n reverse-coach

# Enable auto-scaling
kubectl apply -f k8s/backend.yml  # Includes HPA configuration
```

### Vertical Scaling (Docker Compose)
```yaml
# Update docker-compose.prod.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

### Performance Optimization
1. **Database**: Configure connection pooling, enable query optimization
2. **Redis**: Adjust memory limits and eviction policies
3. **Nginx**: Enable gzip compression, configure caching headers
4. **Application**: Monitor response times, optimize API endpoints

## Security Considerations

### Network Security
- Use HTTPS in production (SSL/TLS)
- Configure firewall rules
- Implement rate limiting
- Use secure headers

### Application Security
- Rotate API keys regularly
- Use strong passwords and secrets
- Enable audit logging
- Regular security updates

### Container Security
- Use non-root users in containers
- Scan images for vulnerabilities
- Keep base images updated
- Implement resource limits

## Troubleshooting

### Common Issues

**Services won't start:**
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs

# Check system resources
docker system df
docker system prune  # Clean up if needed
```

**Database connection issues:**
```bash
# Check PostgreSQL status
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U postgres

# Reset database
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d
```

**SSL certificate issues:**
```bash
# Check certificate validity
openssl x509 -in nginx/ssl/cert.pem -text -noout

# Renew Let's Encrypt certificate
certbot renew --dry-run
```

### Health Checks
```bash
# Application health
curl http://localhost/health

# Service-specific health
curl http://localhost/api/v1/health/database
curl http://localhost/api/v1/health/cache
```

## CI/CD Pipeline

The platform includes GitHub Actions workflows for automated testing and deployment:

- **Testing**: Runs on every push and pull request
- **Building**: Creates Docker images for main/develop branches
- **Deployment**: Automatic deployment to staging/production

### Setup CI/CD
1. Configure GitHub repository secrets:
   - `DOCKER_REGISTRY_TOKEN`
   - `PRODUCTION_SERVER_SSH_KEY`
   - `STAGING_SERVER_SSH_KEY`

2. Update deployment targets in `.github/workflows/ci-cd.yml`

3. Configure deployment environments in GitHub repository settings

## Maintenance

### Regular Tasks
- **Daily**: Monitor application health and performance
- **Weekly**: Review logs and error rates
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Review and rotate API keys and secrets

### Update Procedures
```bash
# 1. Backup current deployment
./scripts/backup.sh

# 2. Pull latest code
git pull origin main

# 3. Update images
docker-compose -f docker-compose.prod.yml pull

# 4. Deploy updates
./scripts/deploy.sh production

# 5. Verify deployment
curl http://localhost/health
```

## Support and Monitoring

### Monitoring Endpoints
- **Application Health**: `/health`
- **Metrics**: `/metrics` (Prometheus format)
- **API Documentation**: `/docs`

### Alert Configuration
Configure alerts for:
- High error rates (>5%)
- High response times (>2s)
- Service downtime
- Resource utilization (>80%)
- Failed backups

### Log Analysis
- Use structured logging (JSON format)
- Implement log aggregation (ELK stack)
- Set up log retention policies
- Monitor error patterns and trends