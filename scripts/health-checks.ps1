# Health Check Scripts for Production Deployment
# This script performs comprehensive health checks after deployment

param(
    [string]$ApiBaseUrl = "https://api.your-domain.com",
    [string]$FrontendUrl = "https://your-domain.com",
    [int]$Timeout = 30,
    [int]$MaxRetries = 5
)

# Logging functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Health check functions
function Test-ApiHealth {
    Write-Info "Checking API health..."
    
    for ($i = 1; $i -le $MaxRetries; $i++) {
        try {
            $response = Invoke-RestMethod -Uri "$ApiBaseUrl/api/monitoring/health" -TimeoutSec $Timeout -ErrorAction Stop
            Write-Info "✓ API health check passed"
            return $true
        }
        catch {
            Write-Warn "API health check failed (attempt $i/$MaxRetries)"
            if ($i -lt $MaxRetries) {
                Start-Sleep -Seconds 5
            }
        }
    }
    
    Write-Error "✗ API health check failed after $MaxRetries attempts"
    return $false
}

function Test-ApiDetailedHealth {
    Write-Info "Checking detailed API health..."
    
    try {
        $response = Invoke-RestMethod -Uri "$ApiBaseUrl/api/monitoring/health/detailed" -TimeoutSec $Timeout -ErrorAction Stop
        
        if ($response.status -eq "healthy") {
            Write-Info "✓ Detailed API health check passed"
            
            # Check individual components
            if ($response.checks.database.status -eq "healthy") {
                Write-Info "  ✓ Database connection healthy"
            }
            else {
                Write-Error "  ✗ Database connection unhealthy: $($response.checks.database.status)"
                return $false
            }
            
            if ($response.checks.redis.status -eq "healthy") {
                Write-Info "  ✓ Redis connection healthy"
            }
            else {
                Write-Warn "  ⚠ Redis connection status: $($response.checks.redis.status)"
            }
            
            return $true
        }
        else {
            Write-Error "✗ Detailed API health check failed: $($response.status)"
            return $false
        }
    }
    catch {
        Write-Error "✗ Detailed API health check failed: $($_.Exception.Message)"
        return $false
    }
}

function Test-FrontendHealth {
    Write-Info "Checking frontend health..."
    
    for ($i = 1; $i -le $MaxRetries; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $FrontendUrl -TimeoutSec $Timeout -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Info "✓ Frontend health check passed"
                return $true
            }
        }
        catch {
            Write-Warn "Frontend health check failed (attempt $i/$MaxRetries)"
            if ($i -lt $MaxRetries) {
                Start-Sleep -Seconds 5
            }
        }
    }
    
    Write-Error "✗ Frontend health check failed after $MaxRetries attempts"
    return $false
}

function Test-AuthenticationEndpoints {
    Write-Info "Checking authentication endpoints..."
    
    try {
        # Test registration endpoint (should return validation error for empty request)
        try {
            $regResponse = Invoke-RestMethod -Uri "$ApiBaseUrl/api/auth/register" -Method Post -Body "{}" -ContentType "application/json" -TimeoutSec $Timeout -ErrorAction Stop
        }
        catch {
            if ($_.Exception.Response.StatusCode -eq 422 -or $_.Exception.Response.StatusCode -eq 400) {
                Write-Info "✓ Registration endpoint responding correctly"
            }
            else {
                Write-Error "✗ Registration endpoint unexpected response: $($_.Exception.Response.StatusCode)"
                return $false
            }
        }
        
        # Test login endpoint (should return validation error for empty request)
        try {
            $loginResponse = Invoke-RestMethod -Uri "$ApiBaseUrl/api/auth/login" -Method Post -Body "{}" -ContentType "application/json" -TimeoutSec $Timeout -ErrorAction Stop
        }
        catch {
            if ($_.Exception.Response.StatusCode -eq 422 -or $_.Exception.Response.StatusCode -eq 400) {
                Write-Info "✓ Login endpoint responding correctly"
                return $true
            }
            else {
                Write-Error "✗ Login endpoint unexpected response: $($_.Exception.Response.StatusCode)"
                return $false
            }
        }
    }
    catch {
        Write-Error "✗ Authentication endpoints check failed: $($_.Exception.Message)"
        return $false
    }
}

function Test-DiscoveryEndpoints {
    Write-Info "Checking discovery endpoints..."
    
    try {
        $response = Invoke-RestMethod -Uri "$ApiBaseUrl/api/discover/repositories?concept=microservices" -TimeoutSec $Timeout -ErrorAction Stop
        Write-Warn "⚠ Discovery endpoint not properly protected (expected 401/403)"
    }
    catch {
        if ($_.Exception.Response.StatusCode -eq 401 -or $_.Exception.Response.StatusCode -eq 403) {
            Write-Info "✓ Discovery endpoint properly protected"
            return $true
        }
        else {
            Write-Warn "⚠ Discovery endpoint response: $($_.Exception.Response.StatusCode) (expected 401/403)"
        }
    }
    
    return $true
}

