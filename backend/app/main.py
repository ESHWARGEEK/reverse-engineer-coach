from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import Response
import os
from dotenv import load_dotenv
from app.error_handlers import setup_error_handlers
from app.middleware.integration import setup_all_middleware
from app.middleware.error_handler_setup import setup_global_error_handling
from app.services.cors_service import cors_service
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Reverse Engineer Coach API",
    description="AI-powered educational platform for learning software architecture with enhanced authentication",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Request ID middleware for error tracking
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

app.add_middleware(RequestIDMiddleware)

# Configure CORS with enhanced security
cors_config = cors_service.get_cors_config()

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config["allow_origins"],
    allow_credentials=cors_config["allow_credentials"],
    allow_methods=cors_config["allow_methods"],
    allow_headers=cors_config["allow_headers"],
    expose_headers=cors_config["expose_headers"],
    max_age=cors_config["max_age"]
)

# Add trusted host middleware for security
allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0").split(",")
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts
)

# Set up comprehensive global error handling (must be before other error handlers)
enable_monitoring = os.getenv("ENABLE_ERROR_MONITORING", "true").lower() == "true"
setup_global_error_handling(app, enable_monitoring=enable_monitoring)

# Set up additional error handlers
setup_error_handlers(app)

# Set up all middleware (authentication, security, logging)
setup_all_middleware(app)

@app.get("/")
async def root():
    """Root endpoint for health check"""
    return {
        "message": "Reverse Engineer Coach API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint with service status"""
    from app.error_handlers import service_monitor
    
    try:
        # Check all services
        services = ["database", "cache", "github"]
        service_results = {}
        overall_status = "healthy"
        
        for service in services:
            result = await service_monitor.check_service_health(service)
            service_results[service] = result
            
            if result["status"] != "healthy":
                overall_status = "degraded"
        
        # Determine overall system status
        unhealthy_services = [s for s, r in service_results.items() if r["status"] == "unhealthy"]
        if len(unhealthy_services) >= 2:
            overall_status = "unhealthy"
        
        response_data = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "services": service_results
        }
        
        # Add degradation information if needed
        if overall_status != "healthy":
            degradation_info = {}
            for service, result in service_results.items():
                if result["status"] != "healthy" and result.get("degradation_available"):
                    strategy = await service_monitor.get_degradation_strategy(service)
                    if strategy:
                        degradation_info[service] = strategy
            
            if degradation_info:
                response_data["degradation_strategies"] = degradation_info
        
        return response_data
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# Metrics endpoint for monitoring
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    except ImportError:
        # Fallback if prometheus_client is not installed
        return {"error": "Metrics not available - prometheus_client not installed"}

# Include routers
from app.routers import projects, files, coach_minimal as coach, github, auth, profile, dashboard, discovery, error_reporting
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["profile"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(discovery.router, prefix="/api/v1", tags=["discovery"])
app.include_router(error_reporting.router, prefix="/api/v1/errors", tags=["error_reporting"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(files.router, prefix="/api/v1/projects", tags=["files"])
app.include_router(coach.router, tags=["coach"])
app.include_router(github.router, prefix="/api/v1/github", tags=["github"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=True
    )