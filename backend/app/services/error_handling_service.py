"""
Enhanced error handling service for comprehensive error management.
Provides authentication error handling, recovery mechanisms, and monitoring integration.
"""

import logging
import asyncio
import time
from typing import Dict, Any, Optional, Callable, List, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

from app.error_handlers import (
    APIError, ServiceUnavailableError, RateLimitError, ValidationError,
    create_error_response, service_monitor
)

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for monitoring and alerting"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification and handling"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    RATE_LIMIT = "rate_limit"
    SERVICE_UNAVAILABLE = "service_unavailable"
    NETWORK = "network"
    DATABASE = "database"
    EXTERNAL_API = "external_api"
    INTERNAL = "internal"


@dataclass
class ErrorContext:
    """Context information for error handling and recovery"""
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0
    max_retries: int = 3
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryStrategy:
    """Recovery strategy for handling specific error types"""
    strategy_type: str
    retry_enabled: bool = True
    retry_delay: float = 1.0
    max_retries: int = 3
    fallback_enabled: bool = False
    fallback_function: Optional[Callable] = None
    user_message: Optional[str] = None
    recovery_actions: List[str] = field(default_factory=list)


class AuthenticationError(APIError):
    """Enhanced authentication error with recovery strategies"""
    
    def __init__(
        self, 
        message: str = "Authentication failed", 
        error_type: str = "INVALID_CREDENTIALS",
        recovery_strategy: Optional[RecoveryStrategy] = None,
        context: Optional[ErrorContext] = None
    ):
        super().__init__(
            message=message,
            status_code=401,
            error_code=f"AUTH_{error_type}",
            details={
                "category": ErrorCategory.AUTHENTICATION.value,
                "severity": ErrorSeverity.MEDIUM.value,
                "recovery_available": recovery_strategy is not None,
                "context": context.__dict__ if context else {}
            }
        )
        self.error_type = error_type
        self.recovery_strategy = recovery_strategy
        self.context = context


class AuthorizationError(APIError):
    """Enhanced authorization error with context"""
    
    def __init__(
        self, 
        message: str = "Access denied", 
        required_permission: Optional[str] = None,
        context: Optional[ErrorContext] = None
    ):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_FAILED",
            details={
                "category": ErrorCategory.AUTHORIZATION.value,
                "severity": ErrorSeverity.MEDIUM.value,
                "required_permission": required_permission,
                "context": context.__dict__ if context else {}
            }
        )
        self.required_permission = required_permission
        self.context = context


