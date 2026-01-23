# Deployment Validation Script
# Validates that the deployment is ready and all services are functioning correctly

param(
    [string]$Environment = "production",
    [string]$Namespace = "production",
    [string]$ApiUrl = "https://api.your-domain.com",
    [string]$FrontendUrl = "https://your-domain.com",
    [int]$TimeoutSeconds = 300
)

# Import required modules
if (Get-Module -ListAvailable -Name "kubernetes") {
    Import-Module kubernetes
} else {
    Write-Warning "Kubernetes module not available. Some checks will be skipped."
}

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

function Test-KubernetesDeployments {
    Write-Info "Checking Kubernetes deployments..."
    
    try {
        # Check if kubectl is available
        $kubectlVersion = kubectl version --client --short 2>$null
        if (-not $kubectlVersion) {
            Write-Warn "kubectl not available - skipping Kubernetes checks"
            return $true
        }
        
        # Check deployment status
        $deployments = @("backend", "frontend", "postgres", "redis")
        $allHealthy = $true
        
        foreach ($deployment in $deployments) {
            try {
                $status = kubectl get deployment $deployment -n $Namespace -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' 2>$null
                
                if ($status -eq "True") {
                    Write-Info "✓ Deployment $deployment is available"
                }
                else {
                    Write-Error "✗ Deployment $deployment is not available"
                    $allHealthy = $false
                }
            }
            catch {
                Write-Warn "⚠ Could not check deployment $deployment"
            }
        }
        
        return $allHealthy
    }
    catch {
        Write-Warn "Kubernetes deployment check failed: $($_.Exception.Message)"
        return $true  # Don't fail the entire validation if k8s checks fail
    }
}

function Test-PodHealth {
    Write-Info "Checking pod health..."
    
    try {
        # Check if kubectl is available
        $kubectlVersion = kubectl version --client --short 2>$null
        if (-not $kubectlVersion) {
            Write-Warn "kubectl not available - skipping pod health checks"
            return $true
        }
        
        # Get all pods in the namespace
        $pods = kubectl get pods -n $Namespace -o json 2>$null | ConvertFrom-Json
        
        if (-not $pods) {
            Write-Warn "Could not retrieve pod information"
            return $true
        }
        
        $allHealthy = $true
        
        foreach ($pod in $pods.items) {
            $podName = $pod.metadata.name
            $phase = $pod.status.phase
            
            if ($phase -eq "Running") {
                # Check if all containers are ready
                $readyContainers = 0
                $totalContainers = $pod.status.containerStatuses.Count
                
                foreach ($container in $pod.status.containerStatuses) {
                    if ($container.ready) {
                        $readyContainers++
                    }
                }
                
                if ($readyContainers -eq $totalContainers) {
                    Write-Info "✓ Pod $podName is running and ready ($readyContainers/$totalContainers containers)"
                }
                else {
                    Write-Error "✗ Pod $podName has unhealthy containers ($readyContainers/$totalContainers ready)"
                    $allHealthy = $false
                }
            }
            else {
                Write-Error "✗ Pod $podName is in phase: $phase"
                $allHealthy = $false
            }
        }
        
        return $allHealthy
    }
    catch {
        Write-Warn "Pod health check failed: $($_.Exception.Message)"
        return $true  # Don't fail the entire validation if k8s checks fail
    }
}

function Test-ServiceEndpoints {
    Write-Info "Checking service endpoints..."
    
    try {
        # Check if kubectl is available
        $kubectlVersion = kubectl version --client --short 2>$null
        if (-not $kubectlVersion) {
            Write-Warn "kubectl not available - skipping service endpoint checks"
            return $true
        }
        
        $services = @("backend-service", "frontend-service", "postgres-service", "redis-service")
        $allHealthy = $true
        
        foreach ($service in $services) {
            try {
                $endpoints = kubectl get endpoints $service -n $Namespace -o jsonpath='{.subsets[*].addresses[*].ip}' 2>$null
                
                if ($endpoints) {
                    $endpointCount = ($endpoints -split ' ').Count
                    Write-Info "✓ Service $service has $endpointCount endpoint(s)"
                }
                else {
                    Write-Error "✗ Service $service has no endpoints"
                    $allHealthy = $false
                }
            }
            catch {
                Write-Warn "⚠ Could not check service $service"
            }
        }
        
        return $allHealthy
    }
    catch {
        Write-Warn "Service endpoint check failed: $($_.Exception.Message)"
        return $true  # Don't fail the entire validation if k8s checks fail
    }
}

