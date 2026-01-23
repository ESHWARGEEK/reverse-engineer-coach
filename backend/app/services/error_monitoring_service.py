"""
Enhanced error monitoring and alerting service.
Provides comprehensive error tracking, pattern analysis, and alerting capabilities.
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
import uuid

from app.services.error_handling_service import ErrorSeverity, ErrorCategory, ErrorContext

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Types of alerts that can be triggered"""
    ERROR_SPIKE = "error_spike"
    AUTHENTICATION_ATTACK = "authentication_attack"
    SERVICE_DEGRADATION = "service_degradation"
    CRITICAL_ERROR = "critical_error"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    SECURITY_INCIDENT = "security_incident"


@dataclass
class ErrorMetric:
    """Individual error metric data"""
    error_id: str
    error_type: str
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: datetime
    user_id: Optional[str] = None
    endpoint: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertRule:
    """Configuration for alert rules"""
    alert_type: AlertType
    threshold: int
    time_window_minutes: int
    severity: ErrorSeverity
    enabled: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)
    cooldown_minutes: int = 15  # Minimum time between alerts of same type


@dataclass
class Alert:
    """Alert instance"""
    alert_id: str
    alert_type: AlertType
    severity: ErrorSeverity
    title: str
    message: str
    timestamp: datetime
    triggered_by: List[ErrorMetric]
    metadata: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False


