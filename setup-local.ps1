# Reverse Engineer Coach - Local Development Setup
# This script sets up the application for local development without Docker

Write-Host "🚀 Setting up Reverse Engineer Coach locally..." -ForegroundColor Green

# Check prerequisites
Write-Host "📋 Checking prerequisites..." -ForegroundColor Yellow

# Check Node.js
try {
    $nodeVersion = node --version
    Write-Host "✅ Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js not found. Please install Node.js 18+ from https://nodejs.org" -ForegroundColor Red
    exit 1
}

# Check Python
try {
    $pythonVersion = python --version
    Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python 3.9+ from https://python.org" -ForegroundColor Red
    exit 1
}

# Check PostgreSQL (optional - we'll use SQLite for local dev)
Write-Host "📦 Setting up local database (SQLite)..." -ForegroundColor Yellow

# Create environment file for local development
Write-Host "⚙️ Creating local environment configuration..." -ForegroundColor Yellow

$envContent = @"
# Local Development Configuration
DATABASE_URL=sqlite:///./reverse_coach.db
REDIS_URL=redis://localhost:6379

# API Configuration
API_HOST=127.0.0.1
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Environment
ENVIRONMENT=development
DEBUG=true

# Frontend Configuration
REACT_APP_API_URL=http://localhost:8000

# Optional: Add your API keys here for full functionality
# OPENAI_API_KEY=your_openai_api_key_here
# ANTHROPIC_API_KEY=your_anthropic_api_key_here
# GITHUB_TOKEN=your_github_token_here
"@

$envContent | Out-File -FilePath ".env" -Encoding UTF8
Write-Host "✅ Created .env file" -ForegroundColor Green

# Setup Backend
Write-Host "🐍 Setting up Python backend..." -ForegroundColor Yellow
Set-Location backend

# Create virtual environment
python -m venv venv
Write-Host "✅ Created Python virtual environment" -ForegroundColor Green

# Activate virtual environment and install dependencies
& ".\venv\Scripts\Activate.ps1"
pip install -r requirements.txt
Write-Host "✅ Installed Python dependencies" -ForegroundColor Green

# Setup database
Write-Host "🗄️ Setting up database..." -ForegroundColor Yellow
alembic upgrade head
Write-Host "✅ Database migrations completed" -ForegroundColor Green

Set-Location ..

# Setup Frontend
Write-Host "⚛️ Setting up React frontend..." -ForegroundColor Yellow
Set-Location frontend

npm install
Write-Host "✅ Installed Node.js dependencies" -ForegroundColor Green

Set-Location ..

Write-Host "🎉 Setup completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 To start the application:" -ForegroundColor Cyan
Write-Host "1. Start the backend:" -ForegroundColor White
Write-Host "   cd backend" -ForegroundColor Gray
Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000" -ForegroundColor Gray
Write-Host ""
Write-Host "2. In a new terminal, start the frontend:" -ForegroundColor White
Write-Host "   cd frontend" -ForegroundColor Gray
Write-Host "   npm run dev" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Open your browser to: http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "📝 Note: For full functionality, add your API keys to the .env file" -ForegroundColor Yellow