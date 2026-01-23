import redis
import redis.asyncio as aioredis
from app.config import settings
import json
import asyncio
import time
import hashlib
from typing import Any, Optional, Dict, List, Callable, Union
from functools import wraps
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class PerformanceCache:
    """Enhanced Redis cache with performance optimizations and rate limiting"""
    
    def __init__(self):
        # Synchronous Redis client for backward compatibility
        self.redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            max_connections=20
        )
        
        # Async Redis client for better performance
        self._async_client = None
        self._connection_pool = None
        
        # Request debouncing
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._request_lock = asyncio.Lock()
        
        # Cache statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0
        }
    
    async def _get_async_client(self):
        """Get or create async Redis client"""
        if self._async_client is None:
            self._connection_pool = aioredis.ConnectionPool.from_url(
                settings.redis_url,
                decode_responses=True,
                max_connections=20
            )
            self._async_client = aioredis.Redis(connection_pool=self._connection_pool)
        return self._async_client
    
    def _generate_cache_key(self, key: str, namespace: str = "default") -> str:
        """Generate namespaced cache key"""
        return f"reverse_coach:{namespace}:{key}"
    
    def _hash_key(self, data: Union[str, Dict, List]) -> str:
        """Generate hash for complex data structures"""
        if isinstance(data, str):
            return data
        
        # Convert to JSON string and hash
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(json_str.encode()).hexdigest()
    
    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Get value from cache with async support"""
        cache_key = self._generate_cache_key(key, namespace)
        
        try:
            client = await self._get_async_client()
            value = await client.get(cache_key)
            
            if value:
                self.stats['hits'] += 1
                return json.loads(value)
            else:
                self.stats['misses'] += 1
                return None
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Cache get error for key {cache_key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, expire: int = 3600, namespace: str = "default") -> bool:
        """Set value in cache with expiration"""
        cache_key = self._generate_cache_key(key, namespace)
        
        try:
            client = await self._get_async_client()
            serialized_value = json.dumps(value, default=str)
            
            result = await client.setex(cache_key, expire, serialized_value)
            
            if result:
                self.stats['sets'] += 1
                return True
            return False
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Cache set error for key {cache_key}: {e}")
            return False
    
    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete key from cache"""
        cache_key = self._generate_cache_key(key, namespace)
        
        try:
            client = await self._get_async_client()
            result = await client.delete(cache_key)
            
            if result:
                self.stats['deletes'] += 1
                return True
            return False
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Cache delete error for key {cache_key}: {e}")
            return False
    
    async def exists(self, key: str, namespace: str = "default") -> bool:
        """Check if key exists in cache"""
        cache_key = self._generate_cache_key(key, namespace)
        
        try:
            client = await self._get_async_client()
            return bool(await client.exists(cache_key))
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Cache exists error for key {cache_key}: {e}")
            return False
    
    async def get_many(self, keys: List[str], namespace: str = "default") -> Dict[str, Any]:
        """Get multiple values from cache efficiently"""
        cache_keys = [self._generate_cache_key(key, namespace) for key in keys]
        
        try:
            client = await self._get_async_client()
            values = await client.mget(cache_keys)
            
            result = {}
            for i, (original_key, value) in enumerate(zip(keys, values)):
                if value:
                    try:
                        result[original_key] = json.loads(value)
                        self.stats['hits'] += 1
                    except json.JSONDecodeError:
                        self.stats['errors'] += 1
                else:
                    self.stats['misses'] += 1
            
            return result
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Cache get_many error: {e}")
            return {}
    
    async def set_many(self, data: Dict[str, Any], expire: int = 3600, namespace: str = "default") -> bool:
        """Set multiple values in cache efficiently"""
        try:
            client = await self._get_async_client()
            
            # Prepare pipeline for batch operations
            pipe = client.pipeline()
            
            for key, value in data.items():
                cache_key = self._generate_cache_key(key, namespace)
                serialized_value = json.dumps(value, default=str)
                pipe.setex(cache_key, expire, serialized_value)
            
            results = await pipe.execute()
            
            success_count = sum(1 for result in results if result)
            self.stats['sets'] += success_count
            
            return success_count == len(data)
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Cache set_many error: {e}")
            return False
    
    async def invalidate_pattern(self, pattern: str, namespace: str = "default") -> int:
        """Invalidate all keys matching a pattern"""
        cache_pattern = self._generate_cache_key(pattern, namespace)
        
        try:
            client = await self._get_async_client()
            
            # Find matching keys
            keys = []
            async for key in client.scan_iter(match=cache_pattern):
                keys.append(key)
            
            if keys:
                deleted_count = await client.delete(*keys)
                self.stats['deletes'] += deleted_count
                return deleted_count
            
            return 0
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Cache invalidate_pattern error: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            client = await self._get_async_client()
            redis_info = await client.info('memory')
            
            return {
                **self.stats,
                'hit_rate': self.stats['hits'] / max(self.stats['hits'] + self.stats['misses'], 1),
                'redis_memory_used': redis_info.get('used_memory_human', 'unknown'),
                'redis_memory_peak': redis_info.get('used_memory_peak_human', 'unknown')
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return self.stats
    
    async def debounced_request(self, key: str, func: Callable, *args, **kwargs) -> Any:
        """Debounce requests to prevent duplicate API calls"""
        request_key = self._hash_key(f"{key}:{args}:{kwargs}")
        
        async with self._request_lock:
            # Check if request is already pending
            if request_key in self._pending_requests:
                logger.info(f"Debouncing request for key: {request_key}")
                return await self._pending_requests[request_key]
            
            # Create new request future
            future = asyncio.create_task(func(*args, **kwargs))
            self._pending_requests[request_key] = future
            
            try:
                result = await future
                return result
            finally:
                # Clean up completed request
                self._pending_requests.pop(request_key, None)
    
    async def close(self):
        """Close Redis connections"""
        try:
            if self._async_client:
                await self._async_client.close()
            if self._connection_pool:
                await self._connection_pool.disconnect()
        except Exception as e:
            logger.error(f"Error closing cache connections: {e}")

# Enhanced cache decorators
def cache_result(expire: int = 3600, namespace: str = "default", key_func: Optional[Callable] = None):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = await cache.get(cache_key, namespace)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            if result is not None:
                await cache.set(cache_key, result, expire, namespace)
            
            return result
        return wrapper
    return decorator

def rate_limit(max_requests: int = 100, window_seconds: int = 60, namespace: str = "rate_limit"):
    """Decorator to rate limit function calls"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate rate limit key (could be based on user ID, IP, etc.)
            rate_key = f"{func.__name__}:rate_limit"
            
            try:
                client = await cache._get_async_client()
                
                # Get current count
                current = await client.get(cache._generate_cache_key(rate_key, namespace))
                current_count = int(current) if current else 0
                
                if current_count >= max_requests:
                    raise Exception(f"Rate limit exceeded: {max_requests} requests per {window_seconds} seconds")
                
                # Increment counter
                pipe = client.pipeline()
                pipe.incr(cache._generate_cache_key(rate_key, namespace))
                pipe.expire(cache._generate_cache_key(rate_key, namespace), window_seconds)
                await pipe.execute()
                
                return await func(*args, **kwargs)
                
            except Exception as e:
                if "Rate limit exceeded" in str(e):
                    raise
                logger.error(f"Rate limiting error: {e}")
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator

# Global cache instance
cache = PerformanceCache()

# Backward compatibility
class RedisCache(PerformanceCache):
    """Backward compatibility wrapper"""
    pass

async def get_redis_client():
    """Get Redis client instance for direct Redis operations"""
    return cache.redis_client