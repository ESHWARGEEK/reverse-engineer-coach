"""
CORS Configuration Service
Provides secure CORS configuration for the FastAPI application.
"""

import os
import logging
from typing import List, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class CORSService:
    """Service for managing CORS configuration securely."""
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # Log environment detection for debugging
        logger.info(f"CORS Service initialized - Environment: {self.environment}, Debug: {self.debug}")
        logger.info(f"CORS_ORIGINS env var: {os.getenv('CORS_ORIGINS', 'NOT SET')}")
    
    def get_allowed_origins(self) -> List[str]:
        """
        Get list of allowed origins based on environment.
        
        Returns:
            List of allowed origin URLs
        """
        # Get origins from environment variable
        origins_env = os.getenv("CORS_ORIGINS", "")
        
        # ALWAYS include Netlify URLs regardless of environment
        # This ensures CORS works even if environment variables are misconfigured
        base_origins = [
            "https://rev-eng.netlify.app",
            "https://reveng.netlify.app"
        ]
        logger.info(f"Base Netlify origins always included: {base_origins}")
        
        # For debugging: also allow wildcard temporarily if in debug mode
        # Note: Wildcard doesn't work with credentials, so this is just for testing
        
        # TEMPORARY FIX: Always return Netlify origins regardless of environment
        # This bypasses any environment detection issues
        logger.info(f"Environment detected: {self.environment}")
        logger.info(f"CORS_ORIGINS env var: {origins_env}")
        
        # Start with base origins and add any additional ones from environment
        final_origins = base_origins.copy()
        
        if origins_env:
            for origin in origins_env.split(","):
                origin = origin.strip()
                if self._is_valid_origin(origin) and origin not in final_origins:
                    final_origins.append(origin)
                    logger.info(f"Added additional origin from environment: {origin}")
        
        logger.info(f"Final allowed origins (all environments): {final_origins}")
        return final_origins
    
    def get_allowed_methods(self) -> List[str]:
        """
        Get list of allowed HTTP methods.
        
        Returns:
            List of allowed HTTP methods
        """
        if self.environment == "production":
            # Production: only necessary methods
            return ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        else:
            # Development: include PATCH for flexibility
            return ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    
    def get_allowed_headers(self) -> List[str]:
        """
        Get list of allowed headers.
        
        Returns:
            List of allowed headers
        """
        base_headers = [
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-Request-ID"
        ]
        
        if self.debug:
            # Add debug headers for development
            base_headers.extend([
                "X-Debug-Mode",
                "X-Client-Version"
            ])
        
        return base_headers
    
    def get_cors_config(self) -> Dict[str, Any]:
        """
        Get complete CORS configuration.
        
        Returns:
            Dictionary with CORS configuration
        """
        config = {
            "allow_origins": self.get_allowed_origins(),
            "allow_credentials": True,
            "allow_methods": self.get_allowed_methods(),
            "allow_headers": self.get_allowed_headers(),
            "expose_headers": [
                "X-Request-ID",
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset"
            ],
            "max_age": 86400 if self.environment == "production" else 3600  # 24h prod, 1h dev
        }
        
        logger.info(f"CORS configuration for {self.environment}: {len(config['allow_origins'])} origins allowed")
        logger.info(f"Allowed origins: {config['allow_origins']}")
        
        return config
    
    def _is_valid_origin(self, origin: str) -> bool:
        """
        Validate origin URL format and security.
        
        Args:
            origin: Origin URL to validate
            
        Returns:
            True if origin is valid and secure
        """
        try:
            parsed = urlparse(origin)
            
            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Check scheme
            if self.environment == "production":
                # Production: only HTTPS, but be more permissive for netlify
                if parsed.scheme != "https":
                    return False
                
                # Allow netlify domains specifically - be more permissive
                if "netlify.app" in parsed.netloc:
                    logger.info(f"Allowing Netlify domain: {parsed.netloc}")
                    return True
                    
                # Allow our specific Netlify URLs
                if parsed.netloc in ["rev-eng.netlify.app", "reveng.netlify.app"]:
                    logger.info(f"Allowing specific Netlify URL: {parsed.netloc}")
                    return True
            else:
                # Development: allow HTTP for localhost
                if parsed.scheme not in ["http", "https"]:
                    return False
                
                if parsed.scheme == "http" and not self._is_localhost(parsed.netloc):
                    return False
            
            # Check for suspicious patterns
            if any(char in origin for char in ["<", ">", "\"", "'", "javascript:", "data:"]):
                logger.warning(f"Origin rejected due to suspicious patterns: {origin}")
                return False
            
            # Check hostname length
            if len(parsed.netloc) > 253:  # RFC 1035 limit
                logger.warning(f"Origin rejected due to hostname length: {origin}")
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Origin validation error for {origin}: {e}")
            return False
    
    def _is_localhost(self, netloc: str) -> bool:
        """
        Check if netloc is localhost.
        
        Args:
            netloc: Network location (hostname:port)
            
        Returns:
            True if netloc is localhost
        """
        hostname = netloc.split(":")[0].lower()
        return hostname in ["localhost", "127.0.0.1", "::1"]
    
    def _is_staging_origin(self, origin: str) -> bool:
        """
        Check if origin is a valid staging origin.
        
        Args:
            origin: Origin URL
            
        Returns:
            True if origin is valid for staging
        """
        try:
            parsed = urlparse(origin)
            hostname = parsed.netloc.lower()
            
            # Allow staging subdomains
            staging_patterns = [
                "staging.",
                "preview.",
                "dev.",
                "test."
            ]
            
            return any(hostname.startswith(pattern) for pattern in staging_patterns)
            
        except Exception:
            return False
    
    def validate_origin_at_runtime(self, origin: str) -> bool:
        """
        Validate origin at runtime (for dynamic CORS).
        
        Args:
            origin: Origin to validate
            
        Returns:
            True if origin is allowed
        """
        allowed_origins = self.get_allowed_origins()
        
        # Exact match
        if origin in allowed_origins:
            return True
        
        # Pattern matching for development
        if self.environment == "development":
            try:
                parsed = urlparse(origin)
                if self._is_localhost(parsed.netloc):
                    return True
            except Exception:
                pass
        
        return False


# Global CORS service instance
cors_service = CORSService()