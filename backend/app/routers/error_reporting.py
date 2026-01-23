"""
Error reporting and monitoring endpoints.
Provides APIs for error reporting, monitoring, and alerting management.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.middleware.auth_middleware import get_optional_user, require_admin
from app.services.error_monitoring_service import (
    error_monitoring_service,
    ErrorCategory,
    ErrorSeverity,
    AlertType,
    record_error_metric
)
from app.services.error_handling_service import ErrorContext
from app.models import User

router = APIRouter()


class ErrorReportRequest(BaseModel):
    """Request model for error reporting"""
    error_type: str = Field(..., description="Type of error")
    category: str = Field(..., description="Error category")
    severity: str = Field(..., description="Error severity")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Error context")
    user_agent: Optional[str] = Field(default=None, description="User agent string")
    url: Optional[str] = Field(default=None, description="URL where error occurred")
    stack_trace: Optional[str] = Field(default=None, description="Error stack trace")


class AlertAcknowledgeRequest(BaseModel):
    """Request model for acknowledging alerts"""
    alert_id: str = Field(..., description="Alert ID to acknowledge")
    note: Optional[str] = Field(default=None, description="Acknowledgment note")


class AlertResolveRequest(BaseModel):
    """Request model for resolving alerts"""
    alert_id: str = Field(..., description="Alert ID to resolve")
    resolution_note: str = Field(..., description="Resolution note")


class AlertRuleUpdateRequest(BaseModel):
    """Request model for updating alert rules"""
    alert_type: str = Field(..., description="Alert type")
    threshold: Optional[int] = Field(default=None, description="Alert threshold")
    time_window_minutes: Optional[int] = Field(default=None, description="Time window in minutes")
    enabled: Optional[bool] = Field(default=None, description="Whether rule is enabled")
    cooldown_minutes: Optional[int] = Field(default=None, description="Cooldown period in minutes")


@router.post("/report")
async def report_error(
    request: ErrorReportRequest,
    http_request: Request,
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Report an error from the frontend for monitoring and analysis.
    """
    try:
        # Parse category and severity
        try:
            category = ErrorCategory(request.category.lower())
        except ValueError:
            category = ErrorCategory.INTERNAL
        
        try:
            severity = ErrorSeverity(request.severity.lower())
        except ValueError:
            severity = ErrorSeverity.MEDIUM
        
        # Create error context
        context = ErrorContext(
            user_id=current_user.id if current_user else None,
            request_id=getattr(http_request.state, 'request_id', None),
            endpoint=request.context.get('endpoint') if request.context else None,
            method=request.context.get('method') if request.context else None,
            ip_address=http_request.client.host if http_request.client else None,
            user_agent=request.user_agent or http_request.headers.get('user-agent'),
            additional_data={
                'url': request.url,
                'stack_trace': request.stack_trace,
                'frontend_context': request.context or {}
            }
        )
        
        # Prepare details
        details = {
            'message': request.message,
            'frontend_details': request.details or {},
            'reported_from': 'frontend',
            'user_agent': request.user_agent,
            'url': request.url
        }
        
        if request.stack_trace:
            details['stack_trace'] = request.stack_trace
        
        # Record error metric in background
        background_tasks.add_task(
            record_error_metric,
            request.error_type,
            category,
            severity,
            context,
            details
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "recorded",
                "message": "Error report received and will be processed",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        # Don't let error reporting fail the request
        return JSONResponse(
            status_code=200,
            content={
                "status": "failed",
                "message": "Error report could not be processed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/statistics")
async def get_error_statistics(
    hours: int = 24,
    current_user: User = Depends(require_admin)
):
    """
    Get comprehensive error statistics for monitoring dashboard.
    Requires admin privileges.
    """
    try:
        stats = error_monitoring_service.get_error_statistics(hours=hours)
        
        return {
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat(),
            "time_period_hours": hours
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve error statistics: {str(e)}"
        )


@router.get("/alerts/active")
async def get_active_alerts(
    current_user: User = Depends(require_admin)
):
    """
    Get all active alerts.
    Requires admin privileges.
    """
    try:
        alerts = error_monitoring_service.get_active_alerts()
        
        return {
            "alerts": alerts,
            "count": len(alerts),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve active alerts: {str(e)}"
        )


@router.get("/alerts/history")
async def get_alert_history(
    hours: int = 24,
    current_user: User = Depends(require_admin)
):
    """
    Get alert history for specified time period.
    Requires admin privileges.
    """
    try:
        alerts = error_monitoring_service.get_alert_history(hours=hours)
        
        return {
            "alerts": alerts,
            "count": len(alerts),
            "time_period_hours": hours,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve alert history: {str(e)}"
        )


@router.post("/alerts/acknowledge")
async def acknowledge_alert(
    request: AlertAcknowledgeRequest,
    current_user: User = Depends(require_admin)
):
    """
    Acknowledge an active alert.
    Requires admin privileges.
    """
    try:
        success = error_monitoring_service.acknowledge_alert(
            request.alert_id,
            current_user.email
        )
        
        if success:
            return {
                "status": "acknowledged",
                "alert_id": request.alert_id,
                "acknowledged_by": current_user.email,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="Alert not found or already acknowledged"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to acknowledge alert: {str(e)}"
        )


@router.post("/alerts/resolve")
async def resolve_alert(
    request: AlertResolveRequest,
    current_user: User = Depends(require_admin)
):
    """
    Resolve an active alert.
    Requires admin privileges.
    """
    try:
        success = error_monitoring_service.resolve_alert(
            request.alert_id,
            current_user.email,
            request.resolution_note
        )
        
        if success:
            return {
                "status": "resolved",
                "alert_id": request.alert_id,
                "resolved_by": current_user.email,
                "resolution_note": request.resolution_note,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="Alert not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resolve alert: {str(e)}"
        )


@router.get("/alerts/rules")
async def get_alert_rules(
    current_user: User = Depends(require_admin)
):
    """
    Get current alert rule configurations.
    Requires admin privileges.
    """
    try:
        rules = {}
        for alert_type, rule in error_monitoring_service.alert_rules.items():
            rules[alert_type.value] = {
                "alert_type": rule.alert_type.value,
                "threshold": rule.threshold,
                "time_window_minutes": rule.time_window_minutes,
                "severity": rule.severity.value,
                "enabled": rule.enabled,
                "cooldown_minutes": rule.cooldown_minutes,
                "conditions": rule.conditions
            }
        
        return {
            "rules": rules,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve alert rules: {str(e)}"
        )


@router.put("/alerts/rules")
async def update_alert_rule(
    request: AlertRuleUpdateRequest,
    current_user: User = Depends(require_admin)
):
    """
    Update an alert rule configuration.
    Requires admin privileges.
    """
    try:
        # Parse alert type
        try:
            alert_type = AlertType(request.alert_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid alert type: {request.alert_type}"
            )
        
        # Prepare update data
        update_data = {}
        if request.threshold is not None:
            update_data['threshold'] = request.threshold
        if request.time_window_minutes is not None:
            update_data['time_window_minutes'] = request.time_window_minutes
        if request.enabled is not None:
            update_data['enabled'] = request.enabled
        if request.cooldown_minutes is not None:
            update_data['cooldown_minutes'] = request.cooldown_minutes
        
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No update data provided"
            )
        
        # Update rule
        success = error_monitoring_service.update_alert_rule(alert_type, **update_data)
        
        if success:
            return {
                "status": "updated",
                "alert_type": request.alert_type,
                "updated_fields": list(update_data.keys()),
                "updated_by": current_user.email,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="Alert rule not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update alert rule: {str(e)}"
        )


@router.get("/health")
async def monitoring_health_check():
    """
    Health check endpoint for the monitoring service.
    """
    try:
        health_data = await error_monitoring_service.health_check()
        
        return {
            "service": "error_monitoring",
            "status": health_data["status"],
            "details": health_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "service": "error_monitoring",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/patterns")
async def get_error_patterns(
    hours: int = 24,
    current_user: User = Depends(require_admin)
):
    """
    Get error pattern analysis for the specified time period.
    Requires admin privileges.
    """
    try:
        # Get basic statistics
        stats = error_monitoring_service.get_error_statistics(hours=hours)
        
        # Add pattern analysis
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_metrics = [
            metric for metric in error_monitoring_service.error_metrics
            if metric.timestamp > cutoff_time
        ]
        
        # Analyze patterns
        patterns = {
            "trending_errors": [],
            "suspicious_ips": [],
            "affected_users": [],
            "peak_hours": []
        }
        
        # Find trending error types
        error_type_counts = {}
        for metric in recent_metrics:
            key = f"{metric.category.value}_{metric.error_type}"
            error_type_counts[key] = error_type_counts.get(key, 0) + 1
        
        patterns["trending_errors"] = sorted(
            error_type_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Find suspicious IP addresses
        ip_counts = {}
        for metric in recent_metrics:
            if metric.ip_address:
                ip_counts[metric.ip_address] = ip_counts.get(metric.ip_address, 0) + 1
        
        patterns["suspicious_ips"] = [
            {"ip": ip, "error_count": count}
            for ip, count in sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            if count > 5  # Only show IPs with more than 5 errors
        ]
        
        # Find affected users
        user_counts = {}
        for metric in recent_metrics:
            if metric.user_id:
                user_counts[metric.user_id] = user_counts.get(metric.user_id, 0) + 1
        
        patterns["affected_users"] = [
            {"user_id": user_id, "error_count": count}
            for user_id, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            if count > 3  # Only show users with more than 3 errors
        ]
        
        # Find peak error hours
        hour_counts = {}
        for metric in recent_metrics:
            hour = metric.timestamp.strftime("%Y-%m-%d %H:00")
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        patterns["peak_hours"] = sorted(
            hour_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:24]  # Last 24 hours
        
        return {
            "patterns": patterns,
            "statistics": stats,
            "analysis_period_hours": hours,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze error patterns: {str(e)}"
        )


# Webhook endpoint for external monitoring systems
@router.post("/webhook/external")
async def external_monitoring_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Webhook endpoint for receiving alerts from external monitoring systems.
    """
    try:
        payload = await request.json()
        
        # Process external alert in background
        background_tasks.add_task(
            process_external_alert,
            payload,
            request.headers.get('user-agent', 'unknown')
        )
        
        return {
            "status": "received",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=200,  # Always return 200 to prevent webhook retries
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


async def process_external_alert(payload: Dict[str, Any], source: str):
    """Process external monitoring alert"""
    try:
        # Map external alert to internal format
        error_type = payload.get('alert_type', 'external_alert')
        severity_map = {
            'critical': ErrorSeverity.CRITICAL,
            'high': ErrorSeverity.HIGH,
            'medium': ErrorSeverity.MEDIUM,
            'low': ErrorSeverity.LOW
        }
        
        severity = severity_map.get(
            payload.get('severity', 'medium').lower(),
            ErrorSeverity.MEDIUM
        )
        
        # Record as monitoring metric
        await record_error_metric(
            error_type=error_type,
            category=ErrorCategory.INTERNAL,
            severity=severity,
            details={
                'source': source,
                'external_payload': payload,
                'processed_at': datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        # Log but don't fail
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to process external alert: {e}")