function Test-RateLimiting {
    Write-Info "Checking rate limiting..."
    
    $successCount = 0
    $rateLimitedCount = 0
    
    # Make multiple rapid requests to test rate limiting
    for ($i = 1; $i -le 10; $i++) {
        try {
            $response = Invoke-RestMethod -Uri "$ApiBaseUrl/api/monitoring/health" -TimeoutSec 5 -ErrorAction Stop
            $successCount++
        }
        catch {
            if ($_.Exception.Response.StatusCode -eq 429) {
                $rateLimitedCount++
            }
        }
        Start-Sleep -Milliseconds 100
    }
    
    if ($successCount -gt 0) {
        Write-Info "✓ Rate limiting configured (successful requests: $successCount, rate limited: $rateLimitedCount)"
        return $true
    }
    else {
        Write-Error "✗ No successful requests - possible rate limiting issue"
        return $false
    }
}

function Test-SslCertificate {
    Write-Info "Checking SSL certificate..."
    
    try {
        $uri = [System.Uri]$ApiBaseUrl
        $domain = $uri.Host
        
        # Create a TCP client to test SSL
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $tcpClient.Connect($domain, 443)
        
        $sslStream = New-Object System.Net.Security.SslStream($tcpClient.GetStream())
        $sslStream.AuthenticateAsClient($domain)
        
        $cert = $sslStream.RemoteCertificate
        $cert2 = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($cert)
        
        if ($cert2.NotAfter -gt (Get-Date)) {
            Write-Info "✓ SSL certificate is valid (expires: $($cert2.NotAfter))"
            $result = $true
        }
        else {
            Write-Error "✗ SSL certificate has expired: $($cert2.NotAfter)"
            $result = $false
        }
        
        $sslStream.Close()
        $tcpClient.Close()
        
        return $result
    }
    catch {
        Write-Error "✗ SSL certificate check failed: $($_.Exception.Message)"
        return $false
    }
}

function Test-SecurityHeaders {
    Write-Info "Checking security headers..."
    
    try {
        $response = Invoke-WebRequest -Uri $FrontendUrl -TimeoutSec $Timeout -ErrorAction Stop
        
        # Check for important security headers
        if ($response.Headers["Strict-Transport-Security"]) {
            Write-Info "✓ HSTS header present"
        }
        else {
            Write-Warn "⚠ HSTS header missing"
        }
        
        if ($response.Headers["X-Frame-Options"]) {
            Write-Info "✓ X-Frame-Options header present"
        }
        else {
            Write-Warn "⚠ X-Frame-Options header missing"
        }
        
        if ($response.Headers["X-Content-Type-Options"]) {
            Write-Info "✓ X-Content-Type-Options header present"
        }
        else {
            Write-Warn "⚠ X-Content-Type-Options header missing"
        }
        
        return $true
    }
    catch {
        Write-Error "✗ Security headers check failed: $($_.Exception.Message)"
        return $false
    }
}

function Test-Performance {
    Write-Info "Running basic performance test..."
    
    try {
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        $response = Invoke-RestMethod -Uri "$ApiBaseUrl/api/monitoring/health" -TimeoutSec $Timeout -ErrorAction Stop
        $stopwatch.Stop()
        
        $duration = $stopwatch.ElapsedMilliseconds
        
        if ($duration -lt 1000) {
            Write-Info "✓ API response time: ${duration}ms (excellent)"
        }
        elseif ($duration -lt 2000) {
            Write-Info "✓ API response time: ${duration}ms (good)"
        }
        elseif ($duration -lt 5000) {
            Write-Warn "⚠ API response time: ${duration}ms (acceptable)"
        }
        else {
            Write-Error "✗ API response time: ${duration}ms (slow)"
            return $false
        }
        
        return $true
    }
    catch {
        Write-Error "✗ Performance test failed - API not responding: $($_.Exception.Message)"
        return $false
    }
}

# Main execution
function Main {
    Write-Info "Starting comprehensive health checks..."
    Write-Info "API Base URL: $ApiBaseUrl"
    Write-Info "Frontend URL: $FrontendUrl"
    Write-Host ""
    
    $failedChecks = 0
    
    # Run all health checks
    if (-not (Test-ApiHealth)) { $failedChecks++ }
    if (-not (Test-ApiDetailedHealth)) { $failedChecks++ }
    if (-not (Test-FrontendHealth)) { $failedChecks++ }
    if (-not (Test-AuthenticationEndpoints)) { $failedChecks++ }
    if (-not (Test-DiscoveryEndpoints)) { $failedChecks++ }
    if (-not (Test-RateLimiting)) { $failedChecks++ }
    if (-not (Test-SslCertificate)) { $failedChecks++ }
    if (-not (Test-SecurityHeaders)) { $failedChecks++ }
    if (-not (Test-Performance)) { $failedChecks++ }
    
    Write-Host ""
    if ($failedChecks -eq 0) {
        Write-Info "🎉 All health checks passed successfully!"
        exit 0
    }
    else {
        Write-Error "❌ $failedChecks health check(s) failed"
        exit 1
    }
}

# Run main function
Main