class ErrorHandlingService:
    """
    Comprehensive error handling service with recovery mechanisms.
    """
    
    def __init__(self):
        self.error_stats = {}
        self.recovery_strategies = self._initialize_recovery_strategies()
        self.error_patterns = {}
        self.monitoring_enabled = True
    
    def _initialize_recovery_strategies(self) -> Dict[str, RecoveryStrategy]:
        """Initialize default recovery strategies for different error types"""
        return {
            "INVALID_TOKEN": RecoveryStrategy(
                strategy_type="token_refresh",
                retry_enabled=True,
                retry_delay=0.5,
                max_retries=1,
                user_message="Your session has expired. Please log in again.",
                recovery_actions=["Redirect to login", "Clear stored tokens"]
            ),
            "EXPIRED_TOKEN": RecoveryStrategy(
                strategy_type="token_refresh",
                retry_enabled=True,
                retry_delay=0.5,
                max_retries=1,
                user_message="Your session has expired. Refreshing authentication...",
                recovery_actions=["Attempt token refresh", "Redirect to login if refresh fails"]
            ),
            "INVALID_CREDENTIALS": RecoveryStrategy(
                strategy_type="credential_validation",
                retry_enabled=False,
                user_message="Invalid email or password. Please check your credentials and try again.",
                recovery_actions=["Verify email format", "Check password requirements", "Use password reset if needed"]
            ),
            "ACCOUNT_LOCKED": RecoveryStrategy(
                strategy_type="account_recovery",
                retry_enabled=False,
                user_message="Your account has been temporarily locked due to multiple failed login attempts.",
                recovery_actions=["Wait for lockout period to expire", "Contact support if needed", "Use password reset"]
            ),
            "RATE_LIMIT_EXCEEDED": RecoveryStrategy(
                strategy_type="rate_limit_backoff",
                retry_enabled=True,
                retry_delay=60.0,
                max_retries=3,
                user_message="Too many requests. Please wait a moment before trying again.",
                recovery_actions=["Wait for rate limit reset", "Reduce request frequency"]
            ),
            "SERVICE_UNAVAILABLE": RecoveryStrategy(
                strategy_type="service_fallback",
                retry_enabled=True,
                retry_delay=5.0,
                max_retries=3,
                fallback_enabled=True,
                user_message="Service temporarily unavailable. Using cached data where possible.",
                recovery_actions=["Retry with exponential backoff", "Use cached responses", "Notify user of limitations"]
            ),
            "NETWORK_ERROR": RecoveryStrategy(
                strategy_type="network_retry",
                retry_enabled=True,
                retry_delay=2.0,
                max_retries=3,
                user_message="Network error occurred. Retrying...",
                recovery_actions=["Retry with exponential backoff", "Check network connectivity"]
            ),
            "DATABASE_ERROR": RecoveryStrategy(
                strategy_type="database_fallback",
                retry_enabled=True,
                retry_delay=1.0,
                max_retries=2,
                fallback_enabled=True,
                user_message="Database temporarily unavailable. Some features may be limited.",
                recovery_actions=["Retry database operation", "Use read-only mode", "Cache responses"]
            )
        }
    
    async def handle_authentication_error(
        self, 
        error_type: str, 
        context: Optional[ErrorContext] = None,
        original_exception: Optional[Exception] = None
    ) -> AuthenticationError:
        """
        Handle authentication errors with appropriate recovery strategies.
        
        Args:
            error_type: Type of authentication error
            context: Error context information
            original_exception: Original exception that caused the error
            
        Returns:
            AuthenticationError with recovery strategy
        """
        # Get recovery strategy for this error type
        recovery_strategy = self.recovery_strategies.get(error_type)
        
        # Create user-friendly error messages
        error_messages = {
            "INVALID_TOKEN": "Your authentication token is invalid. Please log in again.",
            "EXPIRED_TOKEN": "Your session has expired. Please log in again.",
            "MISSING_TOKEN": "Authentication required. Please log in to continue.",
            "INVALID_CREDENTIALS": "Invalid email or password. Please check your credentials.",
            "ACCOUNT_LOCKED": "Account temporarily locked due to multiple failed attempts.",
            "ACCOUNT_DISABLED": "Your account has been disabled. Please contact support.",
            "INSUFFICIENT_PERMISSIONS": "You don't have permission to perform this action.",
            "TOKEN_REFRESH_FAILED": "Unable to refresh your session. Please log in again."
        }
        
        message = error_messages.get(error_type, "Authentication failed")
        
        # Log authentication error for monitoring
        await self._log_authentication_error(error_type, context, original_exception)
        
        # Update error statistics
        self._update_error_stats(ErrorCategory.AUTHENTICATION, error_type)
        
        return AuthenticationError(
            message=message,
            error_type=error_type,
            recovery_strategy=recovery_strategy,
            context=context
        )
    
    async def handle_service_error(
        self,
        service_name: str,
        operation: str,
        error: Exception,
        context: Optional[ErrorContext] = None
    ) -> APIError:
        """
        Handle service errors with fallback strategies.
        
        Args:
            service_name: Name of the failing service
            operation: Operation that failed
            error: Original error
            context: Error context
            
        Returns:
            Appropriate API error with recovery strategy
        """
        # Check if service has a degradation strategy
        degradation_strategy = await service_monitor.get_degradation_strategy(service_name)
        
        # Determine error type based on service and error
        if "github" in service_name.lower():
            error_type = "GITHUB_API_ERROR"
            recovery_strategy = self.recovery_strategies.get("SERVICE_UNAVAILABLE")
        elif "llm" in service_name.lower() or "ai" in service_name.lower():
            error_type = "AI_SERVICE_ERROR"
            recovery_strategy = self.recovery_strategies.get("SERVICE_UNAVAILABLE")
        elif "database" in service_name.lower():
            error_type = "DATABASE_ERROR"
            recovery_strategy = self.recovery_strategies.get("DATABASE_ERROR")
        else:
            error_type = "SERVICE_UNAVAILABLE"
            recovery_strategy = self.recovery_strategies.get("SERVICE_UNAVAILABLE")
        
        # Create appropriate error message
        if degradation_strategy:
            message = degradation_strategy.get("message", f"{service_name} is temporarily unavailable")
        else:
            message = f"{service_name} service error during {operation}. Please try again later."
        
        # Log service error
        await self._log_service_error(service_name, operation, error, context)
        
        # Update error statistics
        self._update_error_stats(ErrorCategory.SERVICE_UNAVAILABLE, error_type)
        
        return ServiceUnavailableError(
            service_name=service_name,
            details={
                "operation": operation,
                "error_type": error_type,
                "degradation_strategy": degradation_strategy,
                "recovery_strategy": recovery_strategy.__dict__ if recovery_strategy else None,
                "context": context.__dict__ if context else {}
            }
        )
    
    async def execute_with_retry(
        self,
        operation: Callable,
        error_type: str,
        context: Optional[ErrorContext] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute operation with retry logic based on error type.
        
        Args:
            operation: Function to execute
            error_type: Type of error for recovery strategy
            context: Error context
            *args: Arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Result of successful operation
            
        Raises:
            APIError: If all retries fail
        """
        recovery_strategy = self.recovery_strategies.get(error_type)
        if not recovery_strategy or not recovery_strategy.retry_enabled:
            return await operation(*args, **kwargs)
        
        last_error = None
        retry_count = 0
        
        while retry_count <= recovery_strategy.max_retries:
            try:
                if retry_count > 0:
                    # Calculate exponential backoff delay
                    delay = recovery_strategy.retry_delay * (2 ** (retry_count - 1))
                    await asyncio.sleep(delay)
                
                result = await operation(*args, **kwargs)
                
                # Log successful retry if applicable
                if retry_count > 0:
                    logger.info(f"Operation succeeded after {retry_count} retries")
                
                return result
                
            except Exception as e:
                last_error = e
                retry_count += 1
                
                logger.warning(
                    f"Operation failed (attempt {retry_count}/{recovery_strategy.max_retries + 1}): {str(e)}"
                )
        
        # All retries failed, handle based on strategy
        if recovery_strategy.fallback_enabled and recovery_strategy.fallback_function:
            try:
                logger.info("Attempting fallback operation")
                return await recovery_strategy.fallback_function(*args, **kwargs)
            except Exception as fallback_error:
                logger.error(f"Fallback operation also failed: {str(fallback_error)}")
        
        # Create appropriate error based on type
        if error_type.startswith("AUTH_"):
            raise await self.handle_authentication_error(error_type, context, last_error)
        else:
            raise ServiceUnavailableError(
                service_name="Operation",
                details={
                    "error_type": error_type,
                    "retry_count": retry_count - 1,
                    "last_error": str(last_error),
                    "context": context.__dict__ if context else {}
                }
            )
    
    async def _log_authentication_error(
        self,
        error_type: str,
        context: Optional[ErrorContext],
        original_exception: Optional[Exception]
    ) -> None:
        """Log authentication error for monitoring and security analysis"""
        log_data = {
            "event_type": "authentication_error",
            "error_type": error_type,
            "timestamp": datetime.utcnow().isoformat(),
            "severity": ErrorSeverity.MEDIUM.value
        }
        
        if context:
            log_data.update({
                "user_id": context.user_id,
                "request_id": context.request_id,
                "endpoint": context.endpoint,
                "method": context.method,
                "ip_address": context.ip_address,
                "user_agent": context.user_agent,
                "retry_count": context.retry_count
            })
        
        if original_exception:
            log_data["original_error"] = str(original_exception)
        
        # Log for security monitoring
        logger.warning(f"Authentication error: {error_type}", extra=log_data)
        
        # Check for suspicious patterns
        await self._check_suspicious_activity(error_type, context)
    
    async def _log_service_error(
        self,
        service_name: str,
        operation: str,
        error: Exception,
        context: Optional[ErrorContext]
    ) -> None:
        """Log service error for monitoring and alerting"""
        log_data = {
            "event_type": "service_error",
            "service_name": service_name,
            "operation": operation,
            "error_message": str(error),
            "timestamp": datetime.utcnow().isoformat(),
            "severity": ErrorSeverity.HIGH.value if "database" in service_name.lower() else ErrorSeverity.MEDIUM.value
        }
        
        if context:
            log_data.update({
                "user_id": context.user_id,
                "request_id": context.request_id,
                "endpoint": context.endpoint,
                "method": context.method
            })
        
        logger.error(f"Service error in {service_name}: {operation}", extra=log_data)
    
    async def _check_suspicious_activity(
        self,
        error_type: str,
        context: Optional[ErrorContext]
    ) -> None:
        """Check for suspicious authentication patterns"""
        if not context or not context.ip_address:
            return
        
        # Track failed attempts by IP
        current_time = time.time()
        ip_key = f"auth_failures_{context.ip_address}"
        
        if ip_key not in self.error_patterns:
            self.error_patterns[ip_key] = []
        
        # Add current failure
        self.error_patterns[ip_key].append({
            "timestamp": current_time,
            "error_type": error_type,
            "user_id": context.user_id,
            "endpoint": context.endpoint
        })
        
        # Clean old entries (older than 1 hour)
        self.error_patterns[ip_key] = [
            entry for entry in self.error_patterns[ip_key]
            if current_time - entry["timestamp"] < 3600
        ]
        
        # Check for suspicious patterns
        recent_failures = len(self.error_patterns[ip_key])
        
        if recent_failures >= 10:  # 10 failures in 1 hour
            logger.critical(
                f"Suspicious authentication activity detected from IP {context.ip_address}",
                extra={
                    "event_type": "suspicious_activity",
                    "ip_address": context.ip_address,
                    "failure_count": recent_failures,
                    "time_window": "1_hour",
                    "severity": ErrorSeverity.CRITICAL.value
                }
            )
            
            # Trigger security alert
            await self._trigger_security_alert(context.ip_address, recent_failures)
    
    async def _trigger_security_alert(self, ip_address: str, failure_count: int) -> None:
        """Trigger security alert for suspicious activity"""
        alert_data = {
            "alert_type": "authentication_attack",
            "ip_address": ip_address,
            "failure_count": failure_count,
            "timestamp": datetime.utcnow().isoformat(),
            "severity": ErrorSeverity.CRITICAL.value,
            "recommended_actions": [
                "Consider IP blocking",
                "Review authentication logs",
                "Check for credential stuffing attacks"
            ]
        }
        
        # Log security alert
        security_logger = logging.getLogger("security")
        security_logger.critical(
            f"SECURITY ALERT: Potential authentication attack from {ip_address}",
            extra=alert_data
        )
        
        # In production, send to SIEM or security monitoring system
        # await self._send_to_security_system(alert_data)
    
    def _update_error_stats(self, category: ErrorCategory, error_type: str) -> None:
        """Update error statistics for monitoring"""
        current_time = datetime.utcnow()
        hour_key = current_time.strftime("%Y-%m-%d-%H")
        
        if hour_key not in self.error_stats:
            self.error_stats[hour_key] = {}
        
        if category.value not in self.error_stats[hour_key]:
            self.error_stats[hour_key][category.value] = {}
        
        if error_type not in self.error_stats[hour_key][category.value]:
            self.error_stats[hour_key][category.value][error_type] = 0
        
        self.error_stats[hour_key][category.value][error_type] += 1
        
        # Clean old statistics (keep only last 24 hours)
        cutoff_time = current_time - timedelta(hours=24)
        cutoff_key = cutoff_time.strftime("%Y-%m-%d-%H")
        
        keys_to_remove = [
            key for key in self.error_stats.keys()
            if key < cutoff_key
        ]
        
        for key in keys_to_remove:
            del self.error_stats[key]
    
    def get_error_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get error statistics for the specified time period"""
        current_time = datetime.utcnow()
        stats = {}
        
        for i in range(hours):
            hour_time = current_time - timedelta(hours=i)
            hour_key = hour_time.strftime("%Y-%m-%d-%H")
            
            if hour_key in self.error_stats:
                stats[hour_key] = self.error_stats[hour_key]
        
        return stats
    
    def create_error_context(self, request: Request) -> ErrorContext:
        """Create error context from FastAPI request"""
        return ErrorContext(
            user_id=getattr(request.state, 'user_id', None),
            request_id=getattr(request.state, 'request_id', None),
            endpoint=request.url.path,
            method=request.method,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent'),
            additional_data={
                "query_params": dict(request.query_params),
                "headers": dict(request.headers)
            }
        )


# Global error handling service instance
error_handling_service = ErrorHandlingService()


# Enhanced error handler functions for FastAPI
async def enhanced_authentication_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    """Enhanced handler for authentication errors"""
    context = error_handling_service.create_error_context(request)
    
    response_data = {
        "error": {
            "message": exc.message,
            "code": exc.error_code,
            "category": "authentication",
            "timestamp": datetime.utcnow().isoformat(),
            "recovery_available": exc.recovery_strategy is not None
        }
    }
    
    # Add recovery information if available
    if exc.recovery_strategy:
        response_data["error"]["recovery"] = {
            "strategy": exc.recovery_strategy.strategy_type,
            "user_message": exc.recovery_strategy.user_message,
            "actions": exc.recovery_strategy.recovery_actions,
            "retry_enabled": exc.recovery_strategy.retry_enabled
        }
    
    # Add request ID for tracking
    if context.request_id:
        response_data["error"]["request_id"] = context.request_id
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )


