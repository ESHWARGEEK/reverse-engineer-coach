#!/usr/bin/env pwsh

Write-Host "🔧 Fixing Package Lock Issue..." -ForegroundColor Green

# Create a temporary directory for the frontend repo
$tempDir = "temp-frontend-lock-fix"
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}

Write-Host "📥 Cloning frontend repository..." -ForegroundColor Yellow
git clone https://github.com/ESHWARGEEK/reverse-engineer-coach-frontend.git $tempDir

Set-Location $tempDir

Write-Host "📦 Generating package-lock.json..." -ForegroundColor Yellow
npm install

Write-Host "🌐 Updating netlify.toml to use npm install..." -ForegroundColor Yellow

# Create netlify.toml with npm install instead of npm ci
$netlifyToml = @"
[build]
  command = "npm install && npm run build"
  publish = "build"

[build.environment]
  NODE_VERSION = "18"
  NPM_VERSION = "10"
  CI = "false"
  SKIP_PREFLIGHT_CHECK = "true"
  GENERATE_SOURCEMAP = "false"
  NPM_CONFIG_LEGACY_PEER_DEPS = "true"
  REACT_APP_API_URL = "https://reverse-coach-backend.onrender.com"
  REACT_APP_ENVIRONMENT = "production"

# SPA redirect for client-side routing
[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

# API proxy
[[redirects]]
  from = "/api/*"
  to = "https://reverse-coach-backend.onrender.com/api/:splat"
  status = 200
  force = false

# Security headers
[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-XSS-Protection = "1; mode=block"
    X-Content-Type-Options = "nosniff"
    Referrer-Policy = "strict-origin-when-cross-origin"
    Content-Security-Policy = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https:;"

# Cache static assets
[[headers]]
  for = "/static/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"
"@

$netlifyToml | Out-File -FilePath "netlify.toml" -Encoding UTF8

Write-Host "📝 Committing package-lock.json and updated config..." -ForegroundColor Yellow
git add .
git commit -m "Fix npm ci error: Add package-lock.json and update build command

- Generated package-lock.json file for consistent dependency resolution
- Updated netlify.toml to use 'npm install' instead of 'npm ci'
- This resolves the 'npm ci requires package-lock.json' error
- Maintains all dependency versions and environment configuration"

Write-Host "📤 Pushing fixes..." -ForegroundColor Yellow
git push origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Successfully pushed package-lock.json fix!" -ForegroundColor Green
    Write-Host "🌐 Netlify will now be able to install dependencies properly" -ForegroundColor Cyan
} else {
    Write-Host "❌ Failed to push fixes" -ForegroundColor Red
}

# Clean up
Set-Location ..
Remove-Item -Recurse -Force $tempDir

Write-Host ""
Write-Host "🔍 Monitor deployment at: https://app.netlify.com" -ForegroundColor Cyan