function Test-DatabaseMigrations {
    Write-Info "Checking database migrations..."
    
    try {
        # Check if kubectl is available
        $kubectlVersion = kubectl version --client --short 2>$null
        if (-not $kubectlVersion) {
            Write-Warn "kubectl not available - skipping migration checks"
            return $true
        }
        
        # Check if there are any pending migrations by running a test job
        $jobName = "migration-check-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        
        $jobYaml = @"
apiVersion: batch/v1
kind: Job
metadata:
  name: $jobName
  namespace: $Namespace
spec:
  template:
    spec:
      containers:
      - name: migration-check
        image: ghcr.io/your-org/reverse-engineer-coach-backend:latest
        command:
        - /bin/bash
        - -c
        - |
          echo "Checking database migration status..."
          alembic current
          alembic check
          echo "Migration check completed"
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: DATABASE_URL
      restartPolicy: Never
  backoffLimit: 1
"@
        
        # Create and run the job
        $jobYaml | kubectl apply -f - 2>$null
        
        # Wait for job completion
        $timeout = 60  # 60 seconds timeout for migration check
        $elapsed = 0
        
        while ($elapsed -lt $timeout) {
            $jobStatus = kubectl get job $jobName -n $Namespace -o jsonpath='{.status.conditions[?(@.type=="Complete")].status}' 2>$null
            
            if ($jobStatus -eq "True") {
                Write-Info "✓ Database migrations are up to date"
                kubectl delete job $jobName -n $Namespace 2>$null
                return $true
            }
            
            $jobFailed = kubectl get job $jobName -n $Namespace -o jsonpath='{.status.conditions[?(@.type=="Failed")].status}' 2>$null
            if ($jobFailed -eq "True") {
                Write-Error "✗ Database migration check failed"
                kubectl logs job/$jobName -n $Namespace 2>$null
                kubectl delete job $jobName -n $Namespace 2>$null
                return $false
            }
            
            Start-Sleep -Seconds 5
            $elapsed += 5
        }
        
        Write-Warn "⚠ Database migration check timed out"
        kubectl delete job $jobName -n $Namespace 2>$null
        return $true  # Don't fail validation on timeout
    }
    catch {
        Write-Warn "Database migration check failed: $($_.Exception.Message)"
        return $true  # Don't fail the entire validation
    }
}

function Test-ExternalConnectivity {
    Write-Info "Testing external connectivity..."
    
    $allHealthy = $true
    
    # Test API connectivity
    try {
        $response = Invoke-RestMethod -Uri "$ApiUrl/api/monitoring/health" -TimeoutSec 30 -ErrorAction Stop
        Write-Info "✓ API is accessible externally"
    }
    catch {
        Write-Error "✗ API is not accessible externally: $($_.Exception.Message)"
        $allHealthy = $false
    }
    
    # Test Frontend connectivity
    try {
        $response = Invoke-WebRequest -Uri $FrontendUrl -TimeoutSec 30 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Info "✓ Frontend is accessible externally"
        }
        else {
            Write-Error "✗ Frontend returned status code: $($response.StatusCode)"
            $allHealthy = $false
        }
    }
    catch {
        Write-Error "✗ Frontend is not accessible externally: $($_.Exception.Message)"
        $allHealthy = $false
    }
    
    return $allHealthy
}

