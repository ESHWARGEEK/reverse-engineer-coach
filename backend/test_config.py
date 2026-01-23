#!/usr/bin/env python3
"""Test configuration loading"""

import os
from app.config import settings

print("Current working directory:", os.getcwd())
print("Environment file exists:", os.path.exists(".env"))
print("Environment file exists (parent):", os.path.exists("../.env"))

print("\nConfiguration values:")
print(f"DATABASE_URL: {settings.database_url}")
print(f"REDIS_URL: {settings.redis_url}")
print(f"API_HOST: {settings.api_host}")
print(f"API_PORT: {settings.api_port}")
print(f"ENVIRONMENT: {settings.environment}")
print(f"DEBUG: {settings.debug}")

print("\nEnvironment variables:")
print(f"DATABASE_URL env: {os.getenv('DATABASE_URL', 'NOT SET')}")
print(f"REDIS_URL env: {os.getenv('REDIS_URL', 'NOT SET')}")