"""
Session Caching Service
Provides Redis-based session caching for improved authentication performance.
"""

import json
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from app.cache import cache
from app.models import User

logger = logging.getLogger(__name__)


@dataclass
class CachedUserSession:
    """Cached user session data."""
    user_id: str
    email: str
    is_active: bool
    preferred_ai_provider: str
    preferred_language: str
    preferred_frameworks: Optional[List[str]]
    last_login: Optional[datetime]
    session_created: datetime
    expires_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        if self.last_login:
            data['last_login'] = self.last_login.isoformat()
        data['session_created'] = self.session_created.isoformat()
        data['expires_at'] = self.expires_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CachedUserSession':
        """Create from dictionary."""
        # Convert ISO strings back to datetime objects
        if data.get('last_login'):
            data['last_login'] = datetime.fromisoformat(data['last_login'])
        data['session_created'] = datetime.fromisoformat(data['session_created'])
        data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        return cls(**data)
    
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at


class SessionCacheService:
    """Service for caching user sessions in Redis."""
    
    def __init__(self):
        self.namespace = "user_sessions"
        self.default_ttl = 3600  # 1 hour
        self.max_ttl = 86400 * 7  # 7 days
        
        # Session statistics
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'sessions_created': 0,
            'sessions_invalidated': 0,
            'sessions_expired': 0
        }
    
    def _get_session_key(self, user_id: str) -> str:
        """Generate session cache key."""
        return f"session:{user_id}"
    
    def _get_token_key(self, token_hash: str) -> str:
        """Generate token cache key."""
        return f"token:{token_hash}"
    
    async def cache_user_session(
        self, 
        user: User, 
        token_hash: str,
        expires_in_seconds: int = None
    ) -> bool:
        """
        Cache user session data.
        
        Args:
            user: User object to cache
            token_hash: JWT token hash for reverse lookup
            expires_in_seconds: Session expiration time
            
        Returns:
            True if successfully cached
        """
        try:
            expires_in = expires_in_seconds or self.default_ttl
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Create cached session
            session = CachedUserSession(
                user_id=user.id,
                email=user.email,
                is_active=user.is_active,
                preferred_ai_provider=user.preferred_ai_provider or "openai",
                preferred_language=user.preferred_language or "python",
                preferred_frameworks=user.preferred_frameworks,
                last_login=user.last_login,
                session_created=datetime.utcnow(),
                expires_at=expires_at
            )
            
            # Cache session by user ID
            session_key = self._get_session_key(user.id)
            success1 = await cache.set(
                session_key, 
                session.to_dict(), 
                expire=expires_in,
                namespace=self.namespace
            )
            
            # Cache token mapping for reverse lookup
            token_key = self._get_token_key(token_hash)
            token_data = {
                'user_id': user.id,
                'created_at': datetime.utcnow().isoformat(),
                'expires_at': expires_at.isoformat()
            }
            success2 = await cache.set(
                token_key,
                token_data,
                expire=expires_in,
                namespace=self.namespace
            )
            
            if success1 and success2:
                self.stats['sessions_created'] += 1
                logger.debug(f"Cached session for user {user.id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to cache user session: {e}")
            return False
    
    async def get_cached_session(self, user_id: str) -> Optional[CachedUserSession]:
        """
        Get cached user session.
        
        Args:
            user_id: User ID to lookup
            
        Returns:
            CachedUserSession if found and valid, None otherwise
        """
        try:
            session_key = self._get_session_key(user_id)
            session_data = await cache.get(session_key, namespace=self.namespace)
            
            if session_data:
                session = CachedUserSession.from_dict(session_data)
                
                # Check if session is expired
                if session.is_expired():
                    await self.invalidate_session(user_id)
                    self.stats['sessions_expired'] += 1
                    return None
                
                self.stats['cache_hits'] += 1
                return session
            
            self.stats['cache_misses'] += 1
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached session: {e}")
            self.stats['cache_misses'] += 1
            return None
    
    async def get_user_by_token(self, token_hash: str) -> Optional[str]:
        """
        Get user ID by token hash.
        
        Args:
            token_hash: JWT token hash
            
        Returns:
            User ID if token is valid, None otherwise
        """
        try:
            token_key = self._get_token_key(token_hash)
            token_data = await cache.get(token_key, namespace=self.namespace)
            
            if token_data:
                expires_at = datetime.fromisoformat(token_data['expires_at'])
                
                # Check if token is expired
                if datetime.utcnow() > expires_at:
                    await cache.delete(token_key, namespace=self.namespace)
                    return None
                
                return token_data['user_id']
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user by token: {e}")
            return None
    
    async def invalidate_session(self, user_id: str) -> bool:
        """
        Invalidate user session.
        
        Args:
            user_id: User ID to invalidate
            
        Returns:
            True if successfully invalidated
        """
        try:
            session_key = self._get_session_key(user_id)
            success = await cache.delete(session_key, namespace=self.namespace)
            
            if success:
                self.stats['sessions_invalidated'] += 1
                logger.debug(f"Invalidated session for user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to invalidate session: {e}")
            return False
    
    async def invalidate_token(self, token_hash: str) -> bool:
        """
        Invalidate specific token.
        
        Args:
            token_hash: JWT token hash to invalidate
            
        Returns:
            True if successfully invalidated
        """
        try:
            token_key = self._get_token_key(token_hash)
            success = await cache.delete(token_key, namespace=self.namespace)
            
            if success:
                logger.debug(f"Invalidated token {token_hash[:8]}...")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to invalidate token: {e}")
            return False
    
    async def refresh_session(
        self, 
        user_id: str, 
        new_token_hash: str,
        old_token_hash: Optional[str] = None,
        expires_in_seconds: int = None
    ) -> bool:
        """
        Refresh user session with new token.
        
        Args:
            user_id: User ID
            new_token_hash: New JWT token hash
            old_token_hash: Old JWT token hash to invalidate
            expires_in_seconds: New session expiration time
            
        Returns:
            True if successfully refreshed
        """
        try:
            # Get existing session
            session = await self.get_cached_session(user_id)
            if not session:
                return False
            
            # Invalidate old token if provided
            if old_token_hash:
                await self.invalidate_token(old_token_hash)
            
            # Update session expiration
            expires_in = expires_in_seconds or self.default_ttl
            session.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Re-cache session
            session_key = self._get_session_key(user_id)
            success1 = await cache.set(
                session_key,
                session.to_dict(),
                expire=expires_in,
                namespace=self.namespace
            )
            
            # Cache new token mapping
            token_key = self._get_token_key(new_token_hash)
            token_data = {
                'user_id': user_id,
                'created_at': datetime.utcnow().isoformat(),
                'expires_at': session.expires_at.isoformat()
            }
            success2 = await cache.set(
                token_key,
                token_data,
                expire=expires_in,
                namespace=self.namespace
            )
            
            return success1 and success2
            
        except Exception as e:
            logger.error(f"Failed to refresh session: {e}")
            return False
    
    async def get_active_sessions_count(self) -> int:
        """
        Get count of active sessions.
        
        Returns:
            Number of active sessions
        """
        try:
            # This is a simplified count - in production you might want to
            # scan through all session keys to get an accurate count
            return self.stats['sessions_created'] - self.stats['sessions_invalidated'] - self.stats['sessions_expired']
        except Exception as e:
            logger.error(f"Failed to get active sessions count: {e}")
            return 0
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions from cache.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            # Use cache pattern invalidation to clean up expired sessions
            # This is a simplified approach - Redis TTL should handle most cleanup
            pattern = f"session:*"
            cleaned_count = await cache.invalidate_pattern(pattern, namespace=self.namespace)
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired sessions")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """
        Get session cache statistics.
        
        Returns:
            Dictionary with session statistics
        """
        try:
            cache_stats = await cache.get_stats()
            active_sessions = await self.get_active_sessions_count()
            
            return {
                **self.stats,
                'active_sessions': active_sessions,
                'cache_hit_rate': self.stats['cache_hits'] / max(
                    self.stats['cache_hits'] + self.stats['cache_misses'], 1
                ),
                'redis_stats': cache_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            return self.stats
    
    async def update_session_activity(self, user_id: str) -> bool:
        """
        Update session last activity timestamp.
        
        Args:
            user_id: User ID to update
            
        Returns:
            True if successfully updated
        """
        try:
            session = await self.get_cached_session(user_id)
            if not session:
                return False
            
            # Update last activity (we can use session_created as last_activity)
            session.session_created = datetime.utcnow()
            
            # Re-cache with updated timestamp
            session_key = self._get_session_key(user_id)
            success = await cache.set(
                session_key,
                session.to_dict(),
                expire=self.default_ttl,
                namespace=self.namespace
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update session activity: {e}")
            return False


# Global session cache service instance
session_cache_service = SessionCacheService()