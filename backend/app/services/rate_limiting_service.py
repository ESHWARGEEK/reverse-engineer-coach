"""
Rate Limiting Service
Provides comprehensive rate limiting functionality for API endpoints.
"""

import time
import logging
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RateLimitType(Enum):
    """Types of rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration."""
    max_requests: int
    window_seconds: int
    limit_type: RateLimitType = RateLimitType.SLIDING_WINDOW
    burst_allowance: int = 0  # For token bucket
    
    def __post_init__(self):
        if self.max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None


class RateLimitStorage:
    """In-memory storage for rate limiting data."""
    
    def __init__(self):
        self._data: Dict[str, deque] = defaultdict(deque)
        self._token_buckets: Dict[str, Dict] = {}
    
    def get_requests(self, key: str) -> deque:
        """Get request timestamps for a key."""
        return self._data[key]
    
    def add_request(self, key: str, timestamp: float):
        """Add a request timestamp."""
        self._data[key].append(timestamp)
    
    def cleanup_old_requests(self, key: str, cutoff_time: float):
        """Remove requests older than cutoff time."""
        requests = self._data[key]
        while requests and requests[0] < cutoff_time:
            requests.popleft()
    
    def get_token_bucket(self, key: str) -> Dict:
        """Get token bucket state."""
        return self._token_buckets.get(key, {})
    
    def set_token_bucket(self, key: str, bucket_state: Dict):
        """Set token bucket state."""
        self._token_buckets[key] = bucket_state
    
    def clear_expired_data(self, max_age_seconds: int = 3600):
        """Clear data older than max_age_seconds."""
        cutoff_time = time.time() - max_age_seconds
        
        # Clear old request data
        keys_to_remove = []
        for key, requests in self._data.items():
            self.cleanup_old_requests(key, cutoff_time)
            if not requests:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._data[key]
        
        # Clear old token buckets
        bucket_keys_to_remove = []
        for key, bucket in self._token_buckets.items():
            if bucket.get('last_refill', 0) < cutoff_time:
                bucket_keys_to_remove.append(key)
        
        for key in bucket_keys_to_remove:
            del self._token_buckets[key]


