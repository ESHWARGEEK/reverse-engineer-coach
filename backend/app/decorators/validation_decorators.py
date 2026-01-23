"""
Validation decorators for API endpoints
Provides decorators for comprehensive input validation and sanitization.
"""

import functools
import logging
from typing import Dict, Any, Callable, Optional, List
from fastapi import HTTPException, status, Request
from pydantic import BaseModel, ValidationError

from app.services.validation_service import ValidationService, ValidationResult
from app.schemas.validation_schemas import ValidationRules

logger = logging.getLogger(__name__)


def validate_input(
    validation_rules: Optional[Dict[str, Dict[str, Any]]] = None,
    sanitize: bool = True,
    strict: bool = True
):
    """
    Decorator for comprehensive input validation and sanitization.
    
    Args:
        validation_rules: Dictionary of validation rules to apply
        sanitize: Whether to sanitize input data
        strict: Whether to raise exceptions on validation errors
        
    Returns:
        Decorated function with validation applied
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            validation_service = ValidationService()
            
            # Extract request data from kwargs
            request_data = {}
            for key, value in kwargs.items():
                if isinstance(value, BaseModel):
                    request_data.update(value.dict())
                elif isinstance(value, dict):
                    request_data.update(value)
                elif not callable(value) and key not in ['db', 'current_user', 'request']:
                    request_data[key] = value
            
            # Apply validation if rules provided
            if validation_rules:
                sanitized_data, validation_result = validation_service.sanitize_and_validate_input(
                    request_data, validation_rules
                )
                
                if validation_result.has_errors():
                    if strict:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={
                                "message": "Validation failed",
                                "errors": validation_result.errors,
                                "code": "VALIDATION_ERROR"
                            }
                        )
                    else:
                        logger.warning(f"Validation errors in {func.__name__}: {validation_result.errors}")
                
                # Update kwargs with sanitized data if sanitization enabled
                if sanitize and not validation_result.has_errors():
                    for key, value in sanitized_data.items():
                        if key in kwargs:
                            # Update BaseModel instances
                            if isinstance(kwargs[key], BaseModel):
                                for field_name, field_value in sanitized_data.items():
                                    if hasattr(kwargs[key], field_name):
                                        setattr(kwargs[key], field_name, field_value)
                            else:
                                kwargs[key] = value
            
            # Call original function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def validate_json_body(
    max_size: int = 10000,
    required_fields: Optional[List[str]] = None,
    allowed_fields: Optional[List[str]] = None
):
    """
    Decorator for JSON body validation.
    
    Args:
        max_size: Maximum JSON size in characters
        required_fields: List of required fields
        allowed_fields: List of allowed fields (if specified, others are rejected)
        
    Returns:
        Decorated function with JSON validation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            validation_service = ValidationService()
            
            # Find request object in args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                for value in kwargs.values():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if request:
                try:
                    # Read and validate JSON body
                    body = await request.body()
                    if body:
                        import json
                        data = json.loads(body.decode('utf-8'))
                        
                        # Validate JSON size
                        json_result = validation_service.validate_json_input(data, max_size)
                        if json_result.has_errors():
                            raise HTTPException(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=json_result.errors
                            )
                        
                        # Check required fields
                        if required_fields:
                            missing_fields = [field for field in required_fields if field not in data]
                            if missing_fields:
                                raise HTTPException(
                                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail=f"Missing required fields: {', '.join(missing_fields)}"
                                )
                        
                        # Check allowed fields
                        if allowed_fields:
                            invalid_fields = [field for field in data.keys() if field not in allowed_fields]
                            if invalid_fields:
                                raise HTTPException(
                                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail=f"Invalid fields: {', '.join(invalid_fields)}"
                                )
                
                except json.JSONDecodeError:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Invalid JSON format"
                    )
                except UnicodeDecodeError:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Invalid request encoding"
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def validate_query_params(
    allowed_params: Optional[List[str]] = None,
    required_params: Optional[List[str]] = None,
    param_validators: Optional[Dict[str, Callable]] = None
):
    """
    Decorator for query parameter validation.
    
    Args:
        allowed_params: List of allowed query parameters
        required_params: List of required query parameters
        param_validators: Dictionary of parameter validators
        
    Returns:
        Decorated function with query parameter validation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            validation_service = ValidationService()
            
            # Find request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                for value in kwargs.values():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if request:
                query_params = dict(request.query_params)
                
                # Check allowed parameters
                if allowed_params:
                    invalid_params = [param for param in query_params.keys() if param not in allowed_params]
                    if invalid_params:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Invalid query parameters: {', '.join(invalid_params)}"
                        )
                
                # Check required parameters
                if required_params:
                    missing_params = [param for param in required_params if param not in query_params]
                    if missing_params:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Missing required parameters: {', '.join(missing_params)}"
                        )
                
                # Apply custom validators
                if param_validators:
                    for param_name, validator in param_validators.items():
                        if param_name in query_params:
                            try:
                                validator(query_params[param_name])
                            except ValueError as e:
                                raise HTTPException(
                                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail=f"Invalid parameter {param_name}: {str(e)}"
                                )
                
                # General validation for all parameters
                for param_name, param_value in query_params.items():
                    # Check for injection attempts
                    if validation_service.sanitizer.check_sql_injection(param_value):
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Invalid parameter value: {param_name}"
                        )
                    
                    # Check for XSS attempts
                    if validation_service.detect_xss_attempt(param_value):
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Invalid parameter content: {param_name}"
                        )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def validate_file_upload(
    max_size: int = 10 * 1024 * 1024,  # 10MB
    allowed_extensions: Optional[List[str]] = None,
    allowed_mime_types: Optional[List[str]] = None
):
    """
    Decorator for file upload validation.
    
    Args:
        max_size: Maximum file size in bytes
        allowed_extensions: List of allowed file extensions
        allowed_mime_types: List of allowed MIME types
        
    Returns:
        Decorated function with file upload validation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            validation_service = ValidationService()
            
            # Find uploaded file in kwargs
            uploaded_file = None
            for key, value in kwargs.items():
                if hasattr(value, 'filename') and hasattr(value, 'file'):
                    uploaded_file = value
                    break
            
            if uploaded_file:
                # Read file content
                file_content = await uploaded_file.read()
                file_size = len(file_content)
                filename = uploaded_file.filename or "unknown"
                
                # Reset file pointer
                await uploaded_file.seek(0)
                
                # Validate file upload
                validation_result = validation_service.validate_file_upload(
                    filename=filename,
                    file_size=file_size,
                    file_content=file_content,
                    allowed_types=allowed_extensions
                )
                
                if validation_result.has_errors():
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=validation_result.errors
                    )
                
                # Additional MIME type validation
                if allowed_mime_types and hasattr(uploaded_file, 'content_type'):
                    if uploaded_file.content_type not in allowed_mime_types:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"File type {uploaded_file.content_type} not allowed"
                        )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def sanitize_output(
    fields_to_mask: Optional[List[str]] = None,
    remove_sensitive: bool = True
):
    """
    Decorator for sanitizing output data.
    
    Args:
        fields_to_mask: List of fields to mask in output
        remove_sensitive: Whether to remove sensitive fields
        
    Returns:
        Decorated function with output sanitization
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Sanitize result if it's a dictionary
            if isinstance(result, dict):
                sanitized_result = result.copy()
                
                # Mask specified fields
                if fields_to_mask:
                    for field in fields_to_mask:
                        if field in sanitized_result:
                            value = sanitized_result[field]
                            if isinstance(value, str) and len(value) > 8:
                                sanitized_result[field] = f"{value[:4]}****{value[-4:]}"
                            else:
                                sanitized_result[field] = "****"
                
                # Remove sensitive fields
                if remove_sensitive:
                    sensitive_fields = [
                        'password', 'password_hash', 'secret', 'token', 
                        'api_key', 'private_key', 'encryption_key'
                    ]
                    for field in sensitive_fields:
                        if field in sanitized_result:
                            del sanitized_result[field]
                
                return sanitized_result
            
            return result
        
        return wrapper
    return decorator


def rate_limit(
    max_requests: int = 100,
    window_seconds: int = 60,
    key_func: Optional[Callable] = None
):
    """
    Decorator for rate limiting API endpoints.
    
    Args:
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
        key_func: Function to generate rate limit key
        
    Returns:
        Decorated function with rate limiting
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # This is a placeholder for rate limiting logic
            # In production, this would integrate with Redis or similar
            
            # Find request object to get client IP
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request:
                # Generate rate limit key
                if key_func:
                    rate_key = key_func(request)
                else:
                    rate_key = request.client.host if request.client else "unknown"
                
                # TODO: Implement actual rate limiting logic with Redis
                # For now, just log the rate limit check
                logger.debug(f"Rate limit check for key: {rate_key}")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Predefined validation decorators for common use cases
validate_auth_registration = validate_input(ValidationRules.USER_REGISTRATION)
validate_auth_login = validate_input(ValidationRules.USER_LOGIN)
validate_profile_update = validate_input(ValidationRules.PROFILE_UPDATE)
validate_repository_discovery = validate_input(ValidationRules.REPOSITORY_DISCOVERY)
validate_project_creation = validate_input(ValidationRules.PROJECT_CREATE)

# File upload decorators
validate_code_upload = validate_file_upload(
    max_size=1024*1024,  # 1MB
    allowed_extensions=['.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs']
)

validate_config_upload = validate_file_upload(
    max_size=512*1024,  # 512KB
    allowed_extensions=['.json', '.yaml', '.yml', '.toml', '.ini']
)

# Output sanitization decorators
mask_credentials = sanitize_output(
    fields_to_mask=['github_token', 'ai_api_key', 'api_key', 'token'],
    remove_sensitive=True
)