# Reverse Engineer Coach

AI-powered educational platform for learning software architecture by rebuilding simplified versions of famous open-source tools.

## Project Structure

```
reverse-engineer-coach/
├── backend/                 # Python FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py         # FastAPI application entry point
│   │   ├── config.py       # Configuration settings
│   │   ├── database.py     # Database connection and session management
│   │   └── cache.py        # Redis cache integration
│   ├── migrations/         # Alembic database migrations
│   ├── requirements.txt    # Python dependencies
│   ├── Dockerfile         # Backend container configuration
│   └── alembic.ini        # Alembic configuration
├── frontend/               # React TypeScript frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── index.tsx      # Application entry point
│   │   ├── App.tsx        # Main application component
│   │   └── index.css      # Tailwind CSS styles
│   ├── public/            # Static assets
│   ├── package.json       # Node.js dependencies
│   ├── Dockerfile         # Frontend container configuration
│   ├── tailwind.config.js # Tailwind CSS configuration
│   └── tsconfig.json      # TypeScript configuration
├── docker-compose.yml     # Multi-service container orchestration
├── package.json          # Monorepo configuration
├── .env.example          # Environment variables template
└── .gitignore           # Git ignore rules
```

## Quick Start

### Prerequisites

- Node.js 18+ and npm 9+
- Python 3.11+
- Docker and Docker Compose (optional)

### Development Setup

1. **Clone and install dependencies:**
   ```bash
   npm install
   cd backend && pip install -r requirements.txt
   cd ../frontend && npm install
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start services with Docker (recommended):**
   ```bash
   npm run docker:up
   ```

4. **Or start services manually:**
   ```bash
   # Terminal 1: Start database and cache
   docker-compose up postgres redis
   
   # Terminal 2: Start backend
   npm run dev:backend
   
   # Terminal 3: Start frontend
   npm run dev:frontend
   ```

### Available Scripts

- `npm run dev` - Start both backend and frontend in development mode
- `npm run dev:backend` - Start only the FastAPI backend
- `npm run dev:frontend` - Start only the React frontend
- `npm run build` - Build both applications for production
- `npm run test` - Run tests for both applications
- `npm run docker:up` - Start all services with Docker Compose
- `npm run docker:down` - Stop all Docker services

## Services

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - SQL toolkit and ORM
- **Alembic** - Database migration tool
- **PostgreSQL** - Primary database
- **Redis** - Caching and session storage
- **Pydantic** - Data validation and settings

### Frontend
- **React 18** - UI library
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **Zustand** - State management
- **Monaco Editor** - Code editor component
- **React Router** - Client-side routing

### Development
- **Docker** - Containerization
- **Pytest** - Python testing framework
- **Jest** - JavaScript testing framework
- **Hypothesis** - Property-based testing for Python
- **fast-check** - Property-based testing for TypeScript

## Architecture

The application follows a modern full-stack architecture:

- **Frontend**: React SPA with TypeScript and Tailwind CSS
- **Backend**: FastAPI REST API with async/await support
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache**: Redis for performance optimization
- **AI Integration**: OpenAI/Anthropic APIs for code analysis and coaching
- **Repository Analysis**: GitHub API integration via MCP client

## Next Steps

This infrastructure setup provides the foundation for:

1. **Data Models** - SQLAlchemy models for projects, tasks, and code snippets
2. **GitHub Integration** - MCP client for repository analysis
3. **AI Services** - LLM integration for specification generation and coaching
4. **Interactive Workspace** - Three-pane layout with Monaco editor
5. **Real-time Features** - WebSocket support for live coaching

See the implementation tasks in `.kiro/specs/reverse-engineer-coach/tasks.md` for detailed development roadmap.