#!/usr/bin/env python3
"""Generate proper encryption keys for development"""

import base64
import os
from cryptography.fernet import Fernet

# Generate proper Fernet keys
encryption_key = Fernet.generate_key()
master_encryption_key = Fernet.generate_key()
credential_encryption_key = Fernet.generate_key()

print("Generated encryption keys for development:")
print(f"ENCRYPTION_KEY={encryption_key.decode()}")
print(f"MASTER_ENCRYPTION_KEY={master_encryption_key.decode()}")
print(f"CREDENTIAL_ENCRYPTION_KEY={credential_encryption_key.decode()}")

# Generate JWT secrets (32+ characters)
jwt_secret = base64.urlsafe_b64encode(os.urandom(32)).decode()
jwt_refresh_secret = base64.urlsafe_b64encode(os.urandom(32)).decode()

print(f"JWT_SECRET_KEY={jwt_secret}")
print(f"JWT_REFRESH_SECRET_KEY={jwt_refresh_secret}")