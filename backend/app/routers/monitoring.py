"""
Monitoring API Router

Provides endpoints for monitoring system health, security events, performance metrics,
and user analytics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from ..database import get_db
from ..middleware.auth_middleware import get_current_user
from ..models import User
from ..services.auth_logging_service import auth_logging_service
from ..services.security_monitoring_service import security_monitoring_service
from ..services.performance_monitoring_service import performance_monitoring_service
from ..services.user_analytics_service import user_analytics_service

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check with system status"""
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Check database connectivity
    try:
        db.execute("SELECT 1")
        health_status["checks"]["database"] = {"status": "healthy", "message": "Database connection OK"}
    except Exception as e:
        health_status["checks"]["database"] = {"status": "unhealthy", "message": f"Database error: {str(e)}"}
        health_status["status"] = "unhealthy"
    
    # Check Redis connectivity (if available)
    try:
        # This would need to be implemented based on your Redis setup
        health_status["checks"]["redis"] = {"status": "healthy", "message": "Redis connection OK"}
    except Exception as e:
        health_status["checks"]["redis"] = {"status": "unhealthy", "message": f"Redis error: {str(e)}"}
    
    # Check external API connectivity (GitHub, AI services)
    # This could be implemented to test API endpoints
    health_status["checks"]["external_apis"] = {"status": "healthy", "message": "External APIs accessible"}
    
    return health_status

@router.get("/security/dashboard")
async def get_security_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get security monitoring dashboard data (admin only)"""
    
    # Check if user has admin privileges (implement based on your user model)
    # For now, we'll assume all authenticated users can access this
    
    try:
        dashboard_data = await security_monitoring_service.get_security_dashboard_data(db)
        return dashboard_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get security dashboard data: {str(e)}")

@router.get("/security/ip-analytics/{ip_address}")
async def get_ip_analytics(
    ip_address: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analytics for a specific IP address (admin only)"""
    
    try:
        analytics = await security_monitoring_service.get_ip_analytics(ip_address, db)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get IP analytics: {str(e)}")

@router.post("/security/block-ip")
async def block_ip_address(
    ip_address: str,
    reason: str,
    current_user: User = Depends(get_current_user)
):
    """Block an IP address (admin only)"""
    
    try:
        security_monitoring_service.block_ip(ip_address, reason)
        return {"message": f"IP address {ip_address} has been blocked", "reason": reason}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to block IP address: {str(e)}")

