"""
System Credentials Service
Provides access to system-wide API credentials from environment variables.
"""

import os
from typing import Optional
from app.config import settings


class SystemCredentialsService:
    """Service for accessing system-wide API credentials."""
    
    @staticmethod
    def get_github_token() -> Optional[str]:
        """
        Get the system GitHub token from environment variables.
        
        Returns:
            GitHub token or None if not configured
        """
        # Try multiple environment variable names for flexibility
        token = (
            os.getenv("SYSTEM_GITHUB_TOKEN") or 
            os.getenv("GITHUB_TOKEN") or 
            settings.system_github_token or
            settings.github_token
        )
        return token if token and token != "" else None
    
    @staticmethod
    def get_gemini_api_key() -> Optional[str]:
        """
        Get the system Gemini API key from environment variables.
        
        Returns:
            Gemini API key or None if not configured
        """
        # Try multiple environment variable names for flexibility
        api_key = (
            os.getenv("SYSTEM_GEMINI_API_KEY") or 
            os.getenv("GEMINI_API_KEY") or 
            settings.system_gemini_api_key or
            settings.gemini_api_key
        )
        return api_key if api_key and api_key != "" else None
    
    @staticmethod
    def get_openai_api_key() -> Optional[str]:
        """
        Get the system OpenAI API key from environment variables.
        
        Returns:
            OpenAI API key or None if not configured
        """
        # Try multiple environment variable names for flexibility
        api_key = (
            os.getenv("SYSTEM_OPENAI_API_KEY") or 
            os.getenv("OPENAI_API_KEY") or 
            settings.openai_api_key
        )
        return api_key if api_key and api_key != "" else None
    
    @staticmethod
    def get_credentials_for_user(preferred_ai_provider: str = "gemini") -> dict:
        """
        Get all available system credentials for a user.
        
        Args:
            preferred_ai_provider: User's preferred AI provider
            
        Returns:
            Dictionary with available credentials
        """
        credentials = {
            "github_token": SystemCredentialsService.get_github_token(),
            "preferred_ai_provider": preferred_ai_provider
        }
        
        if preferred_ai_provider == "gemini":
            credentials["ai_api_key"] = SystemCredentialsService.get_gemini_api_key()
        elif preferred_ai_provider == "openai":
            credentials["ai_api_key"] = SystemCredentialsService.get_openai_api_key()
        else:
            # Default to Gemini
            credentials["ai_api_key"] = SystemCredentialsService.get_gemini_api_key()
            credentials["preferred_ai_provider"] = "gemini"
        
        return credentials
    
    @staticmethod
    def validate_system_credentials() -> dict:
        """
        Validate that required system credentials are available.
        
        Returns:
            Dictionary with validation results
        """
        github_token = SystemCredentialsService.get_github_token()
        gemini_key = SystemCredentialsService.get_gemini_api_key()
        openai_key = SystemCredentialsService.get_openai_api_key()
        
        return {
            "github_token_available": bool(github_token),
            "gemini_api_key_available": bool(gemini_key),
            "openai_api_key_available": bool(openai_key),
            "has_ai_provider": bool(gemini_key or openai_key),
            "recommended_ai_provider": "gemini" if gemini_key else ("openai" if openai_key else None)
        }