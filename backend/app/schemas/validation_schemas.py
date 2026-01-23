"""
Validation Schemas for API Endpoints
"""

class ValidationRules:
    """Centralized validation rules for all API endpoints."""
    
    USER_REGISTRATION = {
        "email": {"type": "email", "required": True, "max_length": 254},
        "password": {"type": "password", "required": True, "min_length": 8, "max_length": 128}
    }
    
    USER_LOGIN = {
        "email": {"type": "email", "required": True, "max_length": 254},
        "password": {"type": "password", "required": True, "min_length": 1, "max_length": 128}
    }
    
    PROFILE_UPDATE = {
        "email": {"type": "email", "required": False, "max_length": 254},
        "password": {"type": "password", "required": False, "min_length": 8, "max_length": 128}
    }
    
    TOKEN_REFRESH = {
        "refresh_token": {"type": "string", "required": True, "max_length": 500}
    }
    
    PASSWORD_UPDATE = {
        "current_password": {"type": "password", "required": True, "max_length": 128},
        "new_password": {"type": "password", "required": True, "min_length": 8, "max_length": 128}
    }
    
    CREDENTIAL_UPDATE = {
        "github_token": {"type": "string", "required": False, "max_length": 100},
        "ai_api_key": {"type": "string", "required": False, "max_length": 100}
    }
    
    REPOSITORY_DISCOVERY = {
        "concept": {"type": "string", "required": True, "min_length": 3, "max_length": 200}
    }
    
    PROJECT_CREATE = {
        "repository_url": {"type": "url", "required": True, "max_length": 500},
        "architecture": {"type": "string", "required": True, "max_length": 100},
        "language": {"type": "string", "required": True, "max_length": 50}
    }
    
    FILE_CONTENT = {
        "content": {"type": "string", "required": True, "max_length": 100000}
    }
    
    COACH_MESSAGE = {
        "message": {"type": "string", "required": True, "min_length": 1, "max_length": 1000}
    }
    
    GITHUB_ANALYZE = {
        "repository_url": {"type": "url", "required": True, "max_length": 500}
    }
    
    SEARCH_QUERY = {
        "query": {"type": "string", "required": True, "min_length": 1, "max_length": 200}
    }


class ValidationPatterns:
    """Common validation patterns."""
    
    EMAIL = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    GITHUB_TOKEN = r"^gh[ps]_[a-zA-Z0-9]{36}$"
    API_KEY = r"^[a-zA-Z0-9\-_]{20,}$"


class SecurityValidationRules:
    """Security validation rules."""
    
    RATE_LIMITS = {
        "auth_login": {"requests": 5, "window": 300},
        "api_general": {"requests": 100, "window": 60}
    }
