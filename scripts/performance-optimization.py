#!/usr/bin/env python3
"""
Performance Optimization Script for Enhanced User System
Identifies bottlenecks and applies optimizations
"""

import asyncio
import aiohttp
import time
import json
import sys
import os
from typing import Dict, List, Any
import logging
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    endpoint: str
    method: str
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    success_rate: float
    requests_per_second: float

class PerformanceOptimizer:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.metrics: List[PerformanceMetric] = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def benchmark_endpoint(self, endpoint: str, method: str = "GET", 
                                data: Dict = None, headers: Dict = None, 
                                num_requests: int = 50) -> PerformanceMetric:
        """Benchmark a specific endpoint"""
        logger.info(f"Benchmarking {method} {endpoint} with {num_requests} requests")
        
        response_times = []
        successful_requests = 0
        
        start_time = time.time()
        
        for i in range(num_requests):
            request_start = time.time()
            
            try:
                if method.upper() == "GET":
                    async with self.session.get(f"{self.base_url}{endpoint}", headers=headers) as response:
                        await response.read()  # Ensure full response is received
                        if response.status < 400:
                            successful_requests += 1
                elif method.upper() == "POST":
                    async with self.session.post(f"{self.base_url}{endpoint}", json=data, headers=headers) as response:
                        await response.read()
                        if response.status < 400:
                            successful_requests += 1
                
                request_time = time.time() - request_start
                response_times.append(request_time)
                
            except Exception as e:
                logger.warning(f"Request {i+1} failed: {e}")
                response_times.append(10.0)  # Penalty for failed requests
        
        total_time = time.time() - start_time
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
        else:
            avg_time = min_time = max_time = 0
        
        success_rate = successful_requests / num_requests
        rps = num_requests / total_time if total_time > 0 else 0
        
        metric = PerformanceMetric(
            endpoint=endpoint,
            method=method,
            avg_response_time=avg_time,
            min_response_time=min_time,
            max_response_time=max_time,
            success_rate=success_rate,
            requests_per_second=rps
        )
        
        self.metrics.append(metric)
        return metric
    
    async def setup_test_user(self) -> Dict[str, str]:
        """Create a test user and return auth headers"""
        test_email = f"perf_test_{int(time.time())}@example.com"
        registration_data = {
            "email": test_email,
            "password": "TestPassword123!",
            "github_token": "ghp_test_token",
            "ai_api_key": "sk-test_key"
        }
        
        try:
            async with self.session.post(f"{self.base_url}/api/v1/auth/register", json=registration_data) as response:
                if response.status == 201:
                    data = await response.json()
                    token = data.get("access_token")
                    return {"Authorization": f"Bearer {token}"}
        except Exception as e:
            logger.warning(f"Could not create test user: {e}")
        
        return {}
    
    async def run_performance_tests(self):
        """Run comprehensive performance tests"""
        logger.info("🚀 Starting Performance Optimization Tests")
        
        # Test public endpoints
        await self.benchmark_endpoint("/health", "GET")
        await self.benchmark_endpoint("/", "GET")
        
        # Setup authenticated user
        auth_headers = await self.setup_test_user()
        
        if auth_headers:
            # Test authentication endpoints
            login_data = {"email": "test@example.com", "password": "wrongpassword"}
            await self.benchmark_endpoint("/api/v1/auth/login", "POST", data=login_data, num_requests=20)
            
            # Test protected endpoints
            await self.benchmark_endpoint("/api/v1/profile", "GET", headers=auth_headers)
            await self.benchmark_endpoint("/api/v1/dashboard/projects", "GET", headers=auth_headers)
            
            # Test discovery endpoint
            discovery_data = {"concept": "web framework"}
            await self.benchmark_endpoint("/api/v1/discover/repositories", "POST", 
                                        data=discovery_data, headers=auth_headers, num_requests=10)
        
        self.analyze_results()
    
    def analyze_results(self):
        """Analyze performance results and provide recommendations"""
        logger.info("\n" + "="*80)
        logger.info("📊 PERFORMANCE ANALYSIS REPORT")
        logger.info("="*80)
        
        # Performance thresholds
        SLOW_THRESHOLD = 1.0  # seconds
        VERY_SLOW_THRESHOLD = 2.0  # seconds
        LOW_RPS_THRESHOLD = 10  # requests per second
        
        slow_endpoints = []
        very_slow_endpoints = []
        low_throughput_endpoints = []
        
        for metric in self.metrics:
            logger.info(f"\n📈 {metric.method} {metric.endpoint}")
            logger.info(f"  Average Response Time: {metric.avg_response_time:.3f}s")
            logger.info(f"  Min/Max Response Time: {metric.min_response_time:.3f}s / {metric.max_response_time:.3f}s")
            logger.info(f"  Success Rate: {metric.success_rate:.1%}")
            logger.info(f"  Requests/Second: {metric.requests_per_second:.1f}")
            
            # Identify performance issues
            if metric.avg_response_time > VERY_SLOW_THRESHOLD:
                very_slow_endpoints.append(metric)
            elif metric.avg_response_time > SLOW_THRESHOLD:
                slow_endpoints.append(metric)
            
            if metric.requests_per_second < LOW_RPS_THRESHOLD and metric.success_rate > 0.8:
                low_throughput_endpoints.append(metric)
        
        # Generate recommendations
        logger.info("\n🔧 OPTIMIZATION RECOMMENDATIONS:")
        
        if very_slow_endpoints:
            logger.info("\n❌ CRITICAL PERFORMANCE ISSUES:")
            for metric in very_slow_endpoints:
                logger.info(f"  • {metric.endpoint}: {metric.avg_response_time:.3f}s (CRITICAL)")
                self.generate_optimization_suggestions(metric)
        
        if slow_endpoints:
            logger.info("\n⚠️  PERFORMANCE WARNINGS:")
            for metric in slow_endpoints:
                logger.info(f"  • {metric.endpoint}: {metric.avg_response_time:.3f}s")
                self.generate_optimization_suggestions(metric)
        
        if low_throughput_endpoints:
            logger.info("\n📉 LOW THROUGHPUT ENDPOINTS:")
            for metric in low_throughput_endpoints:
                logger.info(f"  • {metric.endpoint}: {metric.requests_per_second:.1f} RPS")
        
        # Overall system assessment
        avg_response_time = sum(m.avg_response_time for m in self.metrics) / len(self.metrics)
        avg_success_rate = sum(m.success_rate for m in self.metrics) / len(self.metrics)
        
        logger.info(f"\n📊 OVERALL SYSTEM PERFORMANCE:")
        logger.info(f"  Average Response Time: {avg_response_time:.3f}s")
        logger.info(f"  Average Success Rate: {avg_success_rate:.1%}")
        
        if avg_response_time < 0.5 and avg_success_rate > 0.95:
            logger.info("  ✅ System performance is excellent")
        elif avg_response_time < 1.0 and avg_success_rate > 0.9:
            logger.info("  ✅ System performance is good")
        elif avg_response_time < 2.0 and avg_success_rate > 0.8:
            logger.info("  ⚠️  System performance needs improvement")
        else:
            logger.info("  ❌ System performance is poor - optimization required")
    
    def generate_optimization_suggestions(self, metric: PerformanceMetric):
        """Generate specific optimization suggestions for slow endpoints"""
        suggestions = []
        
        if "/auth/" in metric.endpoint:
            suggestions.extend([
                "Consider implementing Redis caching for session data",
                "Optimize password hashing rounds (balance security vs performance)",
                "Implement connection pooling for database operations"
            ])
        
        if "/discover/" in metric.endpoint:
            suggestions.extend([
                "Implement aggressive caching for repository search results",
                "Consider background processing for AI analysis",
                "Add pagination to limit response size",
                "Implement request deduplication"
            ])
        
        if "/dashboard/" in metric.endpoint or "/profile/" in metric.endpoint:
            suggestions.extend([
                "Add database query optimization and indexing",
                "Implement data pagination for large result sets",
                "Consider lazy loading for non-critical data"
            ])
        
        if metric.avg_response_time > 2.0:
            suggestions.extend([
                "Add database connection pooling",
                "Implement async processing for heavy operations",
                "Consider CDN for static content",
                "Add response compression"
            ])
        
        for suggestion in suggestions[:3]:  # Limit to top 3 suggestions
            logger.info(f"    → {suggestion}")

async def main():
    """Main performance optimization runner"""
    base_url = os.getenv("TEST_BASE_URL", "http://localhost:8000")
    
    async with PerformanceOptimizer(base_url) as optimizer:
        await optimizer.run_performance_tests()

if __name__ == "__main__":
    asyncio.run(main())