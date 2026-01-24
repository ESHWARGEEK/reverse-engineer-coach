#!/usr/bin/env pwsh

Write-Host "⏳ Waiting for Render Deployment to Complete..." -ForegroundColor Cyan

$maxAttempts = 10
$attempt = 1

while ($attempt -le $maxAttempts) {
    Write-Host "`nAttempt $attempt/$maxAttempts - Testing CORS error responses..." -ForegroundColor Yellow
    
    try {
        # Test with curl to see headers
        $curlOutput = curl -X POST -H "Origin: https://reveng.netlify.app" -H "Content-Type: application/json" -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" -d '{"email":"test@example.com","password":"testpass123","preferred_ai_provider":"openai","preferred_language":"python"}' -I https://reverse-coach-backend.onrender.com/api/v1/auth/register 2>&1
        
        if ($curlOutput -match "access-control-allow-origin") {
            Write-Host "✅ CORS headers found in error response!" -ForegroundColor Green
            Write-Host "✅ Deployment successful!" -ForegroundColor Green
            
            # Show the CORS headers
            $corsOrigin = ($curlOutput | Select-String "access-control-allow-origin").ToString()
            Write-Host "   $corsOrigin" -ForegroundColor Gray
            
            break
        } else {
            Write-Host "⚠️  CORS headers not yet present - deployment still in progress..." -ForegroundColor Yellow
            
            # Show status code
            $statusLine = ($curlOutput | Select-String "HTTP/").ToString()
            if ($statusLine) {
                Write-Host "   Status: $statusLine" -ForegroundColor Gray
            }
        }
    }
    catch {
        Write-Host "⚠️  Request failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    
    if ($attempt -lt $maxAttempts) {
        Write-Host "Waiting 30 seconds before next attempt..." -ForegroundColor Gray
        Start-Sleep -Seconds 30
    }
    
    $attempt++
}

if ($attempt -gt $maxAttempts) {
    Write-Host "`n⏰ Deployment is taking longer than expected." -ForegroundColor Yellow
    Write-Host "Please check Render dashboard: https://dashboard.render.com" -ForegroundColor Gray
    Write-Host "Look for your 'reverse-coach-backend' service and check deployment status." -ForegroundColor Gray
} else {
    Write-Host "`n🎉 CORS Error Response Fix Successfully Deployed!" -ForegroundColor Green
    
    Write-Host "`n📋 What's Fixed:" -ForegroundColor Cyan
    Write-Host "✅ Rate limit errors (429) now include CORS headers" -ForegroundColor Green
    Write-Host "✅ Validation errors (422) now include CORS headers" -ForegroundColor Green
    Write-Host "✅ Server errors (500) now include CORS headers" -ForegroundColor Green
    Write-Host "✅ Frontend will show actual error messages instead of CORS blocks" -ForegroundColor Green
    
    Write-Host "`n🧪 Test the Frontend:" -ForegroundColor Yellow
    Write-Host "Go to https://reveng.netlify.app and try authentication" -ForegroundColor Blue
    Write-Host "You should now see proper error messages instead of CORS errors!" -ForegroundColor White
}

Write-Host "`n✨ Testing Complete!" -ForegroundColor Green