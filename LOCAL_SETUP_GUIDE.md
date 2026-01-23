# Reverse Engineer Coach - Local Setup Guide

## Overview
This guide will help you set up and run the Reverse Engineer Coach application locally on your Windows machine.

## Prerequisites
- ✅ Node.js 18+ (Currently: v25.2.1)
- ✅ Python 3.11+ (Currently: v3.13.1)
- ✅ npm 9+ (Currently: v11.1.0)

## Quick Setup (Automated)

### Option 1: Using the Setup Script
```powershell
.\setup-local.ps1
```

This script will:
- Check prerequisites
- Create a local .env file
- Set up Python virtual environment
- Install all dependencies
- Run database migrations

### Option 2: Manual Setup

1. **Install Dependencies**
   ```powershell
   # Install root dependencies
   npm install
   
   # Install backend dependencies
   cd backend
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   
   # Install frontend dependencies
   cd ../frontend
   npm install
   ```

2. **Set up Environment Variables**
   ```powershell
   # Copy the example environment file
   cp .env.example .env
   ```

3. **Run Database Migrations**
   ```powershell
   cd backend
   .\venv\Scripts\Activate.ps1
   alembic upgrade head
   ```

## Running the Application

### Method 1: Start Both Services Together
```powershell
npm run dev
```

### Method 2: Start Services Separately

**Terminal 1 - Backend:**
```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 - Frontend:**
```powershell
cd frontend
npm run dev
```

## Application URLs

Once running, you can access:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc

## Current Status

### ✅ Working Components
- Backend FastAPI server starts successfully
- Frontend React application builds successfully
- Database migrations work
- Basic API endpoints are functional
- Authentication system is implemented
- Project management features are available

### ⚠️ Known Issues
- Some npm security vulnerabilities (non-critical)
- Some Pydantic deprecation warnings (non-breaking)
- Test suite has some import issues (doesn't affect functionality)

### 🔧 Fixed Issues
- TypeScript compilation errors in frontend
- Property name mismatches between interfaces
- Import statement corrections

## Testing the Application

### Frontend Build Test
```powershell
cd frontend
npm run build
```
✅ **Status**: Builds successfully with warnings (non-critical)

### Backend Import Test
```powershell
cd backend
python -c "from app.main import app; print('Backend imports successfully')"
```
✅ **Status**: Imports successfully

## Optional Configuration

### AI Integration (Optional)
To enable full AI features, add these to your `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### GitHub Integration (Optional)
For repository analysis features:
```env
GITHUB_TOKEN=your_github_token_here
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   - Backend (8000): Change `API_PORT` in `.env`
   - Frontend (3000): React will automatically suggest port 3001

2. **Python Virtual Environment Issues**
   ```powershell
   cd backend
   Remove-Item -Recurse -Force venv
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. **Node Modules Issues**
   ```powershell
   cd frontend
   Remove-Item -Recurse -Force node_modules
   npm install
   ```

4. **Database Issues**
   ```powershell
   cd backend
   Remove-Item reverse_coach.db  # If using SQLite
   alembic upgrade head
   ```

## Next Steps

Once the application is running locally:
1. Visit http://localhost:3000
2. Create a user account
3. Explore the repository discovery features
4. Try creating a learning project

## Development Notes

- The application uses SQLite for local development (no PostgreSQL required)
- Redis is optional for local development
- Hot reloading is enabled for both frontend and backend
- API documentation is automatically generated and available at `/docs`