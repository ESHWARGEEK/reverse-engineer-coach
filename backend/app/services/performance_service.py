"""
Performance Optimization Service
Provides database query optimization, lazy loading, and performance monitoring.
"""

import time
import logging
from typing import Dict, List, Optional, Any, Callable, TypeVar, Generic
from functools import wraps
from dataclasses import dataclass
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, Query
from sqlalchemy import text
from contextlib import asynccontextmanager
import asyncio
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class QueryPerformanceMetrics:
    """Performance metrics for database queries."""
    query_hash: str
    execution_time: float
    row_count: int
    timestamp: datetime
    query_type: str
    table_name: Optional[str] = None


@dataclass
class PerformanceAlert:
    """Performance alert for slow queries or high resource usage."""
    alert_type: str
    message: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    timestamp: datetime
    metadata: Dict[str, Any]


class QueryOptimizer:
    """Database query optimization utilities."""
    
    def __init__(self):
        self.query_cache: Dict[str, Any] = {}
        self.performance_metrics: deque = deque(maxlen=1000)
        self.slow_query_threshold = 1.0  # seconds
        self.alerts: deque = deque(maxlen=100)
    
    def optimize_user_scoped_query(self, query: Query, user_id: str) -> Query:
        """
        Optimize queries for user-scoped data access.
        
        Args:
            query: SQLAlchemy query object
            user_id: User ID for scoping
            
        Returns:
            Optimized query with proper indexing hints
        """
        # Add user_id filter early in the query
        optimized_query = query.filter(text(f"user_id = '{user_id}'"))
        
        # Add query hints for better performance
        optimized_query = optimized_query.execution_options(
            compiled_cache={},
            autocommit=False
        )
        
        return optimized_query
    
    def add_pagination_optimization(
        self, 
        query: Query, 
        page: int = 1, 
        page_size: int = 20,
        max_page_size: int = 100
    ) -> Query:
        """
        Add optimized pagination to query.
        
        Args:
            query: SQLAlchemy query object
            page: Page number (1-based)
            page_size: Number of items per page
            max_page_size: Maximum allowed page size
            
        Returns:
            Paginated query with optimization
        """
        # Limit page size to prevent performance issues
        page_size = min(page_size, max_page_size)
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Apply limit and offset
        return query.offset(offset).limit(page_size)
    
    def monitor_query_performance(self, func: Callable) -> Callable:
        """
        Decorator to monitor query performance.
        
        Args:
            func: Function to monitor
            
        Returns:
            Decorated function with performance monitoring
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Record metrics
                metrics = QueryPerformanceMetrics(
                    query_hash=hash(str(args) + str(kwargs)),
                    execution_time=execution_time,
                    row_count=len(result) if hasattr(result, '__len__') else 1,
                    timestamp=datetime.utcnow(),
                    query_type=func.__name__
                )
                
                self.performance_metrics.append(metrics)
                
                # Check for slow queries
                if execution_time > self.slow_query_threshold:
                    self._create_slow_query_alert(func.__name__, execution_time, metrics)
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                self._create_error_alert(func.__name__, str(e), execution_time)
                raise
        
        return wrapper
    
    def _create_slow_query_alert(self, query_name: str, execution_time: float, metrics: QueryPerformanceMetrics):
        """Create alert for slow query."""
        severity = 'high' if execution_time > 5.0 else 'medium'
        
        alert = PerformanceAlert(
            alert_type='slow_query',
            message=f"Slow query detected: {query_name} took {execution_time:.2f}s",
            severity=severity,
            timestamp=datetime.utcnow(),
            metadata={
                'query_name': query_name,
                'execution_time': execution_time,
                'row_count': metrics.row_count,
                'query_hash': metrics.query_hash
            }
        )
        
        self.alerts.append(alert)
        logger.warning(f"Slow query alert: {alert.message}")
    
    def _create_error_alert(self, query_name: str, error_message: str, execution_time: float):
        """Create alert for query error."""
        alert = PerformanceAlert(
            alert_type='query_error',
            message=f"Query error in {query_name}: {error_message}",
            severity='high',
            timestamp=datetime.utcnow(),
            metadata={
                'query_name': query_name,
                'error_message': error_message,
                'execution_time': execution_time
            }
        )
        
        self.alerts.append(alert)
        logger.error(f"Query error alert: {alert.message}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        if not self.performance_metrics:
            return {}
        
        execution_times = [m.execution_time for m in self.performance_metrics]
        row_counts = [m.row_count for m in self.performance_metrics]
        
        return {
            'total_queries': len(self.performance_metrics),
            'avg_execution_time': sum(execution_times) / len(execution_times),
            'max_execution_time': max(execution_times),
            'min_execution_time': min(execution_times),
            'avg_row_count': sum(row_counts) / len(row_counts),
            'slow_queries': len([m for m in self.performance_metrics if m.execution_time > self.slow_query_threshold]),
            'recent_alerts': len([a for a in self.alerts if a.timestamp > datetime.utcnow() - timedelta(hours=1)])
        }


class LazyLoader(Generic[T]):
    """Lazy loading utility for expensive operations."""
    
    def __init__(self, loader_func: Callable[[], T]):
        self._loader_func = loader_func
        self._value: Optional[T] = None
        self._loaded = False
        self._loading = False
        self._load_lock = asyncio.Lock()
    
    async def get(self) -> T:
        """Get the lazy-loaded value."""
        if self._loaded:
            return self._value
        
        async with self._load_lock:
            if not self._loaded and not self._loading:
                self._loading = True
                try:
                    if asyncio.iscoroutinefunction(self._loader_func):
                        self._value = await self._loader_func()
                    else:
                        self._value = self._loader_func()
                    self._loaded = True
                finally:
                    self._loading = False
        
        return self._value
    
    def is_loaded(self) -> bool:
        """Check if value has been loaded."""
        return self._loaded
    
    def reset(self):
        """Reset the lazy loader."""
        self._value = None
        self._loaded = False
        self._loading = False


class BatchProcessor:
    """Batch processing utility for database operations."""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.pending_operations: List[Callable] = []
        self.batch_lock = asyncio.Lock()
    
    async def add_operation(self, operation: Callable):
        """Add operation to batch."""
        async with self.batch_lock:
            self.pending_operations.append(operation)
            
            if len(self.pending_operations) >= self.batch_size:
                await self._process_batch()
    
    async def flush(self):
        """Process all pending operations."""
        async with self.batch_lock:
            if self.pending_operations:
                await self._process_batch()
    
    async def _process_batch(self):
        """Process current batch of operations."""
        if not self.pending_operations:
            return
        
        batch = self.pending_operations.copy()
        self.pending_operations.clear()
        
        try:
            # Execute all operations in batch
            results = []
            for operation in batch:
                if asyncio.iscoroutinefunction(operation):
                    result = await operation()
                else:
                    result = operation()
                results.append(result)
            
            logger.info(f"Processed batch of {len(batch)} operations")
            return results
            
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            # Re-add failed operations for retry
            self.pending_operations.extend(batch)
            raise


class PerformanceMonitor:
    """System performance monitoring."""
    
    def __init__(self):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.thresholds = {
            'response_time': 2.0,  # seconds
            'memory_usage': 80.0,  # percentage
            'cpu_usage': 80.0,     # percentage
            'error_rate': 5.0      # percentage
        }
    
    def record_metric(self, metric_name: str, value: float, timestamp: Optional[datetime] = None):
        """Record a performance metric."""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        self.metrics[metric_name].append({
            'value': value,
            'timestamp': timestamp
        })
        
        # Check thresholds
        if metric_name in self.thresholds and value > self.thresholds[metric_name]:
            self._create_threshold_alert(metric_name, value)
    
    def _create_threshold_alert(self, metric_name: str, value: float):
        """Create alert for threshold breach."""
        threshold = self.thresholds[metric_name]
        severity = 'critical' if value > threshold * 1.5 else 'high'
        
        logger.warning(f"Performance threshold breached: {metric_name} = {value} (threshold: {threshold})")
    
    def get_metric_summary(self, metric_name: str, window_minutes: int = 60) -> Dict[str, Any]:
        """Get summary statistics for a metric."""
        if metric_name not in self.metrics:
            return {}
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
        recent_values = [
            m['value'] for m in self.metrics[metric_name]
            if m['timestamp'] > cutoff_time
        ]
        
        if not recent_values:
            return {}
        
        return {
            'count': len(recent_values),
            'avg': sum(recent_values) / len(recent_values),
            'min': min(recent_values),
            'max': max(recent_values),
            'latest': recent_values[-1] if recent_values else None
        }
    
    @asynccontextmanager
    async def measure_time(self, operation_name: str):
        """Context manager to measure operation time."""
        start_time = time.time()
        try:
            yield
        finally:
            execution_time = time.time() - start_time
            self.record_metric(f"{operation_name}_time", execution_time)


class DatabaseConnectionPool:
    """Enhanced database connection pool management."""
    
    def __init__(self):
        self.active_connections = 0
        self.max_connections = 20
        self.connection_timeout = 30
        self.pool_stats = {
            'created': 0,
            'closed': 0,
            'timeouts': 0,
            'errors': 0
        }
    
    @asynccontextmanager
    async def get_connection(self, db_session_factory: Callable):
        """Get database connection with monitoring."""
        if self.active_connections >= self.max_connections:
            raise Exception("Connection pool exhausted")
        
        self.active_connections += 1
        self.pool_stats['created'] += 1
        
        start_time = time.time()
        session = None
        
        try:
            session = db_session_factory()
            yield session
            
        except Exception as e:
            self.pool_stats['errors'] += 1
            logger.error(f"Database connection error: {e}")
            raise
            
        finally:
            if session:
                try:
                    session.close()
                except Exception as e:
                    logger.error(f"Error closing database session: {e}")
            
            self.active_connections -= 1
            self.pool_stats['closed'] += 1
            
            # Check for connection timeout
            if time.time() - start_time > self.connection_timeout:
                self.pool_stats['timeouts'] += 1
                logger.warning(f"Database connection timeout: {time.time() - start_time:.2f}s")
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        return {
            **self.pool_stats,
            'active_connections': self.active_connections,
            'max_connections': self.max_connections,
            'utilization': (self.active_connections / self.max_connections) * 100
        }


# Global instances
query_optimizer = QueryOptimizer()
performance_monitor = PerformanceMonitor()
db_pool = DatabaseConnectionPool()


# Performance decorators
def optimize_query(func: Callable) -> Callable:
    """Decorator to optimize database queries."""
    return query_optimizer.monitor_query_performance(func)


def lazy_load(loader_func: Callable[[], T]) -> LazyLoader[T]:
    """Create a lazy loader for expensive operations."""
    return LazyLoader(loader_func)


async def batch_process(operations: List[Callable], batch_size: int = 100) -> List[Any]:
    """Process operations in batches for better performance."""
    processor = BatchProcessor(batch_size)
    
    for operation in operations:
        await processor.add_operation(operation)
    
    await processor.flush()