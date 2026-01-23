# PowerShell deployment script for Reverse Engineer Coach
param(
    [string]$Environment = "production"
)

$ErrorActionPreference = "Stop"

# Configuration
$ComposeFile = "docker-compose.prod.yml"
$EnvFile = ".env.$Environment"

Write-Host "🚀 Deploying Reverse Engineer Coach to $Environment environment..." -ForegroundColor Green

# Check if environment file exists
if (-not (Test-Path $EnvFile)) {
    Write-Host "❌ Environment file $EnvFile not found!" -ForegroundColor Red
    Write-Host "Please create the environment file with required variables."
    exit 1
}

# Load environment variables
Get-Content $EnvFile | Where-Object { $_ -notmatch '^#' -and $_ -match '=' } | ForEach-Object {
    $name, $value = $_ -split '=', 2
    [Environment]::SetEnvironmentVariable($name, $value, "Process")
}

# Validate required environment variables
$requiredVars = @("POSTGRES_PASSWORD", "SECRET_KEY", "GITHUB_TOKEN")

foreach ($var in $requiredVars) {
    if (-not [Environment]::GetEnvironmentVariable($var)) {
        Write-Host "❌ Required environment variable $var is not set!" -ForegroundColor Red
        exit 1
    }
}

# Create necessary directories
New-Item -ItemType Directory -Force -Path "nginx/ssl" | Out-Null
New-Item -ItemType Directory -Force -Path "logs" | Out-Null

# Pull latest images
Write-Host "📦 Pulling latest Docker images..." -ForegroundColor Yellow
docker-compose -f $ComposeFile pull

# Stop existing containers
Write-Host "🛑 Stopping existing containers..." -ForegroundColor Yellow
docker-compose -f $ComposeFile down

# Start services
Write-Host "🔄 Starting services..." -ForegroundColor Yellow
docker-compose -f $ComposeFile up -d

# Wait for services to be healthy
Write-Host "⏳ Waiting for services to be healthy..." -ForegroundColor Yellow
$timeout = 300
$elapsed = 0

while ($elapsed -lt $timeout) {
    $status = docker-compose -f $ComposeFile ps
    if ($status -match "unhealthy|starting") {
        Write-Host "Waiting for services to start... ($elapsed s)"
        Start-Sleep 10
        $elapsed += 10
    } else {
        break
    }
}

# Check if all services are running
$status = docker-compose -f $ComposeFile ps
if ($status -match "Exit|unhealthy") {
    Write-Host "❌ Some services failed to start properly!" -ForegroundColor Red
    docker-compose -f $ComposeFile logs --tail=50
    exit 1
}

# Run database migrations
Write-Host "🗄️ Running database migrations..." -ForegroundColor Yellow
docker-compose -f $ComposeFile exec -T backend alembic upgrade head

# Health check
Write-Host "🏥 Performing health check..." -ForegroundColor Yellow
Start-Sleep 10

try {
    $response = Invoke-WebRequest -Uri "http://localhost/health" -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Deployment successful! Application is healthy." -ForegroundColor Green
    } else {
        throw "Health check returned status code: $($response.StatusCode)"
    }
} catch {
    Write-Host "❌ Health check failed!" -ForegroundColor Red
    docker-compose -f $ComposeFile logs --tail=50
    exit 1
}

Write-Host "🎉 Deployment completed successfully!" -ForegroundColor Green
Write-Host "📊 Access the application at: http://localhost"
Write-Host "📈 Monitor logs with: docker-compose -f $ComposeFile logs -f"