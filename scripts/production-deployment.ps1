# Production Deployment Orchestration Script
# Comprehensive deployment with monitoring, validation, and rollback capabilities

param(
    [string]$Environment = "production",
    [string]$Version = "latest",
    [string]$Domain = "",
    [switch]$SkipBackup = $false,
    [switch]$SkipValidation = $false,
    [switch]$DryRun = $false,
    [switch]$Rollback = $false,
    [string]$RollbackVersion = ""
)

$ErrorActionPreference = "Stop"

# Configuration
$DeploymentConfig = @{
    ComposeFile = "docker-compose.prod.yml"
    EnvFile = ".env.$Environment"
    BackupDir = "backups"
    LogDir = "logs/deployment"
    HealthCheckTimeout = 300
    ValidationTimeout = 180
    MonitoringDuration = 600  # 10 minutes post-deployment monitoring
}

# Logging setup
$LogFile = "$($DeploymentConfig.LogDir)/deployment-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
New-Item -ItemType Directory -Force -Path $DeploymentConfig.LogDir | Out-Null

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    Write-Host $logEntry
    Add-Content -Path $LogFile -Value $logEntry
}

function Write-Info { param([string]$Message) Write-Log $Message "INFO" }
function Write-Warn { param([string]$Message) Write-Log $Message "WARN" }
function Write-Error { param([string]$Message) Write-Log $Message "ERROR" }
function Write-Success { param([string]$Message) Write-Log $Message "SUCCESS" }

function Test-Prerequisites {
    Write-Info "Checking deployment prerequisites..."
    
    # Check Docker
    try {
        $dockerVersion = docker --version
        Write-Info "✓ Docker available: $dockerVersion"
    }
    catch {
        Write-Error "✗ Docker is not available or not running"
        return $false
    }
    
    # Check Docker Compose
    try {
        $composeVersion = docker-compose --version
        Write-Info "✓ Docker Compose available: $composeVersion"
    }
    catch {
        Write-Error "✗ Docker Compose is not available"
        return $false
    }
    
    # Check environment file
    if (-not (Test-Path $DeploymentConfig.EnvFile)) {
        Write-Error "✗ Environment file not found: $($DeploymentConfig.EnvFile)"
        return $false
    }
    Write-Info "✓ Environment file found: $($DeploymentConfig.EnvFile)"
    
    # Check required environment variables
    $envContent = Get-Content $DeploymentConfig.EnvFile | Where-Object { $_ -notmatch '^#' -and $_ -match '=' }
    $envVars = @{}
    foreach ($line in $envContent) {
        $name, $value = $line -split '=', 2
        $envVars[$name] = $value
    }
    
    $requiredVars = @(
        "POSTGRES_PASSWORD", "SECRET_KEY", "JWT_SECRET_KEY", 
        "ENCRYPTION_KEY", "MASTER_ENCRYPTION_KEY"
    )
    
    foreach ($var in $requiredVars) {
        if (-not $envVars.ContainsKey($var) -or [string]::IsNullOrEmpty($envVars[$var])) {
            Write-Error "✗ Required environment variable missing or empty: $var"
            return $false
        }
    }
    Write-Info "✓ All required environment variables are set"
    
    return $true
}

function Backup-CurrentDeployment {
    if ($SkipBackup) {
        Write-Warn "Skipping backup as requested"
        return $true
    }
    
    Write-Info "Creating deployment backup..."
    
    $backupTimestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupPath = "$($DeploymentConfig.BackupDir)/$backupTimestamp"
    
    New-Item -ItemType Directory -Force -Path $backupPath | Out-Null
    
    try {
        # Backup database
        Write-Info "Backing up database..."
        docker-compose -f $DeploymentConfig.ComposeFile exec -T postgres pg_dump -U postgres reverse_coach > "$backupPath/database.sql"
        
        # Backup Redis data
        Write-Info "Backing up Redis data..."
        docker-compose -f $DeploymentConfig.ComposeFile exec -T redis redis-cli BGSAVE
        Start-Sleep -Seconds 5
        docker cp "$(docker-compose -f $DeploymentConfig.ComposeFile ps -q redis):/data/dump.rdb" "$backupPath/redis-dump.rdb"
        
        # Backup configuration files
        Write-Info "Backing up configuration..."
        Copy-Item $DeploymentConfig.EnvFile "$backupPath/"
        Copy-Item $DeploymentConfig.ComposeFile "$backupPath/"
        
        # Create backup manifest
        $manifest = @{
            timestamp = $backupTimestamp
            environment = $Environment
            version = $Version
            files = @(
                "database.sql",
                "redis-dump.rdb",
                (Split-Path $DeploymentConfig.EnvFile -Leaf),
                (Split-Path $DeploymentConfig.ComposeFile -Leaf)
            )
        }
        $manifest | ConvertTo-Json | Out-File "$backupPath/manifest.json"
        
        Write-Success "✓ Backup completed: $backupPath"
        return $true
    }
    catch {
        Write-Error "✗ Backup failed: $($_.Exception.Message)"
        return $false
    }
}