async def enhanced_authorization_error_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    """Enhanced handler for authorization errors"""
    context = error_handling_service.create_error_context(request)
    
    response_data = {
        "error": {
            "message": exc.message,
            "code": exc.error_code,
            "category": "authorization",
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    if exc.required_permission:
        response_data["error"]["required_permission"] = exc.required_permission
    
    if context.request_id:
        response_data["error"]["request_id"] = context.request_id
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )


# Decorator for automatic error handling and recovery
def with_error_handling(error_type: str = "GENERAL_ERROR"):
    """
    Decorator to add automatic error handling and recovery to functions.
    
    Args:
        error_type: Type of error for recovery strategy selection
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Extract request context if available
                context = None
                for arg in args:
                    if hasattr(arg, 'state'):  # FastAPI Request object
                        context = error_handling_service.create_error_context(arg)
                        break
                
                # Handle based on error type
                if isinstance(e, AuthenticationError):
                    raise e
                elif isinstance(e, AuthorizationError):
                    raise e
                elif isinstance(e, APIError):
                    raise e
                else:
                    # Convert to appropriate API error
                    if "auth" in error_type.lower():
                        raise await error_handling_service.handle_authentication_error(
                            error_type, context, e
                        )
                    else:
                        raise await error_handling_service.handle_service_error(
                            "Unknown Service", func.__name__, e, context
                        )
        
        return wrapper
    return decorator