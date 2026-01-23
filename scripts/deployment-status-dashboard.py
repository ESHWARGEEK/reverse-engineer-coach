#!/usr/bin/env python3
"""
Deployment Status Dashboard
Real-time dashboard for monitoring deployment status and system health
"""

import json
import time
import requests
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import os
import threading
from flask import Flask, render_template_string, jsonify
import psutil
import docker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class DeploymentStatusDashboard:
    def __init__(self):
        self.db_path = "monitoring.db"
        self.docker_client = None
        self.init_docker_client()
        
    def init_docker_client(self):
        """Initialize Docker client"""
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.warning(f"Could not initialize Docker client: {e}")
    
    def get_system_status(self) -> Dict:
        """Get current system status"""
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network stats
            network = psutil.net_io_counters()
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_gb': round(memory.used / (1024**3), 2),
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'disk_percent': disk.percent,
                'disk_used_gb': round(disk.used / (1024**3), 2),
                'disk_total_gb': round(disk.total / (1024**3), 2),
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {}
    
    def get_service_health(self) -> List[Dict]:
        """Get health status of all services"""
        services = [
            {'name': 'API', 'url': 'http://localhost:8000/health'},
            {'name': 'Frontend', 'url': 'http://localhost:3000'},
            {'name': 'Auth API', 'url': 'http://localhost:8000/api/auth/health'},
            {'name': 'Discovery API', 'url': 'http://localhost:8000/api/discover/health'}
        ]
        
        health_status = []
        
        for service in services:
            try:
                start_time = time.time()
                response = requests.get(service['url'], timeout=5)
                response_time = (time.time() - start_time) * 1000
                
                status = {
                    'name': service['name'],
                    'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                    'response_time': round(response_time, 2),
                    'status_code': response.status_code,
                    'timestamp': datetime.now().isoformat()
                }
                
            except requests.exceptions.Timeout:
                status = {
                    'name': service['name'],
                    'status': 'timeout',
                    'response_time': 5000,
                    'error': 'Request timeout',
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                status = {
                    'name': service['name'],
                    'status': 'error',
                    'response_time': 0,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
            
            health_status.append(status)
        
        return health_status
    
    def get_docker_status(self) -> List[Dict]:
        """Get Docker container status"""
        if not self.docker_client:
            return []
        
        containers = []
        container_names = [
            'reverse-coach-backend-prod',
            'reverse-coach-frontend-prod',
            'reverse-coach-postgres-prod',
            'reverse-coach-redis-prod',
            'reverse-coach-nginx-prod'
        ]
        
        for name in container_names:
            try:
                container = self.docker_client.containers.get(name)
                
                # Get container stats
                stats = container.stats(stream=False)
                
                # Calculate CPU usage
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
                
                container_info = {
                    'name': name,
                    'status': container.status,
                    'health': getattr(container.attrs['State'], 'Health', {}).get('Status', 'unknown'),
                    'created': container.attrs['Created'],
                    'started': container.attrs['State'].get('StartedAt'),
                    'cpu_percent': round(cpu_percent, 2),
                    'memory_percent': round(memory_percent, 2),
                    'memory_usage_mb': round(memory_usage / (1024**2), 2),
                    'ports': container.attrs['NetworkSettings']['Ports']
                }
                
            except docker.errors.NotFound:
                container_info = {
                    'name': name,
                    'status': 'not_found',
                    'health': 'unknown',
                    'error': 'Container not found'
                }
            except Exception as e:
                container_info = {
                    'name': name,
                    'status': 'error',
                    'health': 'unknown',
                    'error': str(e)
                }
            
            containers.append(container_info)
        
        return containers
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """Get recent alerts from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since_time = datetime.now() - timedelta(hours=hours)
            
            cursor.execute('''
                SELECT alert_type, severity, message, timestamp, resolved
                FROM alerts 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 20
            ''', (since_time,))
            
            alerts = []
            for row in cursor.fetchall():
                alerts.append({
                    'type': row[0],
                    'severity': row[1],
                    'message': row[2],
                    'timestamp': row[3],
                    'resolved': bool(row[4])
                })
            
            conn.close()
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting recent alerts: {e}")
            return []
    
    def get_performance_metrics(self, hours: int = 24) -> Dict:
        """Get performance metrics from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since_time = datetime.now() - timedelta(hours=hours)
            
            # Health check metrics
            cursor.execute('''
                SELECT service, 
                       COUNT(*) as total_checks,
                       SUM(CASE WHEN status = 'healthy' THEN 1 ELSE 0 END) as healthy_checks,
                       AVG(response_time) as avg_response_time,
                       MIN(response_time) as min_response_time,
                       MAX(response_time) as max_response_time
                FROM health_checks 
                WHERE timestamp >= ?
                GROUP BY service
            ''', (since_time,))
            
            service_metrics = {}
            for row in cursor.fetchall():
                service_metrics[row[0]] = {
                    'total_checks': row[1],
                    'healthy_checks': row[2],
                    'uptime_percent': round((row[2] / row[1]) * 100, 2) if row[1] > 0 else 0,
                    'avg_response_time': round(row[3], 2) if row[3] else 0,
                    'min_response_time': round(row[4], 2) if row[4] else 0,
                    'max_response_time': round(row[5], 2) if row[5] else 0
                }
            
            # System metrics over time
            cursor.execute('''
                SELECT 
                    datetime(timestamp, 'localtime') as time,
                    cpu_percent,
                    memory_percent,
                    disk_percent
                FROM system_metrics 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 100
            ''', (since_time,))
            
            system_history = []
            for row in cursor.fetchall():
                system_history.append({
                    'timestamp': row[0],
                    'cpu_percent': row[1],
                    'memory_percent': row[2],
                    'disk_percent': row[3]
                })
            
            conn.close()
            
            return {
                'service_metrics': service_metrics,
                'system_history': system_history
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {'service_metrics': {}, 'system_history': []}
    
    def get_user_adoption_stats(self) -> Dict:
        """Get user adoption statistics"""
        try:
            # Try to get stats from the API
            response = requests.get('http://localhost:8000/api/monitoring/user-stats', timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Error getting user adoption stats: {e}")
        
        return {
            'total_users': 0,
            'active_users_24h': 0,
            'new_registrations_24h': 0,
            'total_projects': 0,
            'active_projects_24h': 0
        }

# Flask routes
dashboard = DeploymentStatusDashboard()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/status')
def api_status():
    """API endpoint for current status"""
    return jsonify({
        'system': dashboard.get_system_status(),
        'services': dashboard.get_service_health(),
        'containers': dashboard.get_docker_status(),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/alerts')
def api_alerts():
    """API endpoint for recent alerts"""
    return jsonify(dashboard.get_recent_alerts())

@app.route('/api/metrics')
def api_metrics():
    """API endpoint for performance metrics"""
    return jsonify(dashboard.get_performance_metrics())

@app.route('/api/users')
def api_users():
    """API endpoint for user adoption stats"""
    return jsonify(dashboard.get_user_adoption_stats())

# HTML template for the dashboard
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Deployment Status Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f5f5;
            color: #333;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 1.8rem;
            font-weight: 600;
        }
        
        .header .subtitle {
            opacity: 0.9;
            margin-top: 0.25rem;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border: 1px solid #e1e5e9;
        }
        
        .card h3 {
            margin-bottom: 1rem;
            color: #2c3e50;
            font-size: 1.1rem;
            font-weight: 600;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-healthy { background-color: #27ae60; }
        .status-unhealthy { background-color: #e74c3c; }
        .status-warning { background-color: #f39c12; }
        .status-unknown { background-color: #95a5a6; }
        
        .metric-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 0;
            border-bottom: 1px solid #ecf0f1;
        }
        
        .metric-row:last-child {
            border-bottom: none;
        }
        
        .metric-value {
            font-weight: 600;
            color: #2c3e50;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background-color: #ecf0f1;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 0.5rem;
        }
        
        .progress-fill {
            height: 100%;
            transition: width 0.3s ease;
        }
        
        .progress-normal { background-color: #27ae60; }
        .progress-warning { background-color: #f39c12; }
        .progress-critical { background-color: #e74c3c; }
        
        .alert {
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            border-radius: 4px;
            border-left: 4px solid;
        }
        
        .alert-critical {
            background-color: #fdf2f2;
            border-color: #e74c3c;
            color: #c0392b;
        }
        
        .alert-warning {
            background-color: #fef9e7;
            border-color: #f39c12;
            color: #d68910;
        }
        
        .alert-info {
            background-color: #ebf3fd;
            border-color: #3498db;
            color: #2980b9;
        }
        
        .timestamp {
            font-size: 0.85rem;
            color: #7f8c8d;
            margin-top: 0.25rem;
        }
        
        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 1rem;
        }
        
        .loading {
            text-align: center;
            padding: 2rem;
            color: #7f8c8d;
        }
        
        .refresh-indicator {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            font-size: 0.85rem;
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        .refresh-indicator.show {
            opacity: 1;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Deployment Status Dashboard</h1>
        <div class="subtitle">Real-time monitoring of system health and performance</div>
    </div>
    
    <div class="container">
        <div class="grid">
            <!-- System Overview -->
            <div class="card">
                <h3>System Overview</h3>
                <div id="system-overview" class="loading">Loading...</div>
            </div>
            
            <!-- Service Health -->
            <div class="card">
                <h3>Service Health</h3>
                <div id="service-health" class="loading">Loading...</div>
            </div>
            
            <!-- Docker Containers -->
            <div class="card">
                <h3>Docker Containers</h3>
                <div id="docker-status" class="loading">Loading...</div>
            </div>
            
            <!-- User Adoption -->
            <div class="card">
                <h3>User Adoption</h3>
                <div id="user-stats" class="loading">Loading...</div>
            </div>
        </div>
        
        <!-- Performance Charts -->
        <div class="card">
            <h3>System Performance (Last 24 Hours)</h3>
            <div class="chart-container">
                <canvas id="performance-chart"></canvas>
            </div>
        </div>
        
        <!-- Recent Alerts -->
        <div class="card">
            <h3>Recent Alerts</h3>
            <div id="recent-alerts" class="loading">Loading...</div>
        </div>
    </div>
    
    <div id="refresh-indicator" class="refresh-indicator">Refreshing...</div>
    
    <script>
        let performanceChart = null;
        
        function showRefreshIndicator() {
            const indicator = document.getElementById('refresh-indicator');
            indicator.classList.add('show');
            setTimeout(() => indicator.classList.remove('show'), 1000);
        }
        
        function getStatusClass(status) {
            switch(status) {
                case 'healthy': case 'running': return 'status-healthy';
                case 'unhealthy': case 'error': return 'status-unhealthy';
                case 'timeout': case 'warning': return 'status-warning';
                default: return 'status-unknown';
            }
        }
        
        function getProgressClass(percent) {
            if (percent < 70) return 'progress-normal';
            if (percent < 85) return 'progress-warning';
            return 'progress-critical';
        }
        
        function formatBytes(bytes) {
            const sizes = ['B', 'KB', 'MB', 'GB'];
            if (bytes === 0) return '0 B';
            const i = Math.floor(Math.log(bytes) / Math.log(1024));
            return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
        }
        
        function updateSystemOverview(data) {
            const container = document.getElementById('system-overview');
            const system = data.system;
            
            container.innerHTML = `
                <div class="metric-row">
                    <span>CPU Usage</span>
                    <span class="metric-value">${system.cpu_percent?.toFixed(1) || 0}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill ${getProgressClass(system.cpu_percent || 0)}" 
                         style="width: ${system.cpu_percent || 0}%"></div>
                </div>
                
                <div class="metric-row">
                    <span>Memory Usage</span>
                    <span class="metric-value">${system.memory_percent?.toFixed(1) || 0}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill ${getProgressClass(system.memory_percent || 0)}" 
                         style="width: ${system.memory_percent || 0}%"></div>
                </div>
                
                <div class="metric-row">
                    <span>Disk Usage</span>
                    <span class="metric-value">${system.disk_percent?.toFixed(1) || 0}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill ${getProgressClass(system.disk_percent || 0)}" 
                         style="width: ${system.disk_percent || 0}%"></div>
                </div>
                
                <div class="metric-row">
                    <span>Memory</span>
                    <span class="metric-value">${system.memory_used_gb || 0}GB / ${system.memory_total_gb || 0}GB</span>
                </div>
                
                <div class="metric-row">
                    <span>Network I/O</span>
                    <span class="metric-value">↑${formatBytes(system.network_bytes_sent || 0)} ↓${formatBytes(system.network_bytes_recv || 0)}</span>
                </div>
            `;
        }
        
        function updateServiceHealth(data) {
            const container = document.getElementById('service-health');
            
            container.innerHTML = data.services.map(service => `
                <div class="metric-row">
                    <span>
                        <span class="status-indicator ${getStatusClass(service.status)}"></span>
                        ${service.name}
                    </span>
                    <span class="metric-value">${service.response_time?.toFixed(0) || 0}ms</span>
                </div>
            `).join('');
        }
        
        function updateDockerStatus(data) {
            const container = document.getElementById('docker-status');
            
            container.innerHTML = data.containers.map(container => `
                <div class="metric-row">
                    <span>
                        <span class="status-indicator ${getStatusClass(container.status)}"></span>
                        ${container.name.replace('reverse-coach-', '').replace('-prod', '')}
                    </span>
                    <span class="metric-value">${container.status}</span>
                </div>
            `).join('');
        }
        
        function updateUserStats(data) {
            const container = document.getElementById('user-stats');
            
            container.innerHTML = `
                <div class="metric-row">
                    <span>Total Users</span>
                    <span class="metric-value">${data.total_users || 0}</span>
                </div>
                <div class="metric-row">
                    <span>Active Users (24h)</span>
                    <span class="metric-value">${data.active_users_24h || 0}</span>
                </div>
                <div class="metric-row">
                    <span>New Registrations (24h)</span>
                    <span class="metric-value">${data.new_registrations_24h || 0}</span>
                </div>
                <div class="metric-row">
                    <span>Total Projects</span>
                    <span class="metric-value">${data.total_projects || 0}</span>
                </div>
                <div class="metric-row">
                    <span>Active Projects (24h)</span>
                    <span class="metric-value">${data.active_projects_24h || 0}</span>
                </div>
            `;
        }
        
        function updatePerformanceChart(data) {
            const ctx = document.getElementById('performance-chart').getContext('2d');
            
            if (performanceChart) {
                performanceChart.destroy();
            }
            
            const history = data.system_history || [];
            const labels = history.map(h => new Date(h.timestamp).toLocaleTimeString()).reverse();
            
            performanceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'CPU %',
                            data: history.map(h => h.cpu_percent).reverse(),
                            borderColor: '#3498db',
                            backgroundColor: 'rgba(52, 152, 219, 0.1)',
                            tension: 0.4
                        },
                        {
                            label: 'Memory %',
                            data: history.map(h => h.memory_percent).reverse(),
                            borderColor: '#e74c3c',
                            backgroundColor: 'rgba(231, 76, 60, 0.1)',
                            tension: 0.4
                        },
                        {
                            label: 'Disk %',
                            data: history.map(h => h.disk_percent).reverse(),
                            borderColor: '#f39c12',
                            backgroundColor: 'rgba(243, 156, 18, 0.1)',
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'top'
                        }
                    }
                }
            });
        }
        
        function updateAlerts(data) {
            const container = document.getElementById('recent-alerts');
            
            if (!data || data.length === 0) {
                container.innerHTML = '<div style="text-align: center; color: #27ae60; padding: 1rem;">No recent alerts 🎉</div>';
                return;
            }
            
            container.innerHTML = data.map(alert => `
                <div class="alert alert-${alert.severity}">
                    <strong>${alert.type.replace('_', ' ').toUpperCase()}</strong>: ${alert.message}
                    <div class="timestamp">${new Date(alert.timestamp).toLocaleString()}</div>
                </div>
            `).join('');
        }
        
        async function fetchData() {
            try {
                showRefreshIndicator();
                
                const [statusResponse, alertsResponse, metricsResponse, usersResponse] = await Promise.all([
                    fetch('/api/status'),
                    fetch('/api/alerts'),
                    fetch('/api/metrics'),
                    fetch('/api/users')
                ]);
                
                const statusData = await statusResponse.json();
                const alertsData = await alertsResponse.json();
                const metricsData = await metricsResponse.json();
                const usersData = await usersResponse.json();
                
                updateSystemOverview(statusData);
                updateServiceHealth(statusData);
                updateDockerStatus(statusData);
                updateUserStats(usersData);
                updatePerformanceChart(metricsData);
                updateAlerts(alertsData);
                
            } catch (error) {
                console.error('Error fetching data:', error);
            }
        }
        
        // Initial load
        fetchData();
        
        // Refresh every 30 seconds
        setInterval(fetchData, 30000);
    </script>
</body>
</html>
'''

def main():
    """Main function to start the dashboard"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deployment Status Dashboard')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    print(f"Starting Deployment Status Dashboard on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")
    
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()