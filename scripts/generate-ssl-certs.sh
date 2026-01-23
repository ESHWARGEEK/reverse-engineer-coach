#!/bin/bash

# Generate SSL Certificates for Development
# This script creates self-signed certificates for local development

set -e

# Configuration
SSL_DIR="./nginx/ssl"
DOMAIN_NAME="${DOMAIN_NAME:-localhost}"
COUNTRY="US"
STATE="CA"
CITY="San Francisco"
ORGANIZATION="Reverse Engineer Coach"
ORGANIZATIONAL_UNIT="Development"
EMAIL="dev@reverseengineercoach.com"

# Create SSL directory if it doesn't exist
mkdir -p "$SSL_DIR"

echo "Generating SSL certificates for domain: $DOMAIN_NAME"

# Generate private key
echo "Generating private key..."
openssl genrsa -out "$SSL_DIR/server.key" 2048

# Generate certificate signing request
echo "Generating certificate signing request..."
openssl req -new -key "$SSL_DIR/server.key" -out "$SSL_DIR/server.csr" -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORGANIZATION/OU=$ORGANIZATIONAL_UNIT/CN=$DOMAIN_NAME/emailAddress=$EMAIL"

# Generate self-signed certificate
echo "Generating self-signed certificate..."
openssl x509 -req -days 365 -in "$SSL_DIR/server.csr" -signkey "$SSL_DIR/server.key" -out "$SSL_DIR/server.crt" -extensions v3_req -extfile <(
cat <<EOF
[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = $DOMAIN_NAME
DNS.2 = www.$DOMAIN_NAME
DNS.3 = localhost
DNS.4 = 127.0.0.1
IP.1 = 127.0.0.1
IP.2 = ::1
EOF
)

# Generate CA certificate (for development)
echo "Generating CA certificate..."
openssl req -new -x509 -key "$SSL_DIR/server.key" -out "$SSL_DIR/ca.crt" -days 365 -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORGANIZATION/OU=Certificate Authority/CN=$DOMAIN_NAME CA/emailAddress=$EMAIL"

# Set appropriate permissions
chmod 600 "$SSL_DIR/server.key"
chmod 644 "$SSL_DIR/server.crt"
chmod 644 "$SSL_DIR/ca.crt"
chmod 644 "$SSL_DIR/server.csr"

echo "SSL certificates generated successfully!"
echo "Files created:"
echo "  - Private key: $SSL_DIR/server.key"
echo "  - Certificate: $SSL_DIR/server.crt"
echo "  - CA Certificate: $SSL_DIR/ca.crt"
echo "  - CSR: $SSL_DIR/server.csr"
echo ""
echo "For production, replace these self-signed certificates with certificates from a trusted CA."
echo "You can use Let's Encrypt with certbot for free SSL certificates."

# Clean up CSR file
rm "$SSL_DIR/server.csr"

echo "Certificate generation complete!"