function Deploy-Application {
    Write-Info "Starting application deployment..."
    
    if ($DryRun) {
        Write-Info "[DRY RUN] Would deploy version $Version to $Environment"
        return $true
    }
    
    try {
        # Load environment variables
        Get-Content $DeploymentConfig.EnvFile | Where-Object { $_ -notmatch '^#' -and $_ -match '=' } | ForEach-Object {
            $name, $value = $_ -split '=', 2
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
        
        # Pull latest images
        Write-Info "Pulling Docker images..."
        docker-compose -f $DeploymentConfig.ComposeFile pull
        
        # Stop existing containers gracefully
        Write-Info "Stopping existing containers..."
        docker-compose -f $DeploymentConfig.ComposeFile down --timeout 30
        
        # Start new containers
        Write-Info "Starting new containers..."
        docker-compose -f $DeploymentConfig.ComposeFile up -d
        
        # Wait for services to be healthy
        Write-Info "Waiting for services to become healthy..."
        $timeout = $DeploymentConfig.HealthCheckTimeout
        $elapsed = 0
        
        while ($elapsed -lt $timeout) {
            $unhealthyServices = docker-compose -f $DeploymentConfig.ComposeFile ps --filter "health=unhealthy" -q
            $startingServices = docker-compose -f $DeploymentConfig.ComposeFile ps --filter "health=starting" -q
            
            if (-not $unhealthyServices -and -not $startingServices) {
                Write-Success "✓ All services are healthy"
                break
            }
            
            Write-Info "Waiting for services to start... ($elapsed/$timeout seconds)"
            Start-Sleep -Seconds 10
            $elapsed += 10
        }
        
        if ($elapsed -ge $timeout) {
            Write-Error "✗ Services failed to become healthy within timeout"
            return $false
        }
        
        # Run database migrations
        Write-Info "Running database migrations..."
        docker-compose -f $DeploymentConfig.ComposeFile exec -T backend alembic upgrade head
        
        Write-Success "✓ Application deployment completed"
        return $true
    }
    catch {
        Write-Error "✗ Deployment failed: $($_.Exception.Message)"
        return $false
    }
}

function Test-DeploymentHealth {
    Write-Info "Performing deployment health checks..."
    
    if ($SkipValidation) {
        Write-Warn "Skipping validation as requested"
        return $true
    }
    
    try {
        # Basic health check
        $baseUrl = if ($Domain) { "https://$Domain" } else { "http://localhost" }
        
        Write-Info "Testing basic connectivity..."
        $response = Invoke-RestMethod -Uri "$baseUrl/health" -TimeoutSec 30 -ErrorAction Stop
        
        if ($response.status -eq "healthy") {
            Write-Success "✓ Basic health check passed"
        }
        else {
            Write-Error "✗ Basic health check failed: $($response.status)"
            return $false
        }
        
        # Run comprehensive health checks
        Write-Info "Running comprehensive health checks..."
        $healthCheckScript = if ($Domain) {
            ".\scripts\health-checks.ps1 -ApiBaseUrl https://$Domain -FrontendUrl https://$Domain"
        } else {
            ".\scripts\health-checks.ps1 -ApiBaseUrl http://localhost:8000 -FrontendUrl http://localhost"
        }
        
        $healthResult = Invoke-Expression $healthCheckScript
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✓ Comprehensive health checks passed"
        }
        else {
            Write-Error "✗ Some health checks failed"
            return $false
        }
        
        return $true
    }
    catch {
        Write-Error "✗ Health check failed: $($_.Exception.Message)"
        return $false
    }
}

