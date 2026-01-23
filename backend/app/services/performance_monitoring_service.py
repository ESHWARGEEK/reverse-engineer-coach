"""
Performance Monitoring Service

Monitors API performance, tracks metrics, and provides performance analytics.
"""

import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from contextlib import asynccontextmanager
import json
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime, Float, Integer, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    endpoint: str
    method: str
    response_time: float
    status_code: int
    timestamp: datetime
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    error_message: Optional[str] = None
    request_size: Optional[int] = None
    response_size: Optional[int] = None

@dataclass
class EndpointStats:
    """Endpoint performance statistics"""
    endpoint: str
    total_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    error_rate: float
    requests_per_minute: float

class PerformanceLog(Base):
    """Database model for performance logs"""
    __tablename__ = "performance_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String(255), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    response_time = Column(Float, nullable=False, index=True)
    status_code = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    request_size = Column(Integer, nullable=True)
    response_size = Column(Integer, nullable=True)

class PerformanceMonitoringService:
    """Service for monitoring API performance and generating metrics"""
    
    def __init__(self):
        self.logger = logging.getLogger("performance_monitoring")
        
        # In-memory metrics for real-time monitoring
        self.response_times = defaultdict(lambda: deque(maxlen=1000))
        self.request_counts = defaultdict(lambda: deque(maxlen=100))
        self.error_counts = defaultdict(int)
        
        # Performance thresholds
        self.thresholds = {
            "slow_request_threshold": 2.0,  # seconds
            "very_slow_request_threshold": 5.0,  # seconds
            "high_error_rate_threshold": 0.05,  # 5%
            "discovery_endpoint_threshold": 3.0,  # seconds for discovery endpoints
        }
        
        # Discovery endpoint patterns
        self.discovery_endpoints = [
            "/api/discover/repositories",
            "/api/discover/concepts",
            "/api/repositories/analyze",
            "/api/repositories/search"
        ]
    
    @asynccontextmanager
    async def monitor_request(
        self,
        endpoint: str,
        method: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Context manager to monitor request performance"""
        start_time = time.time()
        error_message = None
        status_code = 200
        
        try:
            yield
        except Exception as e:
            error_message = str(e)
            status_code = 500
            raise
        finally:
            end_time = time.time()
            response_time = end_time - start_time
            
            # Create performance metric
            metric = PerformanceMetric(
                endpoint=endpoint,
                method=method,
                response_time=response_time,
                status_code=status_code,
                timestamp=datetime.utcnow(),
                user_id=user_id,
                ip_address=ip_address,
                error_message=error_message
            )
            
            # Log the metric
            await self.log_performance_metric(metric)
    
    async def log_performance_metric(self, metric: PerformanceMetric, db: Optional[Session] = None):
        """Log a performance metric"""
        
        # Update in-memory metrics
        self._update_in_memory_metrics(metric)
        
        # Log to structured logger
        self._log_to_structured_logger(metric)
        
        # Store in database if available
        if db:
            await self._store_in_database(metric, db)
        
        # Check for performance alerts
        await self._check_performance_alerts(metric)
    
    def _update_in_memory_metrics(self, metric: PerformanceMetric):
        """Update in-memory performance metrics"""
        endpoint_key = f"{metric.method}:{metric.endpoint}"
        
        # Track response times
        self.response_times[endpoint_key].append(metric.response_time)
        
        # Track request counts with timestamps
        self.request_counts[endpoint_key].append(metric.timestamp)
        
        # Track error counts
        if metric.status_code >= 400:
            self.error_counts[endpoint_key] += 1
    
    def _log_to_structured_logger(self, metric: PerformanceMetric):
        """Log metric to structured logger"""
        log_data = {
            "endpoint": metric.endpoint,
            "method": metric.method,
            "response_time": metric.response_time,
            "status_code": metric.status_code,
            "timestamp": metric.timestamp.isoformat(),
            "user_id": metric.user_id,
            "ip_address": metric.ip_address
        }
        
        # Determine log level based on performance
        if metric.response_time > self.thresholds["very_slow_request_threshold"]:
            self.logger.warning(f"Very slow request: {metric.endpoint}", extra=log_data)
        elif metric.response_time > self.thresholds["slow_request_threshold"]:
            self.logger.info(f"Slow request: {metric.endpoint}", extra=log_data)
        elif metric.status_code >= 500:
            self.logger.error(f"Server error: {metric.endpoint}", extra=log_data)
        elif metric.status_code >= 400:
            self.logger.warning(f"Client error: {metric.endpoint}", extra=log_data)
        else:
            self.logger.debug(f"Request completed: {metric.endpoint}", extra=log_data)
    
    async def _store_in_database(self, metric: PerformanceMetric, db: Session):
        """Store performance metric in database"""
        try:
            db_metric = PerformanceLog(
                endpoint=metric.endpoint,
                method=metric.method,
                response_time=metric.response_time,
                status_code=metric.status_code,
                timestamp=metric.timestamp,
                user_id=metric.user_id,
                ip_address=metric.ip_address,
                error_message=metric.error_message,
                request_size=metric.request_size,
                response_size=metric.response_size
            )
            
            db.add(db_metric)
            db.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to store performance metric in database: {e}")
            db.rollback()
    
    async def _check_performance_alerts(self, metric: PerformanceMetric):
        """Check if metric should trigger performance alerts"""
        
        # Alert on very slow requests
        if metric.response_time > self.thresholds["very_slow_request_threshold"]:
            await self._send_performance_alert(
                "VERY_SLOW_REQUEST",
                f"Request to {metric.endpoint} took {metric.response_time:.2f}s",
                metric
            )
        
        # Special monitoring for discovery endpoints
        if any(pattern in metric.endpoint for pattern in self.discovery_endpoints):
            if metric.response_time > self.thresholds["discovery_endpoint_threshold"]:
                await self._send_performance_alert(
                    "SLOW_DISCOVERY_ENDPOINT",
                    f"Discovery endpoint {metric.endpoint} took {metric.response_time:.2f}s",
                    metric
                )
        
        # Alert on server errors
        if metric.status_code >= 500:
            await self._send_performance_alert(
                "SERVER_ERROR",
                f"Server error on {metric.endpoint}: {metric.error_message}",
                metric
            )
    
    async def _send_performance_alert(self, alert_type: str, message: str, metric: PerformanceMetric):
        """Send performance alert"""
        alert_data = {
            "alert_type": alert_type,
            "message": message,
            "metric": asdict(metric),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.warning(f"Performance alert: {alert_type} - {message}", extra=alert_data)
        
        # TODO: Implement actual alerting system
        # This could integrate with monitoring services like:
        # - Prometheus/Grafana alerts
        # - DataDog alerts
        # - New Relic alerts
        # - Custom webhook notifications
    
    def get_endpoint_stats(self, endpoint: str, method: str = "GET") -> EndpointStats:
        """Get performance statistics for an endpoint"""
        endpoint_key = f"{method}:{endpoint}"
        
        response_times = list(self.response_times[endpoint_key])
        request_timestamps = list(self.request_counts[endpoint_key])
        
        if not response_times:
            return EndpointStats(
                endpoint=endpoint,
                total_requests=0,
                avg_response_time=0.0,
                min_response_time=0.0,
                max_response_time=0.0,
                p95_response_time=0.0,
                p99_response_time=0.0,
                error_rate=0.0,
                requests_per_minute=0.0
            )
        
        # Calculate statistics
        total_requests = len(response_times)
        avg_response_time = sum(response_times) / total_requests
        min_response_time = min(response_times)
        max_response_time = max(response_times)
        
        # Calculate percentiles
        sorted_times = sorted(response_times)
        p95_index = int(0.95 * len(sorted_times))
        p99_index = int(0.99 * len(sorted_times))
        p95_response_time = sorted_times[p95_index] if p95_index < len(sorted_times) else max_response_time
        p99_response_time = sorted_times[p99_index] if p99_index < len(sorted_times) else max_response_time
        
        # Calculate error rate
        error_count = self.error_counts.get(endpoint_key, 0)
        error_rate = error_count / total_requests if total_requests > 0 else 0.0
        
        # Calculate requests per minute
        now = datetime.utcnow()
        one_minute_ago = now - timedelta(minutes=1)
        recent_requests = [ts for ts in request_timestamps if ts >= one_minute_ago]
        requests_per_minute = len(recent_requests)
        
        return EndpointStats(
            endpoint=endpoint,
            total_requests=total_requests,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            error_rate=error_rate,
            requests_per_minute=requests_per_minute
        )
    
    async def get_discovery_performance_report(self, db: Session) -> Dict[str, Any]:
        """Get comprehensive performance report for discovery endpoints"""
        
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        
        report = {
            "timestamp": now.isoformat(),
            "period": "24h",
            "discovery_endpoints": {}
        }
        
        for endpoint in self.discovery_endpoints:
            # Get database statistics
            from sqlalchemy import func
            
            stats = db.query(
                func.count(PerformanceLog.id).label('total_requests'),
                func.avg(PerformanceLog.response_time).label('avg_response_time'),
                func.min(PerformanceLog.response_time).label('min_response_time'),
                func.max(PerformanceLog.response_time).label('max_response_time'),
                func.count().filter(PerformanceLog.status_code >= 400).label('error_count')
            ).filter(
                PerformanceLog.endpoint == endpoint,
                PerformanceLog.timestamp >= last_24h
            ).first()
            
            if stats and stats.total_requests > 0:
                error_rate = (stats.error_count / stats.total_requests) * 100
                
                report["discovery_endpoints"][endpoint] = {
                    "total_requests": stats.total_requests,
                    "avg_response_time": round(stats.avg_response_time, 3),
                    "min_response_time": round(stats.min_response_time, 3),
                    "max_response_time": round(stats.max_response_time, 3),
                    "error_rate": round(error_rate, 2),
                    "performance_grade": self._calculate_performance_grade(stats.avg_response_time, error_rate)
                }
            else:
                report["discovery_endpoints"][endpoint] = {
                    "total_requests": 0,
                    "avg_response_time": 0.0,
                    "min_response_time": 0.0,
                    "max_response_time": 0.0,
                    "error_rate": 0.0,
                    "performance_grade": "N/A"
                }
        
        return report
    
    def _calculate_performance_grade(self, avg_response_time: float, error_rate: float) -> str:
        """Calculate performance grade based on response time and error rate"""
        
        # Grade based on response time
        if avg_response_time <= 0.5:
            time_grade = "A"
        elif avg_response_time <= 1.0:
            time_grade = "B"
        elif avg_response_time <= 2.0:
            time_grade = "C"
        elif avg_response_time <= 5.0:
            time_grade = "D"
        else:
            time_grade = "F"
        
        # Grade based on error rate
        if error_rate <= 1.0:
            error_grade = "A"
        elif error_rate <= 2.0:
            error_grade = "B"
        elif error_rate <= 5.0:
            error_grade = "C"
        elif error_rate <= 10.0:
            error_grade = "D"
        else:
            error_grade = "F"
        
        # Return the worse of the two grades
        grades = ["A", "B", "C", "D", "F"]
        time_index = grades.index(time_grade)
        error_index = grades.index(error_grade)
        
        return grades[max(time_index, error_index)]
    
    async def get_performance_dashboard_data(self, db: Session) -> Dict[str, Any]:
        """Get data for performance monitoring dashboard"""
        
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        
        # Get overall statistics
        from sqlalchemy import func
        
        overall_stats = db.query(
            func.count(PerformanceLog.id).label('total_requests'),
            func.avg(PerformanceLog.response_time).label('avg_response_time'),
            func.count().filter(PerformanceLog.status_code >= 400).label('error_count'),
            func.count().filter(PerformanceLog.response_time > self.thresholds["slow_request_threshold"]).label('slow_requests')
        ).filter(
            PerformanceLog.timestamp >= last_24h
        ).first()
        
        # Get top slowest endpoints
        slowest_endpoints = db.query(
            PerformanceLog.endpoint,
            func.avg(PerformanceLog.response_time).label('avg_response_time'),
            func.count(PerformanceLog.id).label('request_count')
        ).filter(
            PerformanceLog.timestamp >= last_24h
        ).group_by(
            PerformanceLog.endpoint
        ).order_by(
            func.avg(PerformanceLog.response_time).desc()
        ).limit(10).all()
        
        # Get error-prone endpoints
        error_endpoints = db.query(
            PerformanceLog.endpoint,
            func.count(PerformanceLog.id).label('total_requests'),
            func.count().filter(PerformanceLog.status_code >= 400).label('error_count')
        ).filter(
            PerformanceLog.timestamp >= last_24h
        ).group_by(
            PerformanceLog.endpoint
        ).having(
            func.count().filter(PerformanceLog.status_code >= 400) > 0
        ).order_by(
            (func.count().filter(PerformanceLog.status_code >= 400) / func.count(PerformanceLog.id)).desc()
        ).limit(10).all()
        
        return {
            "summary": {
                "total_requests_24h": overall_stats.total_requests if overall_stats else 0,
                "avg_response_time_24h": round(overall_stats.avg_response_time, 3) if overall_stats and overall_stats.avg_response_time else 0,
                "error_count_24h": overall_stats.error_count if overall_stats else 0,
                "slow_requests_24h": overall_stats.slow_requests if overall_stats else 0,
                "error_rate_24h": round((overall_stats.error_count / overall_stats.total_requests) * 100, 2) if overall_stats and overall_stats.total_requests > 0 else 0
            },
            "slowest_endpoints": [
                {
                    "endpoint": ep.endpoint,
                    "avg_response_time": round(ep.avg_response_time, 3),
                    "request_count": ep.request_count
                }
                for ep in slowest_endpoints
            ],
            "error_prone_endpoints": [
                {
                    "endpoint": ep.endpoint,
                    "total_requests": ep.total_requests,
                    "error_count": ep.error_count,
                    "error_rate": round((ep.error_count / ep.total_requests) * 100, 2)
                }
                for ep in error_endpoints
            ],
            "timestamp": now.isoformat()
        }

# Global instance
performance_monitoring_service = PerformanceMonitoringService()