# Authentication Setup Guide

This guide will help you set up the new authentication system for the Reverse Engineer Coach application.

## Overview

The application now includes a comprehensive authentication system with:

- **User Registration & Login**: Secure email/password authentication
- **API Key Management**: Encrypted storage of OpenAI, Gemini, and GitHub tokens
- **User Preferences**: Personalized language and framework preferences
- **Technology Search**: Smart search for programming languages and concepts
- **Secure Storage**: JWT tokens and encrypted API keys

## Backend Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/reverse_coach_db

# Security Configuration (IMPORTANT: Change these in production!)
SECRET_KEY=your-super-secret-key-change-in-production
ENCRYPTION_KEY=your-encryption-key-for-api-keys

# API Configuration
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### 3. Database Migration

Run the new migration to add the User table:

```bash
# Create the database if it doesn't exist
python create_db.py

# Run migrations
alembic upgrade head
```

### 4. Start Backend Server

```bash
python -m app.main
# or
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env`:

```env
REACT_APP_API_URL=http://localhost:8000
```

### 3. Start Frontend Server

```bash
npm start
```

## Using the Authentication System

### 1. Registration

When you first visit the application, you'll see the authentication page. To register:

1. Click "Sign up here" to switch to registration
2. Fill in your email and password
3. Choose your preferred AI provider (OpenAI or Gemini)
4. Enter the required API key for your chosen provider
5. Select your preferred programming language
6. Optionally add GitHub token and select frameworks
7. Click "Create Account"

### 2. Login

For existing users:

1. Enter your email and password
2. Click "Sign In"

### 3. User Profile Management

Once logged in, click on your username in the top-right corner to:

- Update your preferred programming language
- Change your AI provider
- Update API keys
- Sign out

### 4. Technology Search

The new technology selector allows you to search for:

- Programming languages (Python, TypeScript, Go, etc.)
- Frameworks (React, FastAPI, Spring Boot, etc.)
- Architecture patterns (Microservices, Event-Driven, etc.)
- System design concepts (Database Design, Load Balancing, etc.)
- And much more!

## API Key Requirements

### OpenAI API Key
- Format: `sk-...`
- Required if OpenAI is selected as preferred provider
- Get yours at: https://platform.openai.com/api-keys

### Gemini API Key
- Required if Gemini is selected as preferred provider
- Get yours at: https://makersuite.google.com/app/apikey

### GitHub Token (Optional)
- Format: `ghp_...` or `github_pat_...`
- Provides access to private repositories and higher rate limits
- Get yours at: https://github.com/settings/tokens

## Security Features

- **Password Security**: Enforced strong password requirements
- **API Key Encryption**: All API keys are encrypted before storage
- **JWT Authentication**: Secure token-based authentication
- **Input Validation**: Comprehensive validation on all inputs
- **CORS Protection**: Configured CORS for secure cross-origin requests

## Troubleshooting

### Common Issues

1. **"Authentication Required" Error**
   - Your session may have expired
   - Clear browser storage and log in again

2. **"Invalid API Key" Error**
   - Check that your API key format is correct
   - Ensure the key is active and has sufficient credits

3. **Database Connection Error**
   - Verify PostgreSQL is running
   - Check DATABASE_URL in .env file

4. **CORS Error**
   - Ensure CORS_ORIGINS includes your frontend URL
   - Check that both frontend and backend are running

### Getting Help

If you encounter issues:

1. Check the browser console for error messages
2. Check backend logs for detailed error information
3. Verify all environment variables are set correctly
4. Ensure all dependencies are installed

## Migration from Previous Version

If you're upgrading from a version without authentication:

1. Run the database migration: `alembic upgrade head`
2. All existing projects will need to be associated with users
3. Users will need to register and re-create their projects
4. API keys that were previously configured globally now need to be set per user

## Development Notes

### New Components Added

- `AuthPage`: Main authentication interface
- `LoginForm`: User login form
- `RegisterForm`: User registration with API key setup
- `UserProfile`: User profile management
- `TechnologySelector`: Smart technology search component
- `authStore`: Zustand store for authentication state
- `authService`: Authentication API service

### Backend Changes

- Added `User` model with encrypted API key storage
- Added authentication middleware and JWT handling
- Updated project endpoints to require authentication
- Added user preference management

### Database Schema

New `users` table with:
- Basic user information (email, password)
- Encrypted API keys (OpenAI, Gemini, GitHub)
- User preferences (language, frameworks, AI provider)
- Timestamps and status fields

The authentication system is now fully integrated and ready for use!