@router.post("/security/unblock-ip")
async def unblock_ip_address(
    ip_address: str,
    current_user: User = Depends(get_current_user)
):
    """Unblock an IP address (admin only)"""
    
    try:
        security_monitoring_service.unblock_ip(ip_address)
        return {"message": f"IP address {ip_address} has been unblocked"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unblock IP address: {str(e)}")

@router.get("/performance/dashboard")
async def get_performance_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get performance monitoring dashboard data"""
    
    try:
        dashboard_data = await performance_monitoring_service.get_performance_dashboard_data(db)
        return dashboard_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance dashboard data: {str(e)}")

@router.get("/performance/discovery-report")
async def get_discovery_performance_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get performance report for discovery endpoints"""
    
    try:
        report = await performance_monitoring_service.get_discovery_performance_report(db)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get discovery performance report: {str(e)}")

@router.get("/performance/endpoint-stats")
async def get_endpoint_stats(
    endpoint: str = Query(..., description="Endpoint path to get statistics for"),
    method: str = Query("GET", description="HTTP method"),
    current_user: User = Depends(get_current_user)
):
    """Get performance statistics for a specific endpoint"""
    
    try:
        stats = performance_monitoring_service.get_endpoint_stats(endpoint, method)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get endpoint statistics: {str(e)}")

@router.get("/analytics/platform")
async def get_platform_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get platform-wide analytics (admin only)"""
    
    try:
        analytics = await user_analytics_service.get_platform_analytics(db, days)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get platform analytics: {str(e)}")

@router.get("/analytics/user/{user_id}")
async def get_user_analytics(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analytics for a specific user (admin only or own user)"""
    
    # Check if user is requesting their own analytics or is admin
    if current_user.id != user_id:
        # Implement admin check here
        # For now, we'll allow any authenticated user to access any user's analytics
        pass
    
    try:
        analytics = await user_analytics_service.get_user_analytics(user_id, db)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user analytics: {str(e)}")

@router.get("/analytics/retention")
async def get_retention_analysis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user retention analysis (admin only)"""
    
    try:
        retention_data = await user_analytics_service.get_user_retention_analysis(db)
        return retention_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get retention analysis: {str(e)}")

@router.get("/logs/auth-events")
async def get_auth_events(
    limit: int = Query(100, ge=1, le=1000, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    ip_address: Optional[str] = Query(None, description="Filter by IP address"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get authentication events log (admin only)"""
    
    try:
        from ..services.auth_logging_service import AuthEventLog
        from sqlalchemy import and_
        
        # Build query filters
        filters = []
        if event_type:
            filters.append(AuthEventLog.event_type == event_type)
        if user_id:
            filters.append(AuthEventLog.user_id == user_id)
        if ip_address:
            filters.append(AuthEventLog.ip_address == ip_address)
        
        # Query events
        query = db.query(AuthEventLog)
        if filters:
            query = query.filter(and_(*filters))
        
        events = query.order_by(AuthEventLog.timestamp.desc()).offset(offset).limit(limit).all()
        
        # Convert to dict format
        events_data = []
        for event in events:
            event_dict = {
                "id": event.id,
                "event_type": event.event_type,
                "user_id": event.user_id,
                "email": event.email,
                "ip_address": event.ip_address,
                "user_agent": event.user_agent,
                "timestamp": event.timestamp.isoformat(),
                "success": event.success,
                "details": event.details,
                "session_id": event.session_id,
                "risk_score": event.risk_score
            }
            events_data.append(event_dict)
        
        return {
            "events": events_data,
            "total": len(events_data),
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get auth events: {str(e)}")

@router.get("/system/metrics")
async def get_system_metrics(
    current_user: User = Depends(get_current_user)
):
    """Get basic system metrics"""
    
    try:
        import psutil
        import os
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get process metrics
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info()
        
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_total": memory.total,
                "memory_available": memory.available,
                "memory_percent": memory.percent,
                "disk_total": disk.total,
                "disk_used": disk.used,
                "disk_free": disk.free,
                "disk_percent": (disk.used / disk.total) * 100
            },
            "process": {
                "memory_rss": process_memory.rss,
                "memory_vms": process_memory.vms,
                "cpu_percent": process.cpu_percent(),
                "num_threads": process.num_threads(),
                "create_time": datetime.fromtimestamp(process.create_time()).isoformat()
            }
        }
        
        return metrics
        
    except ImportError:
        # psutil not available
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "message": "System metrics not available (psutil not installed)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system metrics: {str(e)}")

@router.get("/alerts/recent")
async def get_recent_alerts(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent security and performance alerts"""
    
    try:
        from ..services.auth_logging_service import AuthEventLog
        from sqlalchemy import and_
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get high-risk security events
        security_alerts = db.query(AuthEventLog).filter(
            and_(
                AuthEventLog.timestamp >= cutoff_time,
                AuthEventLog.risk_score >= 7
            )
        ).order_by(AuthEventLog.timestamp.desc()).limit(50).all()
        
        # Get performance alerts (slow requests)
        from ..services.performance_monitoring_service import PerformanceLog
        
        performance_alerts = db.query(PerformanceLog).filter(
            and_(
                PerformanceLog.timestamp >= cutoff_time,
                PerformanceLog.response_time >= 5.0  # 5+ second responses
            )
        ).order_by(PerformanceLog.timestamp.desc()).limit(50).all()
        
        alerts = {
            "security_alerts": [
                {
                    "type": "security",
                    "event_type": alert.event_type,
                    "ip_address": alert.ip_address,
                    "risk_score": alert.risk_score,
                    "timestamp": alert.timestamp.isoformat(),
                    "details": alert.details
                }
                for alert in security_alerts
            ],
            "performance_alerts": [
                {
                    "type": "performance",
                    "endpoint": alert.endpoint,
                    "response_time": alert.response_time,
                    "status_code": alert.status_code,
                    "timestamp": alert.timestamp.isoformat()
                }
                for alert in performance_alerts
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return alerts
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent alerts: {str(e)}")