class RateLimitingService:
    """Comprehensive rate limiting service."""
    
    def __init__(self, storage: Optional[RateLimitStorage] = None):
        self.storage = storage or RateLimitStorage()
        
        # Default rate limit rules for different endpoint types
        self.default_rules = {
            'auth_login': RateLimitRule(15, 300),  # 15 requests per 5 minutes
            'auth_register': RateLimitRule(10, 3600),  # 10 requests per hour
            'auth_refresh': RateLimitRule(10, 60),  # 10 requests per minute
            'api_general': RateLimitRule(100, 60),  # 100 requests per minute
            'api_discovery': RateLimitRule(20, 60),  # 20 requests per minute
            'api_analysis': RateLimitRule(10, 60),  # 10 requests per minute
            'file_upload': RateLimitRule(10, 60),  # 10 uploads per minute
            'password_change': RateLimitRule(5, 300),  # 5 changes per 5 minutes
            'credential_update': RateLimitRule(10, 300),  # 10 updates per 5 minutes
        }
    
    def check_rate_limit(
        self, 
        key: str, 
        rule: RateLimitRule,
        identifier: str = "default"
    ) -> RateLimitResult:
        """
        Check if request is within rate limit.
        
        Args:
            key: Unique identifier for the rate limit (e.g., IP address, user ID)
            rule: Rate limiting rule to apply
            identifier: Additional identifier for the rule type
            
        Returns:
            RateLimitResult with allow/deny decision and metadata
        """
        full_key = f"{identifier}:{key}"
        current_time = time.time()
        
        if rule.limit_type == RateLimitType.SLIDING_WINDOW:
            return self._check_sliding_window(full_key, rule, current_time)
        elif rule.limit_type == RateLimitType.FIXED_WINDOW:
            return self._check_fixed_window(full_key, rule, current_time)
        elif rule.limit_type == RateLimitType.TOKEN_BUCKET:
            return self._check_token_bucket(full_key, rule, current_time)
        else:
            raise ValueError(f"Unknown rate limit type: {rule.limit_type}")
    
    def _check_sliding_window(
        self, 
        key: str, 
        rule: RateLimitRule, 
        current_time: float
    ) -> RateLimitResult:
        """Check rate limit using sliding window algorithm."""
        window_start = current_time - rule.window_seconds
        
        # Clean up old requests
        self.storage.cleanup_old_requests(key, window_start)
        
        # Get current request count
        requests = self.storage.get_requests(key)
        current_count = len(requests)
        
        # Calculate reset time (end of current window)
        reset_time = datetime.fromtimestamp(current_time + rule.window_seconds)
        
        if current_count < rule.max_requests:
            # Allow request
            self.storage.add_request(key, current_time)
            return RateLimitResult(
                allowed=True,
                remaining=rule.max_requests - current_count - 1,
                reset_time=reset_time
            )
        else:
            # Deny request
            oldest_request = requests[0] if requests else current_time
            retry_after = int(oldest_request + rule.window_seconds - current_time)
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=reset_time,
                retry_after=max(1, retry_after)
            )
    
    def _check_fixed_window(
        self, 
        key: str, 
        rule: RateLimitRule, 
        current_time: float
    ) -> RateLimitResult:
        """Check rate limit using fixed window algorithm."""
        # Calculate current window
        window_start = int(current_time // rule.window_seconds) * rule.window_seconds
        window_end = window_start + rule.window_seconds
        
        # Clean up requests outside current window
        self.storage.cleanup_old_requests(key, window_start)
        
        # Get current request count in this window
        requests = self.storage.get_requests(key)
        current_count = len(requests)
        
        reset_time = datetime.fromtimestamp(window_end)
        
        if current_count < rule.max_requests:
            # Allow request
            self.storage.add_request(key, current_time)
            return RateLimitResult(
                allowed=True,
                remaining=rule.max_requests - current_count - 1,
                reset_time=reset_time
            )
        else:
            # Deny request
            retry_after = int(window_end - current_time)
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=reset_time,
                retry_after=max(1, retry_after)
            )
    
    def _check_token_bucket(
        self, 
        key: str, 
        rule: RateLimitRule, 
        current_time: float
    ) -> RateLimitResult:
        """Check rate limit using token bucket algorithm."""
        bucket = self.storage.get_token_bucket(key)
        
        # Initialize bucket if not exists
        if not bucket:
            bucket = {
                'tokens': rule.max_requests,
                'last_refill': current_time
            }
        
        # Calculate tokens to add based on time elapsed
        time_elapsed = current_time - bucket['last_refill']
        tokens_to_add = int(time_elapsed * (rule.max_requests / rule.window_seconds))
        
        # Refill bucket
        bucket['tokens'] = min(
            rule.max_requests + rule.burst_allowance,
            bucket['tokens'] + tokens_to_add
        )
        bucket['last_refill'] = current_time
        
        reset_time = datetime.fromtimestamp(
            current_time + (rule.max_requests - bucket['tokens']) * (rule.window_seconds / rule.max_requests)
        )
        
        if bucket['tokens'] >= 1:
            # Allow request
            bucket['tokens'] -= 1
            self.storage.set_token_bucket(key, bucket)
            
            return RateLimitResult(
                allowed=True,
                remaining=int(bucket['tokens']),
                reset_time=reset_time
            )
        else:
            # Deny request
            retry_after = int(rule.window_seconds / rule.max_requests)
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=reset_time,
                retry_after=retry_after
            )
    
    def get_rate_limit_for_endpoint(self, endpoint_type: str) -> RateLimitRule:
        """Get rate limit rule for specific endpoint type."""
        return self.default_rules.get(endpoint_type, self.default_rules['api_general'])
    
    def check_ip_rate_limit(
        self, 
        ip_address: str, 
        endpoint_type: str = 'api_general'
    ) -> RateLimitResult:
        """Check rate limit for IP address."""
        rule = self.get_rate_limit_for_endpoint(endpoint_type)
        return self.check_rate_limit(ip_address, rule, f"ip_{endpoint_type}")
    
    def check_user_rate_limit(
        self, 
        user_id: str, 
        endpoint_type: str = 'api_general'
    ) -> RateLimitResult:
        """Check rate limit for authenticated user."""
        rule = self.get_rate_limit_for_endpoint(endpoint_type)
        return self.check_rate_limit(user_id, rule, f"user_{endpoint_type}")
    
    def is_suspicious_activity(
        self, 
        ip_address: str, 
        user_agent: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Detect suspicious activity patterns.
        
        Returns:
            Tuple of (is_suspicious, reason)
        """
        # Check for rapid requests from same IP
        rapid_requests_rule = RateLimitRule(50, 60)  # 50 requests per minute
        rapid_result = self.check_rate_limit(
            ip_address, 
            rapid_requests_rule, 
            "suspicious_rapid"
        )
        
        if not rapid_result.allowed:
            return True, "Too many rapid requests"
        
        # Check user agent patterns
        if user_agent:
            suspicious_agents = [
                'curl', 'wget', 'python-requests', 'bot', 'crawler', 
                'spider', 'scraper', 'scanner'
            ]
            
            user_agent_lower = user_agent.lower()
            for agent in suspicious_agents:
                if agent in user_agent_lower:
                    return True, f"Suspicious user agent: {agent}"
        
        return False, ""
    
    def cleanup_expired_data(self):
        """Clean up expired rate limiting data."""
        self.storage.clear_expired_data()
        logger.info("Cleaned up expired rate limiting data")
    
    def reset_rate_limits_for_key(self, key: str, endpoint_type: str = None):
        """
        Reset rate limits for a specific key (IP or user).
        
        Args:
            key: The key to reset (IP address or user ID)
            endpoint_type: Optional endpoint type to reset specific limits
        """
        if endpoint_type:
            # Reset specific endpoint type
            full_key = f"ip_{endpoint_type}:{key}"
            if full_key in self.storage._data:
                del self.storage._data[full_key]
            
            full_key = f"user_{endpoint_type}:{key}"
            if full_key in self.storage._data:
                del self.storage._data[full_key]
        else:
            # Reset all rate limits for this key
            keys_to_remove = []
            for stored_key in self.storage._data.keys():
                if key in stored_key:
                    keys_to_remove.append(stored_key)
            
            for stored_key in keys_to_remove:
                del self.storage._data[stored_key]
        
        logger.info(f"Reset rate limits for key: {key}, endpoint_type: {endpoint_type}")
    
    def get_rate_limit_status(self, key: str, endpoint_type: str = 'api_general') -> Dict:
        """
        Get current rate limit status for a key.
        
        Args:
            key: The key to check (IP address or user ID)
            endpoint_type: Endpoint type to check
            
        Returns:
            Dictionary with rate limit status
        """
        rule = self.get_rate_limit_for_endpoint(endpoint_type)
        result = self.check_rate_limit(key, rule, f"ip_{endpoint_type}")
        
        return {
            'endpoint_type': endpoint_type,
            'max_requests': rule.max_requests,
            'window_seconds': rule.window_seconds,
            'remaining': result.remaining,
            'reset_time': result.reset_time.isoformat(),
            'allowed': result.allowed
        }


# Global rate limiting service instance
rate_limiting_service = RateLimitingService()