function Start-PostDeploymentMonitoring {
    Write-Info "Starting post-deployment monitoring..."
    
    $monitoringEndTime = (Get-Date).AddSeconds($DeploymentConfig.MonitoringDuration)
    $baseUrl = if ($Domain) { "https://$Domain" } else { "http://localhost" }
    
    $metrics = @{
        SuccessfulRequests = 0
        FailedRequests = 0
        TotalResponseTime = 0
        MaxResponseTime = 0
        MinResponseTime = [int]::MaxValue
    }
    
    Write-Info "Monitoring for $($DeploymentConfig.MonitoringDuration) seconds..."
    
    while ((Get-Date) -lt $monitoringEndTime) {
        try {
            $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
            $response = Invoke-RestMethod -Uri "$baseUrl/health" -TimeoutSec 10 -ErrorAction Stop
            $stopwatch.Stop()
            
            $responseTime = $stopwatch.ElapsedMilliseconds
            
            $metrics.SuccessfulRequests++
            $metrics.TotalResponseTime += $responseTime
            $metrics.MaxResponseTime = [Math]::Max($metrics.MaxResponseTime, $responseTime)
            $metrics.MinResponseTime = [Math]::Min($metrics.MinResponseTime, $responseTime)
            
            if ($response.status -ne "healthy") {
                Write-Warn "Health check returned non-healthy status: $($response.status)"
            }
        }
        catch {
            $metrics.FailedRequests++
            Write-Warn "Health check failed: $($_.Exception.Message)"
        }
        
        Start-Sleep -Seconds 30
    }
    
    # Calculate and report metrics
    $totalRequests = $metrics.SuccessfulRequests + $metrics.FailedRequests
    $successRate = if ($totalRequests -gt 0) { ($metrics.SuccessfulRequests / $totalRequests) * 100 } else { 0 }
    $avgResponseTime = if ($metrics.SuccessfulRequests -gt 0) { $metrics.TotalResponseTime / $metrics.SuccessfulRequests } else { 0 }
    
    Write-Info "=== Post-Deployment Monitoring Results ==="
    Write-Info "Total requests: $totalRequests"
    Write-Info "Successful requests: $($metrics.SuccessfulRequests)"
    Write-Info "Failed requests: $($metrics.FailedRequests)"
    Write-Info "Success rate: $([Math]::Round($successRate, 2))%"
    Write-Info "Average response time: $([Math]::Round($avgResponseTime, 2))ms"
    Write-Info "Min response time: $($metrics.MinResponseTime)ms"
    Write-Info "Max response time: $($metrics.MaxResponseTime)ms"
    
    # Determine if monitoring results are acceptable
    if ($successRate -ge 95 -and $avgResponseTime -lt 2000) {
        Write-Success "✓ Post-deployment monitoring shows healthy system"
        return $true
    }
    elseif ($successRate -ge 90) {
        Write-Warn "⚠ Post-deployment monitoring shows acceptable but not optimal performance"
        return $true
    }
    else {
        Write-Error "✗ Post-deployment monitoring shows poor system health"
        return $false
    }
}

function Invoke-Rollback {
    if (-not $Rollback) {
        return
    }
    
    Write-Warn "Initiating rollback procedure..."
    
    if ([string]::IsNullOrEmpty($RollbackVersion)) {
        # Find the most recent backup
        $backups = Get-ChildItem -Path $DeploymentConfig.BackupDir -Directory | Sort-Object Name -Descending
        if ($backups.Count -eq 0) {
            Write-Error "✗ No backups available for rollback"
            return $false
        }
        $RollbackVersion = $backups[0].Name
    }
    
    $rollbackPath = "$($DeploymentConfig.BackupDir)/$RollbackVersion"
    
    if (-not (Test-Path $rollbackPath)) {
        Write-Error "✗ Rollback version not found: $rollbackPath"
        return $false
    }
    
    Write-Info "Rolling back to version: $RollbackVersion"
    
    try {
        # Stop current services
        docker-compose -f $DeploymentConfig.ComposeFile down
        
        # Restore database
        Write-Info "Restoring database..."
        docker-compose -f $DeploymentConfig.ComposeFile up -d postgres
        Start-Sleep -Seconds 10
        Get-Content "$rollbackPath/database.sql" | docker-compose -f $DeploymentConfig.ComposeFile exec -T postgres psql -U postgres -d reverse_coach
        
        # Restore Redis
        Write-Info "Restoring Redis data..."
        docker-compose -f $DeploymentConfig.ComposeFile up -d redis
        Start-Sleep -Seconds 5
        docker cp "$rollbackPath/redis-dump.rdb" "$(docker-compose -f $DeploymentConfig.ComposeFile ps -q redis):/data/dump.rdb"
        docker-compose -f $DeploymentConfig.ComposeFile restart redis
        
        # Start all services
        Write-Info "Starting all services..."
        docker-compose -f $DeploymentConfig.ComposeFile up -d
        
        Write-Success "✓ Rollback completed successfully"
        return $true
    }
    catch {
        Write-Error "✗ Rollback failed: $($_.Exception.Message)"
        return $false
    }
}

