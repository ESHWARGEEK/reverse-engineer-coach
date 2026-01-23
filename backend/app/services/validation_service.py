"""
Comprehensive Input Validation Service
Provides server-side validation for all user inputs with SQL injection prevention
and input sanitization.
"""

import re
import html
import bleach
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, validator, EmailStr
from urllib.parse import urlparse
import ipaddress
from datetime import datetime


class ValidationError(Exception):
    """Custom validation error with detailed information."""
    
    def __init__(self, field: str, message: str, code: str = "VALIDATION_ERROR"):
        self.field = field
        self.message = message
        self.code = code
        super().__init__(f"{field}: {message}")


class ValidationResult:
    """Result of validation with success status and errors."""
    
    def __init__(self, is_valid: bool = True, errors: Optional[Dict[str, str]] = None):
        self.is_valid = is_valid
        self.errors = errors or {}
    
    def add_error(self, field: str, message: str):
        """Add validation error."""
        self.is_valid = False
        self.errors[field] = message
    
    def has_errors(self) -> bool:
        """Check if validation has errors."""
        return not self.is_valid or bool(self.errors)


class InputSanitizer:
    """Input sanitization utilities."""
    
    # Allowed HTML tags for rich text (very restrictive)
    ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li']
    ALLOWED_ATTRIBUTES = {}
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(\b(UNION|OR|AND)\s+\d+\s*=\s*\d+)",
        r"(--|#|/\*|\*/)",
        r"(\bxp_cmdshell\b)",
        r"(\bsp_executesql\b)",
        r"('(\s*|\s*\w+\s*)(=|<|>|!=))",
    ]
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize string input by removing dangerous characters and HTML.
        
        Args:
            value: Input string to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return str(value)
        
        # HTML escape
        sanitized = html.escape(value.strip())
        
        # Remove null bytes and control characters
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)
        
        # Truncate if needed
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized
    
    @classmethod
    def sanitize_html(cls, value: str) -> str:
        """
        Sanitize HTML content allowing only safe tags.
        
        Args:
            value: HTML content to sanitize
            
        Returns:
            Sanitized HTML
        """
        return bleach.clean(
            value,
            tags=cls.ALLOWED_TAGS,
            attributes=cls.ALLOWED_ATTRIBUTES,
            strip=True
        )
    
    @classmethod
    def check_sql_injection(cls, value: str) -> bool:
        """
        Check if string contains potential SQL injection patterns.
        
        Args:
            value: String to check
            
        Returns:
            True if potential SQL injection detected
        """
        value_lower = value.lower()
        
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        
        return False
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        Sanitize filename to prevent directory traversal and other attacks.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove path separators and dangerous characters
        sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
        
        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip('. ')
        
        # Prevent reserved names on Windows
        reserved_names = [
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        ]
        
        if sanitized.upper() in reserved_names:
            sanitized = f"file_{sanitized}"
        
        # Ensure minimum length
        if len(sanitized) < 1:
            sanitized = "file"
        
        return sanitized


