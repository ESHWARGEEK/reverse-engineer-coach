#!/usr/bin/env python3
"""
Post-Deployment Monitoring System
Monitors system performance, user adoption, and identifies issues after deployment
"""

import json
import time
import requests
import psutil
import sqlite3
import docker
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import os
import subprocess
import threading
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/deployment-monitoring.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class HealthCheckResult:
    service: str
    status: str
    response_time: float
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class SystemMetrics:
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: Dict[str, int]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class DeploymentMonitor:
    def __init__(self, config_file: str = "monitoring-config.json"):
        self.config = self.load_config(config_file)
        self.db_path = "monitoring.db"
        self.docker_client = None
        self.monitoring_active = False
        self.init_database()
        self.init_docker_client()
        
    def load_config(self, config_file: str) -> Dict:
        """Load monitoring configuration"""
        default_config = {
            "api_base_url": "http://localhost:8000",
            "frontend_url": "http://localhost:3000",
            "health_check_interval": 30,
            "metrics_collection_interval": 60,
            "alert_thresholds": {
                "response_time_ms": 2000,
                "error_rate_percent": 5,
                "cpu_percent": 80,
                "memory_percent": 85,
                "disk_percent": 90
            },
            "services": [
                {"name": "api", "url": "/health", "timeout": 10},
                {"name": "frontend", "url": "/", "timeout": 10},
                {"name": "auth", "url": "/api/auth/health", "timeout": 10},
                {"name": "discovery", "url": "/api/discover/health", "timeout": 10}
            ],
            "docker_services": [
                "reverse-coach-backend-prod",
                "reverse-coach-frontend-prod",
                "reverse-coach-postgres-prod",
                "reverse-coach-redis-prod"
            ]
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
        except Exception as e:
            logger.warning(f"Could not load config file {config_file}: {e}")
            
        return default_config
    
    def init_database(self):
        """Initialize monitoring database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Health checks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT NOT NULL,
                status TEXT NOT NULL,
                response_time REAL,
                error_message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # System metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cpu_percent REAL,
                memory_percent REAL,
                disk_percent REAL,
                network_bytes_sent INTEGER,
                network_bytes_recv INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User adoption metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_adoption (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                resolved BOOLEAN DEFAULT FALSE,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Monitoring database initialized")
    
    def init_docker_client(self):
        """Initialize Docker client"""
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized")
        except Exception as e:
            logger.warning(f"Could not initialize Docker client: {e}")
    
    def perform_health_check(self, service: Dict) -> HealthCheckResult:
        """Perform health check for a service"""
        start_time = time.time()
        
        try:
            url = f"{self.config['api_base_url']}{service['url']}"
            response = requests.get(url, timeout=service['timeout'])
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            if response.status_code == 200:
                return HealthCheckResult(
                    service=service['name'],
                    status='healthy',
                    response_time=response_time
                )
            else:
                return HealthCheckResult(
                    service=service['name'],
                    status='unhealthy',
                    response_time=response_time,
                    error_message=f"HTTP {response.status_code}"
                )
                
        except requests.exceptions.Timeout:
            return HealthCheckResult(
                service=service['name'],
                status='timeout',
                response_time=(time.time() - start_time) * 1000,
                error_message="Request timeout"
            )
        except Exception as e:
            return HealthCheckResult(
                service=service['name'],
                status='error',
                response_time=(time.time() - start_time) * 1000,
                error_message=str(e)
            )
    
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Network I/O
            network = psutil.net_io_counters()
            network_io = {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv
            }
            
            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_percent=disk_percent,
                network_io=network_io
            )
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics(0, 0, 0, {'bytes_sent': 0, 'bytes_recv': 0})
    
    def check_docker_services(self) -> List[Dict]:
        """Check Docker service status"""
        service_status = []
        
        if not self.docker_client:
            return service_status
        
        try:
            for service_name in self.config['docker_services']:
                try:
                    container = self.docker_client.containers.get(service_name)
                    status = {
                        'name': service_name,
                        'status': container.status,
                        'health': getattr(container.attrs['State'], 'Health', {}).get('Status', 'unknown'),
                        'created': container.attrs['Created'],
                        'started': container.attrs['State'].get('StartedAt'),
                        'cpu_usage': self.get_container_stats(container)
                    }
                    service_status.append(status)
                    
                except docker.errors.NotFound:
                    service_status.append({
                        'name': service_name,
                        'status': 'not_found',
                        'health': 'unknown',
                        'error': 'Container not found'
                    })
                    
        except Exception as e:
            logger.error(f"Error checking Docker services: {e}")
            
        return service_status
    
    def get_container_stats(self, container) -> Dict:
        """Get container resource usage statistics"""
        try:
            stats = container.stats(stream=False)
            
            # Calculate CPU usage percentage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            
            cpu_percent = 0
            if system_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * 100
            
            # Memory usage
            memory_usage = stats['memory_stats']['usage']
            memory_limit = stats['memory_stats']['limit']
            memory_percent = (memory_usage / memory_limit) * 100
            
            return {
                'cpu_percent': round(cpu_percent, 2),
                'memory_percent': round(memory_percent, 2),
                'memory_usage_mb': round(memory_usage / 1024 / 1024, 2),
                'memory_limit_mb': round(memory_limit / 1024 / 1024, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting container stats: {e}")
            return {}
    
    def collect_user_adoption_metrics(self) -> Dict:
        """Collect user adoption and usage metrics"""
        metrics = {}
        
        try:
            # Get user registration count
            response = requests.get(
                f"{self.config['api_base_url']}/api/monitoring/user-metrics",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                metrics.update(data)
                
        except Exception as e:
            logger.error(f"Error collecting user adoption metrics: {e}")
        
        # Add timestamp
        metrics['timestamp'] = datetime.now().isoformat()
        
        return metrics
    
    def store_health_check(self, result: HealthCheckResult):
        """Store health check result in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO health_checks (service, status, response_time, error_message)
                VALUES (?, ?, ?, ?)
            ''', (result.service, result.status, result.response_time, result.error_message))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing health check: {e}")
    
    def store_system_metrics(self, metrics: SystemMetrics):
        """Store system metrics in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO system_metrics (
                    cpu_percent, memory_percent, disk_percent, 
                    network_bytes_sent, network_bytes_recv
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                metrics.cpu_percent, metrics.memory_percent, metrics.disk_percent,
                metrics.network_io['bytes_sent'], metrics.network_io['bytes_recv']
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing system metrics: {e}")
    
    def store_user_adoption_metrics(self, metrics: Dict):
        """Store user adoption metrics in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for metric_name, metric_value in metrics.items():
                if metric_name != 'timestamp' and isinstance(metric_value, (int, float)):
                    cursor.execute('''
                        INSERT INTO user_adoption (metric_name, metric_value)
                        VALUES (?, ?)
                    ''', (metric_name, metric_value))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing user adoption metrics: {e}")
    
    def check_alert_conditions(self, health_results: List[HealthCheckResult], 
                             system_metrics: SystemMetrics) -> List[Dict]:
        """Check for alert conditions"""
        alerts = []
        thresholds = self.config['alert_thresholds']
        
        # Check health check alerts
        for result in health_results:
            if result.status != 'healthy':
                alerts.append({
                    'type': 'service_unhealthy',
                    'severity': 'critical' if result.status == 'error' else 'warning',
                    'message': f"Service {result.service} is {result.status}: {result.error_message or 'No details'}"
                })
            elif result.response_time > thresholds['response_time_ms']:
                alerts.append({
                    'type': 'slow_response',
                    'severity': 'warning',
                    'message': f"Service {result.service} response time is {result.response_time:.0f}ms (threshold: {thresholds['response_time_ms']}ms)"
                })
        
        # Check system resource alerts
        if system_metrics.cpu_percent > thresholds['cpu_percent']:
            alerts.append({
                'type': 'high_cpu',
                'severity': 'warning',
                'message': f"High CPU usage: {system_metrics.cpu_percent:.1f}% (threshold: {thresholds['cpu_percent']}%)"
            })
        
        if system_metrics.memory_percent > thresholds['memory_percent']:
            alerts.append({
                'type': 'high_memory',
                'severity': 'warning',
                'message': f"High memory usage: {system_metrics.memory_percent:.1f}% (threshold: {thresholds['memory_percent']}%)"
            })
        
        if system_metrics.disk_percent > thresholds['disk_percent']:
            alerts.append({
                'type': 'high_disk',
                'severity': 'critical',
                'message': f"High disk usage: {system_metrics.disk_percent:.1f}% (threshold: {thresholds['disk_percent']}%)"
            })
        
        return alerts
    
    def store_alert(self, alert: Dict):
        """Store alert in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO alerts (alert_type, severity, message)
                VALUES (?, ?, ?)
            ''', (alert['type'], alert['severity'], alert['message']))
            
            conn.commit()
            conn.close()
            
            # Log alert
            severity_level = logging.CRITICAL if alert['severity'] == 'critical' else logging.WARNING
            logger.log(severity_level, f"ALERT: {alert['message']}")
            
        except Exception as e:
            logger.error(f"Error storing alert: {e}")
    
    def send_alert_notification(self, alert: Dict):
        """Send alert notification"""
        try:
            # Email notification
            if os.getenv('ALERT_EMAIL'):
                self.send_email_alert(alert)
            
            # Slack notification
            if os.getenv('SLACK_WEBHOOK_URL'):
                self.send_slack_alert(alert)
                
        except Exception as e:
            logger.error(f"Error sending alert notification: {e}")
    
    def send_slack_alert(self, alert: Dict):
        """Send alert to Slack"""
        try:
            webhook_url = os.getenv('SLACK_WEBHOOK_URL')
            color = "danger" if alert['severity'] == 'critical' else "warning"
            
            payload = {
                "text": f"🚨 Deployment Alert - {alert['severity'].upper()}",
                "attachments": [
                    {
                        "color": color,
                        "fields": [
                            {
                                "title": "Alert Type",
                                "value": alert['type'],
                                "short": True
                            },
                            {
                                "title": "Severity",
                                "value": alert['severity'],
                                "short": True
                            },
                            {
                                "title": "Message",
                                "value": alert['message'],
                                "short": False
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            
        except Exception as e:
            logger.error(f"Error sending Slack alert: {e}")
    
    def generate_monitoring_report(self, hours: int = 24) -> str:
        """Generate monitoring report for the last N hours"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since_time = datetime.now() - timedelta(hours=hours)
            
            # Health check summary
            cursor.execute('''
                SELECT service, 
                       COUNT(*) as total_checks,
                       SUM(CASE WHEN status = 'healthy' THEN 1 ELSE 0 END) as healthy_checks,
                       AVG(response_time) as avg_response_time
                FROM health_checks 
                WHERE timestamp >= ?
                GROUP BY service
            ''', (since_time,))
            
            health_summary = cursor.fetchall()
            
            # System metrics summary
            cursor.execute('''
                SELECT AVG(cpu_percent) as avg_cpu,
                       MAX(cpu_percent) as max_cpu,
                       AVG(memory_percent) as avg_memory,
                       MAX(memory_percent) as max_memory,
                       AVG(disk_percent) as avg_disk,
                       MAX(disk_percent) as max_disk
                FROM system_metrics 
                WHERE timestamp >= ?
            ''', (since_time,))
            
            system_summary = cursor.fetchone()
            
            # Recent alerts
            cursor.execute('''
                SELECT alert_type, severity, message, timestamp
                FROM alerts 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 10
            ''', (since_time,))
            
            recent_alerts = cursor.fetchall()
            
            conn.close()
            
            # Generate report
            report = f"""
# Deployment Monitoring Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Period: Last {hours} hours

## Service Health Summary
"""
            
            for service, total, healthy, avg_time in health_summary:
                uptime = (healthy / total) * 100 if total > 0 else 0
                report += f"- {service}: {uptime:.1f}% uptime, {avg_time:.0f}ms avg response time\n"
            
            if system_summary:
                report += f"""

## System Performance Summary
- CPU: {system_summary[0]:.1f}% avg, {system_summary[1]:.1f}% max
- Memory: {system_summary[2]:.1f}% avg, {system_summary[3]:.1f}% max  
- Disk: {system_summary[4]:.1f}% avg, {system_summary[5]:.1f}% max
"""
            
            if recent_alerts:
                report += "\n## Recent Alerts\n"
                for alert_type, severity, message, timestamp in recent_alerts:
                    report += f"- [{severity.upper()}] {message} ({timestamp})\n"
            else:
                report += "\n## Recent Alerts\nNo alerts in the monitoring period.\n"
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating monitoring report: {e}")
            return "Error generating report"
    
    def start_monitoring(self, duration_minutes: int = 60):
        """Start continuous monitoring for specified duration"""
        logger.info(f"Starting deployment monitoring for {duration_minutes} minutes...")
        
        self.monitoring_active = True
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        
        health_check_interval = self.config['health_check_interval']
        metrics_interval = self.config['metrics_collection_interval']
        
        last_health_check = datetime.min
        last_metrics_collection = datetime.min
        
        try:
            while datetime.now() < end_time and self.monitoring_active:
                current_time = datetime.now()
                
                # Perform health checks
                if (current_time - last_health_check).total_seconds() >= health_check_interval:
                    health_results = []
                    
                    for service in self.config['services']:
                        result = self.perform_health_check(service)
                        health_results.append(result)
                        self.store_health_check(result)
                        
                        logger.info(f"Health check - {result.service}: {result.status} ({result.response_time:.0f}ms)")
                    
                    last_health_check = current_time
                
                # Collect system metrics
                if (current_time - last_metrics_collection).total_seconds() >= metrics_interval:
                    system_metrics = self.collect_system_metrics()
                    self.store_system_metrics(system_metrics)
                    
                    logger.info(f"System metrics - CPU: {system_metrics.cpu_percent:.1f}%, "
                              f"Memory: {system_metrics.memory_percent:.1f}%, "
                              f"Disk: {system_metrics.disk_percent:.1f}%")
                    
                    # Collect user adoption metrics
                    user_metrics = self.collect_user_adoption_metrics()
                    if user_metrics:
                        self.store_user_adoption_metrics(user_metrics)
                    
                    # Check for alerts
                    if 'health_results' in locals():
                        alerts = self.check_alert_conditions(health_results, system_metrics)
                        for alert in alerts:
                            self.store_alert(alert)
                            self.send_alert_notification(alert)
                    
                    last_metrics_collection = current_time
                
                time.sleep(10)  # Check every 10 seconds
                
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Error during monitoring: {e}")
        finally:
            self.monitoring_active = False
            logger.info("Deployment monitoring completed")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring_active = False

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deployment Monitoring System')
    parser.add_argument('--action', choices=['monitor', 'report', 'status'], default='monitor',
                       help='Action to perform')
    parser.add_argument('--duration', type=int, default=60,
                       help='Monitoring duration in minutes')
    parser.add_argument('--hours', type=int, default=24,
                       help='Hours to include in report')
    parser.add_argument('--config', type=str, default='monitoring-config.json',
                       help='Configuration file path')
    
    args = parser.parse_args()
    
    monitor = DeploymentMonitor(args.config)
    
    if args.action == 'monitor':
        monitor.start_monitoring(args.duration)
        
    elif args.action == 'report':
        report = monitor.generate_monitoring_report(args.hours)
        print(report)
        
        # Save report to file
        report_file = f"reports/monitoring-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        os.makedirs('reports', exist_ok=True)
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"\nReport saved to: {report_file}")
        
    elif args.action == 'status':
        # Quick status check
        health_results = []
        for service in monitor.config['services']:
            result = monitor.perform_health_check(service)
            health_results.append(result)
            
        system_metrics = monitor.collect_system_metrics()
        docker_status = monitor.check_docker_services()
        
        print("=== Current System Status ===")
        print("\nService Health:")
        for result in health_results:
            status_icon = "✅" if result.status == 'healthy' else "❌"
            print(f"{status_icon} {result.service}: {result.status} ({result.response_time:.0f}ms)")
        
        print(f"\nSystem Resources:")
        print(f"CPU: {system_metrics.cpu_percent:.1f}%")
        print(f"Memory: {system_metrics.memory_percent:.1f}%")
        print(f"Disk: {system_metrics.disk_percent:.1f}%")
        
        print(f"\nDocker Services:")
        for service in docker_status:
            status_icon = "✅" if service['status'] == 'running' else "❌"
            print(f"{status_icon} {service['name']}: {service['status']}")

if __name__ == "__main__":
    main()