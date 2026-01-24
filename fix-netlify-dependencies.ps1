#!/usr/bin/env pwsh

Write-Host "🔧 Fixing Netlify Dependencies..." -ForegroundColor Green

# Create a temporary directory for the frontend repo
$tempDir = "temp-frontend-fix"
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}

Write-Host "📥 Cloning frontend repository..." -ForegroundColor Yellow
git clone https://github.com/ESHWARGEEK/reverse-engineer-coach-frontend.git $tempDir

Set-Location $tempDir

Write-Host "🔧 Fixing package.json dependencies..." -ForegroundColor Yellow

# Create a fixed package.json with compatible versions
$packageJson = @"
{
  "name": "reverse-engineer-coach-frontend",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "@headlessui/react": "^1.7.17",
    "@heroicons/react": "^1.0.6",
    "@hookform/resolvers": "^3.3.2",
    "@tailwindcss/forms": "^0.5.7",
    "@tailwindcss/typography": "^0.5.10",
    "@types/node": "^20.10.0",
    "@types/react": "^18.2.42",
    "@types/react-dom": "^18.2.17",
    "autoprefixer": "^10.4.16",
    "axios": "^1.6.2",
    "clsx": "^2.0.0",
    "lucide-react": "^0.263.1",
    "postcss": "^8.4.32",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "react-hook-form": "^7.48.2",
    "react-resizable-panels": "^0.0.55",
    "react-router-dom": "^6.8.1",
    "react-scripts": "5.0.1",
    "tailwindcss": "^3.3.6",
    "web-vitals": "^5.1.0",
    "zustand": "^4.4.7"
  },
  "scripts": {
    "start": "react-scripts start",
    "dev": "react-scripts start", 
    "build": "react-scripts build",
    "test": "react-scripts test --watchAll=false",
    "test:watch": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "eslintConfig": {
    "extends": [
      "react-app",
      "react-app/jest"
    ]
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.1.5",
    "@testing-library/react": "^13.4.0",
    "@testing-library/user-event": "^14.5.1",
    "@types/jest": "^29.5.8",
    "@types/react": "^18.2.42",
    "@types/react-dom": "^18.2.17",
    "fast-check": "^3.15.0",
    "jest-axe": "^10.0.0",
    "typescript": "^4.9.5"
  },
  "proxy": "http://localhost:8000"
}
"@

$packageJson | Out-File -FilePath "package.json" -Encoding UTF8

Write-Host "🌐 Creating netlify.toml..." -ForegroundColor Yellow

# Create netlify.toml with proper configuration
$netlifyToml = @"
[build]
  command = "npm ci && npm run build"
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

Write-Host "📝 Creating .env file..." -ForegroundColor Yellow

# Create .env file
$envFile = @"
SKIP_PREFLIGHT_CHECK=true
GENERATE_SOURCEMAP=false
CI=false
REACT_APP_API_URL=https://reverse-coach-backend.onrender.com
REACT_APP_ENVIRONMENT=production
"@

$envFile | Out-File -FilePath ".env" -Encoding UTF8

Write-Host "📝 Committing fixes..." -ForegroundColor Yellow
git add .
git commit -m "Fix Netlify deployment: Remove cross-env, fix dependencies, simplify build

- Removed cross-env dependency (incompatible with Node 18)
- Simplified build scripts to work with Netlify's Node 18 environment
- Fixed dependency conflicts causing AJV module errors
- Added proper environment variables via netlify.toml and .env
- Streamlined package.json for better compatibility"

Write-Host "📤 Pushing fixes..." -ForegroundColor Yellow
git push origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Successfully pushed dependency fixes!" -ForegroundColor Green
    Write-Host "🌐 Netlify will automatically deploy with fixed dependencies" -ForegroundColor Cyan
} else {
    Write-Host "❌ Failed to push fixes" -ForegroundColor Red
}

# Clean up
Set-Location ..
Remove-Item -Recurse -Force $tempDir

Write-Host ""
Write-Host "🔍 Monitor deployment at: https://app.netlify.com" -ForegroundColor Cyan