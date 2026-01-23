"""
Logging Configuration

Centralized logging configuration for the application with structured logging,
multiple handlers, and integration with monitoring systems.
"""

import os
import sys
import logging
import logging.config
from datetime import datetime
from typing import Dict, Any
import json

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        
        # Base log data
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from the record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in [
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'message'
            ]:
                extra_fields[key] = value
        
        if extra_fields:
            log_data["extra"] = extra_fields
        
        return json.dumps(log_data, default=str)

class SecurityFilter(logging.Filter):
    """Filter to prevent logging of sensitive information"""
    
    SENSITIVE_PATTERNS = [
        'password', 'token', 'key', 'secret', 'credential',
        'authorization', 'bearer', 'jwt', 'api_key'
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out sensitive information from log records"""
        
        # Check message for sensitive patterns
        message = record.getMessage().lower()
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in message:
                # Mask the sensitive information
                record.msg = "[SENSITIVE DATA MASKED]"
                record.args = ()
                break
        
        # Check extra fields for sensitive data
        if hasattr(record, 'extra') and isinstance(record.extra, dict):
            for key, value in record.extra.items():
                if any(pattern in key.lower() for pattern in self.SENSITIVE_PATTERNS):
                    record.extra[key] = "[MASKED]"
        
        return True

def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration dictionary"""
    
    # Get configuration from environment
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "json").lower()
    enable_access_logs = os.getenv("ENABLE_ACCESS_LOGS", "true").lower() == "true"
    enable_error_tracking = os.getenv("ENABLE_ERROR_TRACKING", "true").lower() == "true"
    
    # Determine log directory
    log_dir = os.getenv("LOG_DIR", "/var/log/reverse-coach")
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except PermissionError:
            # Fallback to local logs directory
            log_dir = "./logs"
            os.makedirs(log_dir, exist_ok=True)
    
    # Base formatters
    formatters = {
        "json": {
            "()": JSONFormatter,
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
        "simple": {
            "format": "%(levelname)s - %(name)s - %(message)s"
        }
    }
    
    # Base filters
    filters = {
        "security_filter": {
            "()": SecurityFilter,
        }
    }
    
    # Base handlers
    handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": log_format if log_format in formatters else "json",
            "filters": ["security_filter"],
            "stream": sys.stdout
        },
        "file_all": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": log_format if log_format in formatters else "json",
            "filters": ["security_filter"],
            "filename": os.path.join(log_dir, "application.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf8"
        },
        "file_error": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": log_format if log_format in formatters else "json",
            "filters": ["security_filter"],
            "filename": os.path.join(log_dir, "error.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "encoding": "utf8"
        }
    }
    
    # Add access log handler if enabled
    if enable_access_logs:
        handlers["file_access"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": log_format if log_format in formatters else "json",
            "filename": os.path.join(log_dir, "access.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf8"
        }
    
    # Add security log handler
    handlers["file_security"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "level": "WARNING",
        "formatter": log_format if log_format in formatters else "json",
        "filename": os.path.join(log_dir, "security.log"),
        "maxBytes": 10485760,  # 10MB
        "backupCount": 10,
        "encoding": "utf8"
    }
    
    # Add performance log handler
    handlers["file_performance"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "level": "DEBUG",
        "formatter": log_format if log_format in formatters else "json",
        "filename": os.path.join(log_dir, "performance.log"),
        "maxBytes": 10485760,  # 10MB
        "backupCount": 5,
        "encoding": "utf8"
    }
    
    # Add analytics log handler
    handlers["file_analytics"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "level": "INFO",
        "formatter": log_format if log_format in formatters else "json",
        "filename": os.path.join(log_dir, "analytics.log"),
        "maxBytes": 10485760,  # 10MB
        "backupCount": 5,
        "encoding": "utf8"
    }
    
    # Logger configuration
    loggers = {
        # Root logger
        "": {
            "level": log_level,
            "handlers": ["console", "file_all", "file_error"],
            "propagate": False
        },
        
        # Application loggers
        "app": {
            "level": log_level,
            "handlers": ["console", "file_all"],
            "propagate": False
        },
        
        # Authentication events
        "auth_events": {
            "level": "INFO",
            "handlers": ["file_security", "console"],
            "propagate": False
        },
        
        # Security monitoring
        "security": {
            "level": "WARNING",
            "handlers": ["file_security", "console"],
            "propagate": False
        },
        
        # Performance monitoring
        "performance_monitoring": {
            "level": "DEBUG",
            "handlers": ["file_performance"],
            "propagate": False
        },
        
        # User analytics
        "user_analytics": {
            "level": "INFO",
            "handlers": ["file_analytics"],
            "propagate": False
        },
        
        # FastAPI access logs
        "uvicorn.access": {
            "level": "INFO",
            "handlers": ["file_access"] if enable_access_logs else [],
            "propagate": False
        },
        
        # Database logs
        "sqlalchemy.engine": {
            "level": "WARNING",
            "handlers": ["file_all"],
            "propagate": False
        },
        
        # Redis logs
        "redis": {
            "level": "WARNING",
            "handlers": ["file_all"],
            "propagate": False
        }
    }
    
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "filters": filters,
        "handlers": handlers,
        "loggers": loggers
    }

def setup_logging():
    """Setup logging configuration"""
    
    config = get_logging_config()
    logging.config.dictConfig(config)
    
    # Log startup message
    logger = logging.getLogger("app")
    logger.info("Logging configuration initialized", extra={
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "log_format": os.getenv("LOG_FORMAT", "json"),
        "log_dir": os.getenv("LOG_DIR", "/var/log/reverse-coach")
    })

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name"""
    return logging.getLogger(name)

# Convenience functions for different log types
def get_app_logger() -> logging.Logger:
    """Get application logger"""
    return logging.getLogger("app")

def get_auth_logger() -> logging.Logger:
    """Get authentication events logger"""
    return logging.getLogger("auth_events")

def get_security_logger() -> logging.Logger:
    """Get security logger"""
    return logging.getLogger("security")

def get_performance_logger() -> logging.Logger:
    """Get performance monitoring logger"""
    return logging.getLogger("performance_monitoring")

def get_analytics_logger() -> logging.Logger:
    """Get user analytics logger"""
    return logging.getLogger("user_analytics")

# Initialize logging when module is imported
if __name__ != "__main__":
    setup_logging()