class ErrorMonitoringService:
    """
    Comprehensive error monitoring service with real-time analysis and alerting.
    """
    
    def __init__(self, max_metrics_retention: int = 10000):
        self.max_metrics_retention = max_metrics_retention
        self.error_metrics: deque = deque(maxlen=max_metrics_retention)
        self.alert_rules: Dict[AlertType, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        self.last_alert_times: Dict[AlertType, datetime] = {}
        
        # Pattern analysis
        self.error_patterns: Dict[str, List[datetime]] = defaultdict(list)
        self.ip_patterns: Dict[str, List[datetime]] = defaultdict(list)
        self.user_patterns: Dict[str, List[datetime]] = defaultdict(list)
        
        # Performance tracking
        self.response_times: deque = deque(maxlen=1000)
        self.error_rates: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        self._initialize_default_alert_rules()
    
    def _initialize_default_alert_rules(self) -> None:
        """Initialize default alert rules"""
        
        # Error spike detection
        self.alert_rules[AlertType.ERROR_SPIKE] = AlertRule(
            alert_type=AlertType.ERROR_SPIKE,
            threshold=50,  # 50 errors in time window
            time_window_minutes=5,
            severity=ErrorSeverity.HIGH,
            conditions={"exclude_categories": ["validation"]}
        )
        
        # Authentication attack detection
        self.alert_rules[AlertType.AUTHENTICATION_ATTACK] = AlertRule(
            alert_type=AlertType.AUTHENTICATION_ATTACK,
            threshold=10,  # 10 auth failures from same IP
            time_window_minutes=60,
            severity=ErrorSeverity.CRITICAL,
            conditions={"category": "authentication"}
        )
        
        # Service degradation detection
        self.alert_rules[AlertType.SERVICE_DEGRADATION] = AlertRule(
            alert_type=AlertType.SERVICE_DEGRADATION,
            threshold=20,  # 20 service errors
            time_window_minutes=10,
            severity=ErrorSeverity.HIGH,
            conditions={"category": "service_unavailable"}
        )
        
        # Critical error detection
        self.alert_rules[AlertType.CRITICAL_ERROR] = AlertRule(
            alert_type=AlertType.CRITICAL_ERROR,
            threshold=1,  # Any critical error
            time_window_minutes=1,
            severity=ErrorSeverity.CRITICAL,
            conditions={"severity": "critical"}
        )
        
        # Performance degradation
        self.alert_rules[AlertType.PERFORMANCE_DEGRADATION] = AlertRule(
            alert_type=AlertType.PERFORMANCE_DEGRADATION,
            threshold=100,  # 100 slow requests
            time_window_minutes=15,
            severity=ErrorSeverity.MEDIUM,
            conditions={"response_time_threshold": 5000}  # 5 seconds
        )
    
    async def record_error(
        self,
        error_type: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        context: Optional[ErrorContext] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record an error metric and trigger analysis.
        
        Returns:
            Error ID for tracking
        """
        error_id = str(uuid.uuid4())
        
        metric = ErrorMetric(
            error_id=error_id,
            error_type=error_type,
            category=category,
            severity=severity,
            timestamp=datetime.utcnow(),
            user_id=context.user_id if context else None,
            endpoint=context.endpoint if context else None,
            ip_address=context.ip_address if context else None,
            user_agent=context.user_agent if context else None,
            request_id=context.request_id if context else None,
            details=details or {}
        )
        
        # Store metric
        self.error_metrics.append(metric)
        
        # Update patterns
        self._update_patterns(metric)
        
        # Trigger real-time analysis
        await self._analyze_and_alert(metric)
        
        # Log metric
        logger.info(
            f"Error recorded: {error_type}",
            extra={
                "error_id": error_id,
                "category": category.value,
                "severity": severity.value,
                "context": asdict(context) if context else None
            }
        )
        
        return error_id
    
    def _update_patterns(self, metric: ErrorMetric) -> None:
        """Update error patterns for analysis"""
        current_time = metric.timestamp
        
        # Update error type patterns
        pattern_key = f"{metric.category.value}_{metric.error_type}"
        self.error_patterns[pattern_key].append(current_time)
        
        # Update IP patterns if available
        if metric.ip_address:
            self.ip_patterns[metric.ip_address].append(current_time)
        
        # Update user patterns if available
        if metric.user_id:
            self.user_patterns[metric.user_id].append(current_time)
        
        # Clean old patterns (keep only last 24 hours)
        cutoff_time = current_time - timedelta(hours=24)
        
        for pattern_list in [self.error_patterns, self.ip_patterns, self.user_patterns]:
            for key in list(pattern_list.keys()):
                pattern_list[key] = [
                    timestamp for timestamp in pattern_list[key]
                    if timestamp > cutoff_time
                ]
                if not pattern_list[key]:
                    del pattern_list[key]
    
    async def _analyze_and_alert(self, metric: ErrorMetric) -> None:
        """Analyze error patterns and trigger alerts if necessary"""
        
        # Check each alert rule
        for alert_type, rule in self.alert_rules.items():
            if not rule.enabled:
                continue
            
            # Check cooldown period
            if self._is_in_cooldown(alert_type, rule.cooldown_minutes):
                continue
            
            # Check if conditions match
            if not self._matches_conditions(metric, rule):
                continue
            
            # Check threshold
            if await self._check_threshold(alert_type, rule):
                await self._trigger_alert(alert_type, rule, metric)
    
    def _is_in_cooldown(self, alert_type: AlertType, cooldown_minutes: int) -> bool:
        """Check if alert type is in cooldown period"""
        last_alert_time = self.last_alert_times.get(alert_type)
        if not last_alert_time:
            return False
        
        cooldown_period = timedelta(minutes=cooldown_minutes)
        return datetime.utcnow() - last_alert_time < cooldown_period
    
    def _matches_conditions(self, metric: ErrorMetric, rule: AlertRule) -> bool:
        """Check if metric matches alert rule conditions"""
        conditions = rule.conditions
        
        # Check category condition
        if "category" in conditions:
            if metric.category.value != conditions["category"]:
                return False
        
        # Check severity condition
        if "severity" in conditions:
            if metric.severity.value != conditions["severity"]:
                return False
        
        # Check exclude categories
        if "exclude_categories" in conditions:
            if metric.category.value in conditions["exclude_categories"]:
                return False
        
        # Check endpoint condition
        if "endpoint" in conditions:
            if metric.endpoint != conditions["endpoint"]:
                return False
        
        return True
    
    async def _check_threshold(self, alert_type: AlertType, rule: AlertRule) -> bool:
        """Check if threshold is exceeded for alert rule"""
        time_window = timedelta(minutes=rule.time_window_minutes)
        cutoff_time = datetime.utcnow() - time_window
        
        if alert_type == AlertType.ERROR_SPIKE:
            # Count all errors in time window (excluding validation errors)
            count = sum(
                1 for metric in self.error_metrics
                if (metric.timestamp > cutoff_time and 
                    metric.category != ErrorCategory.VALIDATION)
            )
            return count >= rule.threshold
        
        elif alert_type == AlertType.AUTHENTICATION_ATTACK:
            # Count authentication errors by IP
            ip_counts = defaultdict(int)
            for metric in self.error_metrics:
                if (metric.timestamp > cutoff_time and 
                    metric.category == ErrorCategory.AUTHENTICATION and
                    metric.ip_address):
                    ip_counts[metric.ip_address] += 1
            
            return any(count >= rule.threshold for count in ip_counts.values())
        
        elif alert_type == AlertType.SERVICE_DEGRADATION:
            # Count service unavailable errors
            count = sum(
                1 for metric in self.error_metrics
                if (metric.timestamp > cutoff_time and 
                    metric.category == ErrorCategory.SERVICE_UNAVAILABLE)
            )
            return count >= rule.threshold
        
        elif alert_type == AlertType.CRITICAL_ERROR:
            # Any critical error triggers this
            count = sum(
                1 for metric in self.error_metrics
                if (metric.timestamp > cutoff_time and 
                    metric.severity == ErrorSeverity.CRITICAL)
            )
            return count >= rule.threshold
        
        elif alert_type == AlertType.PERFORMANCE_DEGRADATION:
            # Check response times (would need to be recorded separately)
            threshold_ms = rule.conditions.get("response_time_threshold", 5000)
            slow_requests = sum(
                1 for response_time in self.response_times
                if response_time > threshold_ms
            )
            return slow_requests >= rule.threshold
        
        return False
    
    async def _trigger_alert(
        self, 
        alert_type: AlertType, 
        rule: AlertRule, 
        triggering_metric: ErrorMetric
    ) -> None:
        """Trigger an alert"""
        
        alert_id = str(uuid.uuid4())
        
        # Get related metrics for context
        time_window = timedelta(minutes=rule.time_window_minutes)
        cutoff_time = datetime.utcnow() - time_window
        
        related_metrics = [
            metric for metric in self.error_metrics
            if (metric.timestamp > cutoff_time and 
                self._matches_conditions(metric, rule))
        ]
        
        # Create alert
        alert = Alert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=rule.severity,
            title=self._generate_alert_title(alert_type, len(related_metrics)),
            message=self._generate_alert_message(alert_type, rule, related_metrics),
            timestamp=datetime.utcnow(),
            triggered_by=related_metrics,
            metadata={
                "rule": asdict(rule),
                "triggering_metric": asdict(triggering_metric),
                "metric_count": len(related_metrics)
            }
        )
        
        # Store alert
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        self.last_alert_times[alert_type] = alert.timestamp
        
        # Log alert
        logger.critical(
            f"ALERT TRIGGERED: {alert.title}",
            extra={
                "alert_id": alert_id,
                "alert_type": alert_type.value,
                "severity": rule.severity.value,
                "metric_count": len(related_metrics),
                "message": alert.message
            }
        )
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                await asyncio.create_task(callback(alert))
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def _generate_alert_title(self, alert_type: AlertType, metric_count: int) -> str:
        """Generate alert title based on type and context"""
        titles = {
            AlertType.ERROR_SPIKE: f"Error Spike Detected ({metric_count} errors)",
            AlertType.AUTHENTICATION_ATTACK: f"Potential Authentication Attack ({metric_count} failures)",
            AlertType.SERVICE_DEGRADATION: f"Service Degradation Detected ({metric_count} errors)",
            AlertType.CRITICAL_ERROR: f"Critical Error Occurred",
            AlertType.PERFORMANCE_DEGRADATION: f"Performance Degradation ({metric_count} slow requests)",
            AlertType.SECURITY_INCIDENT: f"Security Incident Detected"
        }
        return titles.get(alert_type, f"Alert: {alert_type.value}")
    
    def _generate_alert_message(
        self, 
        alert_type: AlertType, 
        rule: AlertRule, 
        metrics: List[ErrorMetric]
    ) -> str:
        """Generate detailed alert message"""
        
        base_message = f"Alert triggered: {rule.threshold} occurrences in {rule.time_window_minutes} minutes."
        
        if alert_type == AlertType.AUTHENTICATION_ATTACK:
            # Group by IP address
            ip_counts = defaultdict(int)
            for metric in metrics:
                if metric.ip_address:
                    ip_counts[metric.ip_address] += 1
            
            top_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            ip_info = ", ".join([f"{ip}: {count}" for ip, count in top_ips])
            return f"{base_message} Top attacking IPs: {ip_info}"
        
        elif alert_type == AlertType.SERVICE_DEGRADATION:
            # Group by service/endpoint
            endpoint_counts = defaultdict(int)
            for metric in metrics:
                if metric.endpoint:
                    endpoint_counts[metric.endpoint] += 1
            
            top_endpoints = sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            endpoint_info = ", ".join([f"{ep}: {count}" for ep, count in top_endpoints])
            return f"{base_message} Affected endpoints: {endpoint_info}"
        
        elif alert_type == AlertType.ERROR_SPIKE:
            # Group by error type
            error_counts = defaultdict(int)
            for metric in metrics:
                error_counts[metric.error_type] += 1
            
            top_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            error_info = ", ".join([f"{error}: {count}" for error, count in top_errors])
            return f"{base_message} Top error types: {error_info}"
        
        return base_message
    
    def add_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        """Add callback function to be called when alerts are triggered"""
        self.alert_callbacks.append(callback)
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an active alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            self.active_alerts[alert_id].metadata["acknowledged_by"] = acknowledged_by
            self.active_alerts[alert_id].metadata["acknowledged_at"] = datetime.utcnow().isoformat()
            
            logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
            return True
        return False
    
    def resolve_alert(self, alert_id: str, resolved_by: str, resolution_note: str = "") -> bool:
        """Resolve an active alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.metadata["resolved_by"] = resolved_by
            alert.metadata["resolved_at"] = datetime.utcnow().isoformat()
            alert.metadata["resolution_note"] = resolution_note
            
            # Move to history and remove from active
            del self.active_alerts[alert_id]
            
            logger.info(f"Alert {alert_id} resolved by {resolved_by}: {resolution_note}")
            return True
        return False
    
    def get_error_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent_metrics = [
            metric for metric in self.error_metrics
            if metric.timestamp > cutoff_time
        ]
        
        # Group by various dimensions
        by_category = defaultdict(int)
        by_severity = defaultdict(int)
        by_hour = defaultdict(int)
        by_endpoint = defaultdict(int)
        
        for metric in recent_metrics:
            by_category[metric.category.value] += 1
            by_severity[metric.severity.value] += 1
            by_endpoint[metric.endpoint or "unknown"] += 1
            
            hour_key = metric.timestamp.strftime("%Y-%m-%d %H:00")
            by_hour[hour_key] += 1
        
        return {
            "total_errors": len(recent_metrics),
            "time_period_hours": hours,
            "by_category": dict(by_category),
            "by_severity": dict(by_severity),
            "by_hour": dict(by_hour),
            "by_endpoint": dict(sorted(by_endpoint.items(), key=lambda x: x[1], reverse=True)[:10]),
            "active_alerts": len(self.active_alerts),
            "total_alerts_today": len([
                alert for alert in self.alert_history
                if alert.timestamp > datetime.utcnow() - timedelta(days=1)
            ])
        }
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        return [asdict(alert) for alert in self.active_alerts.values()]
    
    def get_alert_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alert history for specified time period"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent_alerts = [
            alert for alert in self.alert_history
            if alert.timestamp > cutoff_time
        ]
        
        return [asdict(alert) for alert in recent_alerts]
    
    def update_alert_rule(self, alert_type: AlertType, **kwargs) -> bool:
        """Update an alert rule configuration"""
        if alert_type in self.alert_rules:
            rule = self.alert_rules[alert_type]
            
            for key, value in kwargs.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
            
            logger.info(f"Alert rule updated: {alert_type.value}")
            return True
        return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of monitoring service"""
        return {
            "status": "healthy",
            "metrics_count": len(self.error_metrics),
            "active_alerts": len(self.active_alerts),
            "alert_rules": len(self.alert_rules),
            "last_metric_time": self.error_metrics[-1].timestamp.isoformat() if self.error_metrics else None,
            "memory_usage": {
                "error_metrics": len(self.error_metrics),
                "alert_history": len(self.alert_history),
                "error_patterns": len(self.error_patterns),
                "ip_patterns": len(self.ip_patterns)
            }
        }


# Global monitoring service instance
error_monitoring_service = ErrorMonitoringService()


# Integration functions for easy use
async def record_error_metric(
    error_type: str,
    category: ErrorCategory,
    severity: ErrorSeverity,
    context: Optional[ErrorContext] = None,
    details: Optional[Dict[str, Any]] = None
) -> str:
    """Convenience function to record error metrics"""
    return await error_monitoring_service.record_error(
        error_type, category, severity, context, details
    )


async def setup_monitoring_alerts():
    """Set up default monitoring alert callbacks"""
    
    async def log_alert_callback(alert: Alert):
        """Log alerts to monitoring systems"""
        logger.critical(
            f"MONITORING ALERT: {alert.title}",
            extra={
                "alert_id": alert.alert_id,
                "alert_type": alert.alert_type.value,
                "severity": alert.severity.value,
                "message": alert.message,
                "metric_count": len(alert.triggered_by)
            }
        )
        
        # In production, send to external monitoring systems
        # await send_to_slack(alert)
        # await send_to_pagerduty(alert)
        # await send_to_email(alert)
    
    error_monitoring_service.add_alert_callback(log_alert_callback)