function Send-DeploymentNotification {
    param(
        [bool]$Success,
        [string]$Message
    )
    
    # This function can be extended to send notifications via email, Slack, etc.
    $status = if ($Success) { "SUCCESS" } else { "FAILED" }
    $emoji = if ($Success) { "🎉" } else { "❌" }
    
    Write-Log "$emoji Deployment $status: $Message" "NOTIFICATION"
    
    # Example: Send to webhook (uncomment and configure as needed)
    # $webhook = $env:DEPLOYMENT_WEBHOOK_URL
    # if ($webhook) {
    #     $payload = @{
    #         text = "$emoji Production Deployment $status"
    #         attachments = @(@{
    #             color = if ($Success) { "good" } else { "danger" }
    #             fields = @(@{
    #                 title = "Environment"
    #                 value = $Environment
    #                 short = $true
    #             }, @{
    #                 title = "Version"
    #                 value = $Version
    #                 short = $true
    #             }, @{
    #                 title = "Message"
    #                 value = $Message
    #                 short = $false
    #             })
    #         })
    #     }
    #     Invoke-RestMethod -Uri $webhook -Method Post -Body ($payload | ConvertTo-Json -Depth 3) -ContentType "application/json"
    # }
}

# Main execution
function Main {
    Write-Info "=== Production Deployment Started ==="
    Write-Info "Environment: $Environment"
    Write-Info "Version: $Version"
    Write-Info "Domain: $(if ($Domain) { $Domain } else { 'localhost' })"
    Write-Info "Dry Run: $DryRun"
    Write-Info "Skip Backup: $SkipBackup"
    Write-Info "Skip Validation: $SkipValidation"
    Write-Info "Rollback: $Rollback"
    Write-Info "Log File: $LogFile"
    Write-Host ""
    
    $deploymentSuccess = $false
    
    try {
        # Handle rollback request
        if ($Rollback) {
            $rollbackSuccess = Invoke-Rollback
            Send-DeploymentNotification $rollbackSuccess "Rollback to version $RollbackVersion"
            exit $(if ($rollbackSuccess) { 0 } else { 1 })
        }
        
        # Pre-deployment checks
        if (-not (Test-Prerequisites)) {
            throw "Prerequisites check failed"
        }
        
        # Create backup
        if (-not (Backup-CurrentDeployment)) {
            throw "Backup creation failed"
        }
        
        # Deploy application
        if (-not (Deploy-Application)) {
            throw "Application deployment failed"
        }
        
        # Validate deployment
        if (-not (Test-DeploymentHealth)) {
            throw "Deployment health validation failed"
        }
        
        # Start monitoring
        if (-not (Start-PostDeploymentMonitoring)) {
            Write-Warn "Post-deployment monitoring detected issues, but deployment will continue"
        }
        
        $deploymentSuccess = $true
        Write-Success "🎉 Production deployment completed successfully!"
        Send-DeploymentNotification $true "Deployment completed successfully"
        
    }
    catch {
        Write-Error "❌ Deployment failed: $($_.Exception.Message)"
        Send-DeploymentNotification $false $_.Exception.Message
        
        # Offer automatic rollback on failure
        if (-not $DryRun) {
            Write-Warn "Would you like to automatically rollback? (This would need to be implemented as user input)"
            # In a real scenario, you might want to implement automatic rollback logic here
        }
    }
    
    Write-Info "=== Deployment Log Available: $LogFile ==="
    exit $(if ($deploymentSuccess) { 0 } else { 1 })
}

# Execute main function
Main