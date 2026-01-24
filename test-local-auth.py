#!/usr/bin/env python3
"""
Test the simplified authentication locally to identify the issue.
"""

import sys
import os

# Add the backend directory to Python path
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

try:
    from app.services.auth_service import AuthService, UserRegistrationRequest
    from app.services.password_service import PasswordService
    
    def test_auth_service():
        """Test the auth service directly."""
        print("Testing AuthService locally...")
        
        try:
            # Test password service first
            password_service = PasswordService()
            print("✅ PasswordService initialized successfully")
            
            # Test password validation
            is_strong, errors = password_service.validate_password_strength("TestPassword123!")
            print(f"✅ Password validation: {is_strong}")
            if not is_strong:
                print(f"   Errors: {errors}")
            
            # Test password hashing
            hashed = password_service.hash_password("TestPassword123!")
            print(f"✅ Password hashing works: {len(hashed)} chars")
            
            # Test UserRegistrationRequest
            registration_data = UserRegistrationRequest(
                email="test@example.com",
                password="TestPassword123!",
                preferred_ai_provider="gemini",
                preferred_language="python"
            )
            print("✅ UserRegistrationRequest created successfully")
            print(f"   Email: {registration_data.email}")
            print(f"   AI Provider: {registration_data.preferred_ai_provider}")
            print(f"   Language: {registration_data.preferred_language}")
            
            print("\n✅ All components working locally!")
            return True
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    if __name__ == "__main__":
        test_auth_service()
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")