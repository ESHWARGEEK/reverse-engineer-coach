#!/bin/bash

# SSL setup script for production deployment
set -e

DOMAIN=${1:-"your-domain.com"}
EMAIL=${2:-"admin@your-domain.com"}

echo "🔒 Setting up SSL certificates for domain: $DOMAIN"

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    echo "📦 Installing certbot..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y certbot python3-certbot-nginx
    elif command -v yum &> /dev/null; then
        sudo yum install -y certbot python3-certbot-nginx
    else
        echo "❌ Please install certbot manually"
        exit 1
    fi
fi

# Create SSL directory
mkdir -p nginx/ssl

# Generate SSL certificate using Let's Encrypt
echo "🔐 Generating SSL certificate..."
sudo certbot certonly \
    --standalone \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN \
    -d www.$DOMAIN

# Copy certificates to nginx directory
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem nginx/ssl/key.pem

# Set proper permissions
sudo chown $(whoami):$(whoami) nginx/ssl/*.pem
chmod 644 nginx/ssl/cert.pem
chmod 600 nginx/ssl/key.pem

# Update nginx configuration for HTTPS
echo "⚙️ Updating nginx configuration..."
sed -i "s/your-domain.com/$DOMAIN/g" nginx/nginx.conf

# Enable HTTPS redirect in nginx config
sed -i 's/# return 301 https/return 301 https/' nginx/nginx.conf
sed -i 's/# Uncomment the following lines for production with SSL/# Production SSL configuration/' nginx/nginx.conf

# Setup certificate renewal
echo "🔄 Setting up automatic certificate renewal..."
(crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet --post-hook 'docker-compose -f docker-compose.prod.yml restart nginx'") | crontab -

echo "✅ SSL setup completed successfully!"
echo "🔒 Certificates installed for: $DOMAIN"
echo "🔄 Automatic renewal configured"
echo ""
echo "Next steps:"
echo "1. Update your DNS records to point to this server"
echo "2. Update .env.production with your domain"
echo "3. Restart the application: ./scripts/deploy.sh production"