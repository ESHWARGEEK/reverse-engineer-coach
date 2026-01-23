# Generate SSL Certificates for Development
# This script creates self-signed certificates for local development

param(
    [string]$DomainName = "localhost",
    [string]$SslDir = "./nginx/ssl"
)

# Configuration
$Country = "US"
$State = "CA"
$City = "San Francisco"
$Organization = "Reverse Engineer Coach"
$OrganizationalUnit = "Development"
$Email = "dev@reverseengineercoach.com"

# Create SSL directory if it doesn't exist
if (!(Test-Path $SslDir)) {
    New-Item -ItemType Directory -Path $SslDir -Force | Out-Null
}

Write-Host "Generating SSL certificates for domain: $DomainName" -ForegroundColor Green

try {
    # Check if OpenSSL is available
    $opensslPath = Get-Command openssl -ErrorAction SilentlyContinue
    if (-not $opensslPath) {
        Write-Host "OpenSSL not found. Attempting to use PowerShell certificate generation..." -ForegroundColor Yellow
        
        # Use PowerShell to create self-signed certificate
        $cert = New-SelfSignedCertificate -DnsName $DomainName, "www.$DomainName", "localhost", "127.0.0.1" -CertStoreLocation "cert:\LocalMachine\My" -KeyAlgorithm RSA -KeyLength 2048 -Provider "Microsoft RSA SChannel Cryptographic Provider" -KeyExportPolicy Exportable -KeyUsage DigitalSignature, KeyEncipherment -Type SSLServerAuthentication -ValidityPeriod Years -ValidityPeriodUnits 1
        
        # Export certificate and private key
        $certPath = Join-Path $SslDir "server.crt"
        $keyPath = Join-Path $SslDir "server.key"
        $pfxPath = Join-Path $SslDir "server.pfx"
        
        # Export as PFX first
        Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password (ConvertTo-SecureString -String "temp" -Force -AsPlainText) | Out-Null
        
        # Convert PFX to PEM format (requires OpenSSL or manual conversion)
        Write-Host "Certificate created in Windows certificate store." -ForegroundColor Green
        Write-Host "To use with nginx, you'll need to export the certificate manually or install OpenSSL." -ForegroundColor Yellow
        Write-Host "Certificate thumbprint: $($cert.Thumbprint)" -ForegroundColor Cyan
        
        # Clean up certificate from store
        Remove-Item -Path "cert:\LocalMachine\My\$($cert.Thumbprint)" -Force
        
    } else {
        Write-Host "Using OpenSSL to generate certificates..." -ForegroundColor Green
        
        # Generate private key
        Write-Host "Generating private key..."
        & openssl genrsa -out "$SslDir/server.key" 2048
        
        # Generate certificate signing request
        Write-Host "Generating certificate signing request..."
        $subject = "/C=$Country/ST=$State/L=$City/O=$Organization/OU=$OrganizationalUnit/CN=$DomainName/emailAddress=$Email"
        & openssl req -new -key "$SslDir/server.key" -out "$SslDir/server.csr" -subj $subject
        
        # Create config file for certificate extensions
        $configContent = @"
[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = $DomainName
DNS.2 = www.$DomainName
DNS.3 = localhost
DNS.4 = 127.0.0.1
IP.1 = 127.0.0.1
IP.2 = ::1
"@
        
        $configPath = Join-Path $SslDir "cert.conf"
        $configContent | Out-File -FilePath $configPath -Encoding ASCII
        
        # Generate self-signed certificate
        Write-Host "Generating self-signed certificate..."
        & openssl x509 -req -days 365 -in "$SslDir/server.csr" -signkey "$SslDir/server.key" -out "$SslDir/server.crt" -extensions v3_req -extfile $configPath
        
        # Generate CA certificate (for development)
        Write-Host "Generating CA certificate..."
        $caSubject = "/C=$Country/ST=$State/L=$City/O=$Organization/OU=Certificate Authority/CN=$DomainName CA/emailAddress=$Email"
        & openssl req -new -x509 -key "$SslDir/server.key" -out "$SslDir/ca.crt" -days 365 -subj $caSubject
        
        # Clean up temporary files
        Remove-Item "$SslDir/server.csr" -Force -ErrorAction SilentlyContinue
        Remove-Item $configPath -Force -ErrorAction SilentlyContinue
        
        Write-Host "SSL certificates generated successfully!" -ForegroundColor Green
        Write-Host "Files created:" -ForegroundColor Cyan
        Write-Host "  - Private key: $SslDir/server.key" -ForegroundColor White
        Write-Host "  - Certificate: $SslDir/server.crt" -ForegroundColor White
        Write-Host "  - CA Certificate: $SslDir/ca.crt" -ForegroundColor White
    }
    
    Write-Host ""
    Write-Host "For production, replace these self-signed certificates with certificates from a trusted CA." -ForegroundColor Yellow
    Write-Host "You can use Let's Encrypt with certbot for free SSL certificates." -ForegroundColor Yellow
    Write-Host "Certificate generation complete!" -ForegroundColor Green
    
} catch {
    Write-Host "Error generating SSL certificates: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "You may need to install OpenSSL or run this script as Administrator." -ForegroundColor Yellow
    exit 1
}