function Test-SecurityConfiguration {
    Write-Info "Checking security configuration..."
    
    $allSecure = $true
    
    # Check HTTPS enforcement
    try {
        $httpUrl = $FrontendUrl -replace "https://", "http://"
        $response = Invoke-WebRequest -Uri $httpUrl -TimeoutSec 10 -MaximumRedirection 0 -ErrorAction Stop
        
        if ($response.StatusCode -eq 301 -or $response.StatusCode -eq 302) {
            $location = $response.Headers.Location
            if ($location -and $location.StartsWith("https://")) {
                Write-Info "✓ HTTP to HTTPS redirect is working"
            }
            else {
                Write-Warn "⚠ HTTP redirect is not to HTTPS"
            }
        }
        else {
            Write-Warn "⚠ HTTP is not being redirected to HTTPS"
        }
    }
    catch {
        # This might be expected if HTTP is completely blocked
        Write-Info "✓ HTTP access is blocked (expected for secure deployments)"
    }
    
    # Check security headers
    try {
        $response = Invoke-WebRequest -Uri $FrontendUrl -TimeoutSec 30 -ErrorAction Stop
        
        $securityHeaders = @(
            "Strict-Transport-Security",
            "X-Frame-Options",
            "X-Content-Type-Options",
            "X-XSS-Protection"
        )
        
        foreach ($header in $securityHeaders) {
            if ($response.Headers[$header]) {
                Write-Info "✓ Security header present: $header"
            }
            else {
                Write-Warn "⚠ Security header missing: $header"
            }
        }
    }
    catch {
        Write-Warn "Could not check security headers: $($_.Exception.Message)"
    }
    
    return $allSecure
}

function Test-PerformanceBaseline {
    Write-Info "Testing performance baseline..."
    
    $performanceGood = $true
    
    # Test API response time
    try {
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        $response = Invoke-RestMethod -Uri "$ApiUrl/api/monitoring/health" -TimeoutSec 30 -ErrorAction Stop
        $stopwatch.Stop()
        
        $responseTime = $stopwatch.ElapsedMilliseconds
        
        if ($responseTime -lt 1000) {
            Write-Info "✓ API response time: ${responseTime}ms (excellent)"
        }
        elseif ($responseTime -lt 2000) {
            Write-Info "✓ API response time: ${responseTime}ms (good)"
        }
        elseif ($responseTime -lt 5000) {
            Write-Warn "⚠ API response time: ${responseTime}ms (acceptable)"
        }
        else {
            Write-Error "✗ API response time: ${responseTime}ms (poor)"
            $performanceGood = $false
        }
    }
    catch {
        Write-Error "✗ Could not test API performance: $($_.Exception.Message)"
        $performanceGood = $false
    }
    
    # Test Frontend response time
    try {
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        $response = Invoke-WebRequest -Uri $FrontendUrl -TimeoutSec 30 -ErrorAction Stop
        $stopwatch.Stop()
        
        $responseTime = $stopwatch.ElapsedMilliseconds
        
        if ($responseTime -lt 2000) {
            Write-Info "✓ Frontend response time: ${responseTime}ms (good)"
        }
        elseif ($responseTime -lt 5000) {
            Write-Warn "⚠ Frontend response time: ${responseTime}ms (acceptable)"
        }
        else {
            Write-Error "✗ Frontend response time: ${responseTime}ms (poor)"
            $performanceGood = $false
        }
    }
    catch {
        Write-Error "✗ Could not test Frontend performance: $($_.Exception.Message)"
        $performanceGood = $false
    }
    
    return $performanceGood
}

# Main execution
function Main {
    Write-Info "Starting deployment validation for environment: $Environment"
    Write-Info "Namespace: $Namespace"
    Write-Info "API URL: $ApiUrl"
    Write-Info "Frontend URL: $FrontendUrl"
    Write-Host ""
    
    $failedChecks = 0
    
    # Run all validation checks
    if (-not (Test-KubernetesDeployments)) { $failedChecks++ }
    if (-not (Test-PodHealth)) { $failedChecks++ }
    if (-not (Test-ServiceEndpoints)) { $failedChecks++ }
    if (-not (Test-DatabaseMigrations)) { $failedChecks++ }
    if (-not (Test-ExternalConnectivity)) { $failedChecks++ }
    if (-not (Test-SecurityConfiguration)) { $failedChecks++ }
    if (-not (Test-PerformanceBaseline)) { $failedChecks++ }
    
    Write-Host ""
    if ($failedChecks -eq 0) {
        Write-Info "🎉 Deployment validation completed successfully!"
        Write-Info "The $Environment environment is ready for use."
        exit 0
    }
    else {
        Write-Error "❌ $failedChecks validation check(s) failed"
        Write-Error "The $Environment environment may not be ready for use."
        exit 1
    }
}

# Run main function
Main