class ValidationService:
    """Comprehensive validation service for all user inputs."""
    
    def __init__(self):
        self.sanitizer = InputSanitizer()
    
    def validate_email(self, email: str) -> ValidationResult:
        """
        Validate email address format and security.
        
        Args:
            email: Email address to validate
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult()
        
        if not email:
            result.add_error("email", "Email address is required")
            return result
        
        # Sanitize input
        email = self.sanitizer.sanitize_string(email, max_length=254)
        
        # Check for SQL injection
        if self.sanitizer.check_sql_injection(email):
            result.add_error("email", "Invalid email format")
            return result
        
        # Basic email format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            result.add_error("email", "Invalid email format")
            return result
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'[<>"\']',  # HTML/script injection
            r'javascript:',  # JavaScript injection
            r'data:',  # Data URI
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, email, re.IGNORECASE):
                result.add_error("email", "Invalid email format")
                return result
        
        return result
    
    def validate_password(self, password: str) -> ValidationResult:
        """
        Validate password strength and security.
        
        Args:
            password: Password to validate
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult()
        
        if not password:
            result.add_error("password", "Password is required")
            return result
        
        # Check minimum length
        if len(password) < 8:
            result.add_error("password", "Password must be at least 8 characters long")
        
        # Check maximum length (prevent DoS)
        if len(password) > 128:
            result.add_error("password", "Password must be less than 128 characters")
        
        # Check for required character types
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
        
        missing_types = []
        if not has_upper:
            missing_types.append("uppercase letter")
        if not has_lower:
            missing_types.append("lowercase letter")
        if not has_digit:
            missing_types.append("number")
        if not has_special:
            missing_types.append("special character")
        
        if missing_types:
            result.add_error(
                "password", 
                f"Password must contain at least one: {', '.join(missing_types)}"
            )
        
        # Check for common weak patterns
        weak_patterns = [
            r'(.)\1{3,}',  # Repeated characters (aaaa)
            r'(012|123|234|345|456|567|678|789|890)',  # Sequential numbers
            r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)',  # Sequential letters
        ]
        
        for pattern in weak_patterns:
            if re.search(pattern, password.lower()):
                result.add_error("password", "Password contains weak patterns")
                break
        
        return result
    
    def validate_url(self, url: str, allowed_schemes: Optional[List[str]] = None) -> ValidationResult:
        """
        Validate URL format and security.
        
        Args:
            url: URL to validate
            allowed_schemes: List of allowed URL schemes (default: ['http', 'https'])
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult()
        
        if not url:
            result.add_error("url", "URL is required")
            return result
        
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
        
        # Sanitize input
        url = self.sanitizer.sanitize_string(url, max_length=2048)
        
        # Check for SQL injection
        if self.sanitizer.check_sql_injection(url):
            result.add_error("url", "Invalid URL format")
            return result
        
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in allowed_schemes:
                result.add_error("url", f"URL scheme must be one of: {', '.join(allowed_schemes)}")
            
            # Check for valid hostname
            if not parsed.netloc:
                result.add_error("url", "URL must have a valid hostname")
            
            # Check for suspicious patterns
            suspicious_patterns = [
                r'javascript:',  # JavaScript injection
                r'data:',  # Data URI
                r'file:',  # File URI
                r'ftp:',  # FTP (if not allowed)
            ]
            
            for pattern in suspicious_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    result.add_error("url", "Invalid URL format")
                    break
            
            # Check for private IP addresses (optional security measure)
            try:
                # Extract hostname without port
                hostname = parsed.hostname
                if hostname:
                    ip = ipaddress.ip_address(hostname)
                    if ip.is_private or ip.is_loopback:
                        result.add_error("url", "Private IP addresses are not allowed")
            except (ValueError, ipaddress.AddressValueError):
                # Not an IP address, which is fine
                pass
            
        except Exception:
            result.add_error("url", "Invalid URL format")
        
        return result
    
    def validate_github_url(self, url: str) -> ValidationResult:
        """
        Validate GitHub repository URL.
        
        Args:
            url: GitHub URL to validate
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult()
        
        if not url:
            result.add_error("github_url", "GitHub URL is required")
            return result
        
        # First validate as general URL
        url_result = self.validate_url(url, allowed_schemes=['https'])
        if url_result.has_errors():
            result.errors.update(url_result.errors)
            return result
        
        # Check if it's a GitHub URL
        github_pattern = r'^https://github\.com/[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+/?$'
        if not re.match(github_pattern, url.rstrip('/')):
            result.add_error("github_url", "Must be a valid GitHub repository URL")
        
        return result
    
    def validate_api_key(self, api_key: str, key_type: str) -> ValidationResult:
        """
        Validate API key format.
        
        Args:
            api_key: API key to validate
            key_type: Type of API key ('github', 'openai', 'gemini')
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult()
        
        if not api_key:
            result.add_error("api_key", f"{key_type.title()} API key is required")
            return result
        
        # Sanitize input
        api_key = self.sanitizer.sanitize_string(api_key, max_length=512)
        
        # Check for SQL injection
        if self.sanitizer.check_sql_injection(api_key):
            result.add_error("api_key", "Invalid API key format")
            return result
        
        # Validate based on key type
        if key_type == 'github':
            # GitHub personal access tokens
            github_patterns = [
                r'^ghp_[a-zA-Z0-9]{36}$',  # Personal access token
                r'^gho_[a-zA-Z0-9]{36}$',  # OAuth token
                r'^ghu_[a-zA-Z0-9]{36}$',  # User token
                r'^ghs_[a-zA-Z0-9]{36}$',  # Server token
                r'^ghr_[a-zA-Z0-9]{36}$',  # Refresh token
            ]
            
            if not any(re.match(pattern, api_key) for pattern in github_patterns):
                result.add_error("api_key", "Invalid GitHub API key format")
        
        elif key_type == 'openai':
            # OpenAI API keys
            if not re.match(r'^sk-[a-zA-Z0-9]{48}$', api_key):
                result.add_error("api_key", "Invalid OpenAI API key format")
        
        elif key_type == 'gemini':
            # Google Gemini API keys
            if not re.match(r'^[a-zA-Z0-9_-]{39}$', api_key):
                result.add_error("api_key", "Invalid Gemini API key format")
        
        else:
            result.add_error("api_key", f"Unknown API key type: {key_type}")
        
        return result
    
    def validate_filename(self, filename: str) -> ValidationResult:
        """
        Validate filename for security and format.
        
        Args:
            filename: Filename to validate
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult()
        
        if not filename:
            result.add_error("filename", "Filename is required")
            return result
        
        # Sanitize filename
        sanitized = self.sanitizer.sanitize_filename(filename)
        
        # Check for path traversal attempts
        path_traversal_patterns = [
            r'\.\./+',
            r'\.\.\\+',
            r'%2e%2e%2f',
            r'%2e%2e\\',
        ]
        
        for pattern in path_traversal_patterns:
            if re.search(pattern, filename, re.IGNORECASE):
                result.add_error("filename", "Invalid filename: path traversal detected")
                break
        
        # Check for dangerous extensions
        dangerous_extensions = [
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
            '.jar', '.app', '.deb', '.pkg', '.dmg', '.iso', '.msi'
        ]
        
        file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
        if f'.{file_ext}' in dangerous_extensions:
            result.add_error("filename", f"File type '.{file_ext}' is not allowed")
        
        # Check filename length
        if len(sanitized) > 255:
            result.add_error("filename", "Filename too long (max 255 characters)")
        
        if len(sanitized) < 1:
            result.add_error("filename", "Filename cannot be empty")
        
        return result
    
    def validate_ip_address(self, ip_address: str) -> ValidationResult:
        """
        Validate IP address format.
        
        Args:
            ip_address: IP address to validate
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult()
        
        if not ip_address:
            result.add_error("ip_address", "IP address is required")
            return result
        
        try:
            import ipaddress
            ip = ipaddress.ip_address(ip_address)
            
            # Check for private/loopback addresses if needed
            if ip.is_private or ip.is_loopback:
                # This might be acceptable depending on use case
                pass
                
        except ValueError:
            result.add_error("ip_address", "Invalid IP address format")
        
        return result
    
    def validate_integer_input(
        self, 
        value: Any, 
        field_name: str,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None
    ) -> ValidationResult:
        """
        Validate integer input with range checking.
        
        Args:
            value: Value to validate
            field_name: Name of the field
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult()
        
        try:
            int_value = int(value)
            
            if min_value is not None and int_value < min_value:
                result.add_error(field_name, f"{field_name.title()} must be at least {min_value}")
            
            if max_value is not None and int_value > max_value:
                result.add_error(field_name, f"{field_name.title()} must be at most {max_value}")
                
        except (ValueError, TypeError):
            result.add_error(field_name, f"{field_name.title()} must be a valid integer")
        
        return result
    
    def validate_file_upload(
        self, 
        filename: str, 
        file_size: int, 
        file_content: bytes,
        allowed_types: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        Comprehensive file upload validation.
        
        Args:
            filename: Name of uploaded file
            file_size: Size of file in bytes
            file_content: File content as bytes
            allowed_types: List of allowed file types
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult()
        
        # Validate filename
        filename_result = self.validate_filename(filename)
        if filename_result.has_errors():
            result.errors.update(filename_result.errors)
        
        # Validate file size
        max_size = 10 * 1024 * 1024  # 10MB default
        if file_size > max_size:
            result.add_error("file_size", f"File too large (max {max_size // (1024*1024)}MB)")
        
        if file_size <= 0:
            result.add_error("file_size", "File cannot be empty")
        
        # Validate file type if specified
        if allowed_types:
            file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
            if f'.{file_ext}' not in allowed_types:
                result.add_error("file_type", f"File type '.{file_ext}' not allowed")
        
        # Check for malicious content patterns
        try:
            content_str = file_content.decode('utf-8', errors='ignore')
            
            # Check for script injection in file content
            malicious_patterns = [
                r'<script[^>]*>.*?</script>',
                r'javascript:',
                r'eval\s*\(',
                r'exec\s*\(',
                r'system\s*\(',
                r'shell_exec\s*\(',
            ]
            
            for pattern in malicious_patterns:
                if re.search(pattern, content_str, re.IGNORECASE):
                    result.add_error("file_content", "File contains potentially malicious content")
                    break
                    
        except Exception:
            # If we can't decode the file, it might be binary, which is okay
            pass
        
        return result
    
    def detect_xss_attempt(self, content: str) -> bool:
        """
        Detect potential XSS (Cross-Site Scripting) attempts.
        
        Args:
            content: Content to check
            
        Returns:
            True if XSS attempt detected
        """
        xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'data:.*base64',
            r'<iframe[^>]*>.*?</iframe>',
            r'<object[^>]*>.*?</object>',
            r'<embed[^>]*>.*?</embed>',
            r'<link[^>]*>',
            r'<meta[^>]*>',
            r'expression\s*\(',
            r'url\s*\(',
            r'@import',
        ]
        
        content_lower = content.lower()
        
        for pattern in xss_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return True
        
        return False
    
    def validate_user_agent(self, user_agent: str) -> ValidationResult:
        """
        Validate user agent string and detect suspicious patterns.
        
        Args:
            user_agent: User agent string
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult()
        
        if not user_agent:
            result.add_error("user_agent", "User agent is required")
            return result
        
        # Check for blocked user agents (bots, scrapers)
        blocked_patterns = [
            r'.*bot.*',
            r'.*crawler.*',
            r'.*spider.*',
            r'.*scraper.*',
            r'^curl',
            r'^wget',
            r'.*python.*',
            r'.*java.*',
        ]
        
        user_agent_lower = user_agent.lower()
        
        for pattern in blocked_patterns:
            if re.search(pattern, user_agent_lower):
                result.add_error("user_agent", "Automated requests not allowed")
                break
        
        # Check for suspicious patterns
        if len(user_agent) > 500:
            result.add_error("user_agent", "User agent string too long")
        
        if self.sanitizer.check_sql_injection(user_agent):
            result.add_error("user_agent", "Invalid user agent format")
        
        return result
    
    def validate_request_headers(self, headers: dict) -> ValidationResult:
        """
        Validate HTTP request headers for security.
        
        Args:
            headers: Dictionary of HTTP headers
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult()
        
        # Check for suspicious headers
        suspicious_headers = [
            'x-forwarded-for',
            'x-real-ip',
            'x-originating-ip',
            'x-remote-ip',
            'x-cluster-client-ip'
        ]
        
        for header_name, header_value in headers.items():
            header_name_lower = header_name.lower()
            
            # Check for header injection
            if '\n' in header_value or '\r' in header_value:
                result.add_error("headers", f"Header injection detected in {header_name}")
            
            # Check for suspicious header values
            if header_name_lower in suspicious_headers:
                # Validate IP addresses in forwarding headers
                if header_name_lower in ['x-forwarded-for', 'x-real-ip']:
                    ip_result = self.validate_ip_address(header_value.split(',')[0].strip())
                    if ip_result.has_errors():
                        result.add_error("headers", f"Invalid IP in {header_name}")
            
            # Check for overly long header values
            if len(header_value) > 8192:  # 8KB limit
                result.add_error("headers", f"Header {header_name} too long")
        
        return result
    
    def validate_text_input(
        self, 
        text: str, 
        field_name: str,
        min_length: int = 0,
        max_length: int = 1000,
        allow_html: bool = False
    ) -> ValidationResult:
        """
        Validate general text input with customizable constraints.
        
        Args:
            text: Text to validate
            field_name: Name of the field for error messages
            min_length: Minimum required length
            max_length: Maximum allowed length
            allow_html: Whether to allow HTML content
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult()
        
        if text is None:
            text = ""
        
        # Check minimum length
        if len(text.strip()) < min_length:
            if min_length > 0:
                result.add_error(field_name, f"{field_name.title()} must be at least {min_length} characters")
            else:
                result.add_error(field_name, f"{field_name.title()} is required")
        
        # Check maximum length
        if len(text) > max_length:
            result.add_error(field_name, f"{field_name.title()} must be less than {max_length} characters")
        
        # Check for SQL injection
        if self.sanitizer.check_sql_injection(text):
            result.add_error(field_name, f"Invalid {field_name} format")
        
        # Sanitize based on HTML allowance
        if allow_html:
            # Allow limited HTML
            sanitized = self.sanitizer.sanitize_html(text)
        else:
            # No HTML allowed
            sanitized = self.sanitizer.sanitize_string(text, max_length)
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',  # JavaScript URLs
            r'on\w+\s*=',  # Event handlers
            r'data:.*base64',  # Base64 data URIs
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                result.add_error(field_name, f"Invalid {field_name} content")
                break
        
        return result
    
    def validate_json_input(self, data: Any, max_size: int = 10000) -> ValidationResult:
        """
        Validate JSON input for size and structure.
        
        Args:
            data: JSON data to validate
            max_size: Maximum size in characters when serialized
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult()
        
        try:
            import json
            
            # Serialize to check size
            json_str = json.dumps(data)
            
            if len(json_str) > max_size:
                result.add_error("json_data", f"JSON data too large (max {max_size} characters)")
            
            # Check for suspicious content in JSON strings
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, str):
                        if self.sanitizer.check_sql_injection(value):
                            result.add_error("json_data", "Invalid content in JSON data")
                            break
            
        except (TypeError, ValueError):
            result.add_error("json_data", "Invalid JSON format")
        
        return result
    
    def sanitize_and_validate_input(
        self, 
        data: Dict[str, Any], 
        validation_rules: Dict[str, Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], ValidationResult]:
        """
        Sanitize and validate input data based on rules.
        
        Args:
            data: Input data to validate
            validation_rules: Dictionary of field validation rules
            
        Returns:
            Tuple of (sanitized_data, validation_result)
        """
        sanitized_data = {}
        result = ValidationResult()
        
        for field, rules in validation_rules.items():
            value = data.get(field)
            
            # Apply validation based on field type
            field_type = rules.get('type', 'string')
            required = rules.get('required', False)
            
            if value is None or value == "":
                if required:
                    result.add_error(field, f"{field.title()} is required")
                continue
            
            if field_type == 'email':
                email_result = self.validate_email(value)
                if email_result.has_errors():
                    result.errors.update(email_result.errors)
                else:
                    sanitized_data[field] = self.sanitizer.sanitize_string(value, 254)
            
            elif field_type == 'password':
                password_result = self.validate_password(value)
                if password_result.has_errors():
                    result.errors.update(password_result.errors)
                else:
                    sanitized_data[field] = value  # Don't sanitize passwords
            
            elif field_type == 'url':
                url_result = self.validate_url(value)
                if url_result.has_errors():
                    result.errors.update(url_result.errors)
                else:
                    sanitized_data[field] = self.sanitizer.sanitize_string(value, 2048)
            
            elif field_type == 'text':
                min_length = rules.get('min_length', 0)
                max_length = rules.get('max_length', 1000)
                allow_html = rules.get('allow_html', False)
                
                text_result = self.validate_text_input(
                    value, field, min_length, max_length, allow_html
                )
                if text_result.has_errors():
                    result.errors.update(text_result.errors)
                else:
                    if allow_html:
                        sanitized_data[field] = self.sanitizer.sanitize_html(value)
                    else:
                        sanitized_data[field] = self.sanitizer.sanitize_string(value, max_length)
            
            elif field_type == 'api_key':
                key_type = rules.get('key_type', 'unknown')
                api_key_result = self.validate_api_key(value, key_type)
                if api_key_result.has_errors():
                    result.errors.update(api_key_result.errors)
                else:
                    sanitized_data[field] = value  # Don't sanitize API keys
            
            else:
                # Default string handling
                sanitized_data[field] = self.sanitizer.sanitize_string(
                    str(value), 
                    rules.get('max_length', 1000)
                )
        
        return sanitized_data, result


# Global validation service instance
validation_service = ValidationService()