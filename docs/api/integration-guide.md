# API Integration Guide

This guide provides comprehensive information for developers integrating with the Reverse Engineer Coach API, including authentication setup, best practices, and complete workflow examples.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication Setup](#authentication-setup)
3. [API Client Libraries](#api-client-libraries)
4. [Complete Workflow Examples](#complete-workflow-examples)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)
7. [Best Practices](#best-practices)
8. [Webhooks (Future)](#webhooks-future)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites
- Valid GitHub Personal Access Token with `public_repo` and `read:user` scopes
- OpenAI or compatible AI service API key
- Basic understanding of REST APIs and JWT authentication

### Base URLs
```
Production: https://api.reverseengineercoach.com
Staging: https://staging-api.reverseengineercoach.com
Development: http://localhost:8000
```

### Quick Start Checklist
1. ✅ Obtain GitHub and AI API credentials
2. ✅ Register user account via API
3. ✅ Store JWT tokens securely
4. ✅ Test basic API calls
5. ✅ Implement token refresh logic
6. ✅ Set up error handling

## Authentication Setup

### 1. User Registration

First, register a new user account with your API credentials:

```bash
curl -X POST "https://api.reverseengineercoach.com/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "developer@example.com",
    "password": "SecurePassword123!",
    "github_token": "ghp_your_github_token_here",
    "ai_api_key": "sk-your_openai_key_here",
    "ai_provider": "openai"
  }'
```

**Response:**
```json
{
  "user": {
    "id": "user_123456789",
    "email": "developer@example.com",
    "is_active": true,
    "created_at": "2024-01-01T12:00:00Z"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### 2. User Login

For existing users, authenticate with email and password:

```bash
curl -X POST "https://api.reverseengineercoach.com/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "developer@example.com",
    "password": "SecurePassword123!"
  }'
```

### 3. Token Management

#### Using Access Tokens
Include the access token in all API requests:

```bash
curl -X GET "https://api.reverseengineercoach.com/profile/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### Token Refresh
When access tokens expire (24 hours), use the refresh token:

```bash
curl -X POST "https://api.reverseengineercoach.com/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

## API Client Libraries

### Python Client

```python
import requests
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

class ReverseEngineerCoachClient:
    def __init__(self, base_url: str = "https://api.reverseengineercoach.com"):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
    
    def register(self, email: str, password: str, github_token: str, ai_api_key: str) -> Dict[str, Any]:
        """Register a new user account"""
        response = requests.post(f"{self.base_url}/auth/register", json={
            "email": email,
            "password": password,
            "github_token": github_token,
            "ai_api_key": ai_api_key,
            "ai_provider": "openai"
        })
        
        if response.status_code == 201:
            data = response.json()
            self._store_tokens(data)
            return data["user"]
        else:
            raise Exception(f"Registration failed: {response.json()}")
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login with email and password"""
        response = requests.post(f"{self.base_url}/auth/login", json={
            "email": email,
            "password": password
        })
        
        if response.status_code == 200:
            data = response.json()
            self._store_tokens(data)
            return data["user"]
        else:
            raise Exception(f"Login failed: {response.json()}")
    
    def _store_tokens(self, auth_data: Dict[str, Any]):
        """Store authentication tokens"""
        self.access_token = auth_data["access_token"]
        self.refresh_token = auth_data["refresh_token"]
        expires_in = auth_data.get("expires_in", 86400)
        self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication"""
        if not self.access_token:
            raise Exception("Not authenticated. Please login first.")
        
        # Check if token needs refresh
        if self.token_expires_at and datetime.utcnow() >= self.token_expires_at - timedelta(minutes=5):
            self._refresh_access_token()
        
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def _refresh_access_token(self):
        """Refresh access token"""
        if not self.refresh_token:
            raise Exception("No refresh token available")
        
        response = requests.post(f"{self.base_url}/auth/refresh", json={
            "refresh_token": self.refresh_token
        })
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            expires_in = data.get("expires_in", 86400)
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        else:
            raise Exception("Token refresh failed")
    
    # Discovery methods
    def discover_repositories(self, concept: str, **filters) -> List[Dict[str, Any]]:
        """Discover repositories for a learning concept"""
        payload = {"concept": concept, **filters}
        response = requests.post(
            f"{self.base_url}/discover/repositories",
            json=payload,
            headers=self._get_headers()
        )
        
        if response.status_code == 200:
            return response.json()["repositories"]
        else:
            raise Exception(f"Discovery failed: {response.json()}")
    
    # Project methods
    def create_project(self, title: str, repository_url: str, architecture_topic: str, **options) -> Dict[str, Any]:
        """Create a new learning project"""
        payload = {
            "title": title,
            "target_repository": repository_url,
            "architecture_topic": architecture_topic,
            **options
        }
        
        response = requests.post(
            f"{self.base_url}/projects/",
            json=payload,
            headers=self._get_headers()
        )
        
        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Project creation failed: {response.json()}")
    
    def create_project_from_discovery(self, title: str, repository_suggestion: Dict[str, Any], 
                                    learning_concept: str, **options) -> Dict[str, Any]:
        """Create project from discovery suggestion"""
        payload = {
            "title": title,
            "repository_suggestion": repository_suggestion,
            "learning_concept": learning_concept,
            **options
        }
        
        response = requests.post(
            f"{self.base_url}/projects/from-discovery",
            json=payload,
            headers=self._get_headers()
        )
        
        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Project creation failed: {response.json()}")
    
    def get_dashboard(self, **filters) -> Dict[str, Any]:
        """Get user dashboard with projects and statistics"""
        response = requests.get(
            f"{self.base_url}/dashboard/",
            params=filters,
            headers=self._get_headers()
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Dashboard request failed: {response.json()}")

# Usage example
client = ReverseEngineerCoachClient()

# Register or login
user = client.login("developer@example.com", "password")
print(f"Logged in as: {user['email']}")

# Discover repositories
repos = client.discover_repositories(
    concept="microservices architecture",
    language="python",
    max_results=5
)

# Create project from discovery
if repos:
    project = client.create_project_from_discovery(
        title="Learning Microservices",
        repository_suggestion=repos[0],
        learning_concept="microservices architecture",
        implementation_language="python"
    )
    print(f"Created project: {project['id']}")

# Get dashboard
dashboard = client.get_dashboard()
print(f"Total projects: {dashboard['stats']['total_projects']}")
```

### JavaScript/TypeScript Client

```typescript
interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresAt: Date;
}

interface User {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

interface RepositorySuggestion {
  repository_url: string;
  repository_name: string;
  description: string;
  stars: number;
  language: string;
  quality_score: number;
  educational_value: number;
  overall_score: number;
}

class ReverseEngineerCoachClient {
  private baseUrl: string;
  private tokens: AuthTokens | null = null;

  constructor(baseUrl: string = 'https://api.reverseengineercoach.com') {
    this.baseUrl = baseUrl;
  }

  async register(
    email: string,
    password: string,
    githubToken: string,
    aiApiKey: string
  ): Promise<User> {
    const response = await fetch(`${this.baseUrl}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email,
        password,
        github_token: githubToken,
        ai_api_key: aiApiKey,
        ai_provider: 'openai'
      })
    });

    if (response.ok) {
      const data = await response.json();
      this.storeTokens(data);
      return data.user;
    } else {
      const error = await response.json();
      throw new Error(`Registration failed: ${error.detail}`);
    }
  }

  async login(email: string, password: string): Promise<User> {
    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    if (response.ok) {
      const data = await response.json();
      this.storeTokens(data);
      return data.user;
    } else {
      const error = await response.json();
      throw new Error(`Login failed: ${error.detail}`);
    }
  }

  private storeTokens(authData: any): void {
    const expiresIn = authData.expires_in || 86400;
    this.tokens = {
      accessToken: authData.access_token,
      refreshToken: authData.refresh_token,
      expiresAt: new Date(Date.now() + expiresIn * 1000)
    };

    // Store in localStorage for persistence
    localStorage.setItem('auth_tokens', JSON.stringify({
      accessToken: this.tokens.accessToken,
      refreshToken: this.tokens.refreshToken,
      expiresAt: this.tokens.expiresAt.toISOString()
    }));
  }

  private async getAuthHeaders(): Promise<Record<string, string>> {
    if (!this.tokens) {
      // Try to restore from localStorage
      const stored = localStorage.getItem('auth_tokens');
      if (stored) {
        const parsed = JSON.parse(stored);
        this.tokens = {
          accessToken: parsed.accessToken,
          refreshToken: parsed.refreshToken,
          expiresAt: new Date(parsed.expiresAt)
        };
      } else {
        throw new Error('Not authenticated. Please login first.');
      }
    }

    // Check if token needs refresh (5 minutes before expiry)
    if (Date.now() >= this.tokens.expiresAt.getTime() - 5 * 60 * 1000) {
      await this.refreshAccessToken();
    }

    return {
      'Authorization': `Bearer ${this.tokens.accessToken}`,
      'Content-Type': 'application/json'
    };
  }

  private async refreshAccessToken(): Promise<void> {
    if (!this.tokens?.refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await fetch(`${this.baseUrl}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: this.tokens.refreshToken })
    });

    if (response.ok) {
      const data = await response.json();
      const expiresIn = data.expires_in || 86400;
      this.tokens.accessToken = data.access_token;
      this.tokens.expiresAt = new Date(Date.now() + expiresIn * 1000);

      // Update localStorage
      localStorage.setItem('auth_tokens', JSON.stringify({
        accessToken: this.tokens.accessToken,
        refreshToken: this.tokens.refreshToken,
        expiresAt: this.tokens.expiresAt.toISOString()
      }));
    } else {
      throw new Error('Token refresh failed');
    }
  }

  async discoverRepositories(
    concept: string,
    filters: Record<string, any> = {}
  ): Promise<RepositorySuggestion[]> {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseUrl}/discover/repositories`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ concept, ...filters })
    });

    if (response.ok) {
      const data = await response.json();
      return data.repositories;
    } else {
      const error = await response.json();
      throw new Error(`Discovery failed: ${error.detail}`);
    }
  }

  async createProject(
    title: string,
    repositoryUrl: string,
    architectureTopic: string,
    options: Record<string, any> = {}
  ): Promise<any> {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseUrl}/projects/`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        title,
        target_repository: repositoryUrl,
        architecture_topic: architectureTopic,
        ...options
      })
    });

    if (response.ok) {
      return response.json();
    } else {
      const error = await response.json();
      throw new Error(`Project creation failed: ${error.detail}`);
    }
  }

  async createProjectFromDiscovery(
    title: string,
    repositorySuggestion: RepositorySuggestion,
    learningConcept: string,
    options: Record<string, any> = {}
  ): Promise<any> {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${this.baseUrl}/projects/from-discovery`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        title,
        repository_suggestion: repositorySuggestion,
        learning_concept: learningConcept,
        ...options
      })
    });

    if (response.ok) {
      return response.json();
    } else {
      const error = await response.json();
      throw new Error(`Project creation failed: ${error.detail}`);
    }
  }

  async getDashboard(filters: Record<string, any> = {}): Promise<any> {
    const headers = await this.getAuthHeaders();
    const params = new URLSearchParams(filters);
    const response = await fetch(`${this.baseUrl}/dashboard/?${params}`, {
      headers
    });

    if (response.ok) {
      return response.json();
    } else {
      const error = await response.json();
      throw new Error(`Dashboard request failed: ${error.detail}`);
    }
  }

  logout(): void {
    this.tokens = null;
    localStorage.removeItem('auth_tokens');
  }
}

// Usage example
const client = new ReverseEngineerCoachClient();

// Login
const user = await client.login('developer@example.com', 'password');
console.log(`Logged in as: ${user.email}`);

// Discover repositories
const repos = await client.discoverRepositories('microservices architecture', {
  language: 'python',
  max_results: 5
});

// Create project from discovery
if (repos.length > 0) {
  const project = await client.createProjectFromDiscovery(
    'Learning Microservices',
    repos[0],
    'microservices architecture',
    { implementation_language: 'python' }
  );
  console.log(`Created project: ${project.id}`);
}

// Get dashboard
const dashboard = await client.getDashboard();
console.log(`Total projects: ${dashboard.stats.total_projects}`);
```

## Complete Workflow Examples

### 1. Discovery-to-Project Workflow

This example shows the complete flow from concept discovery to project creation:

```python
# Complete workflow example
client = ReverseEngineerCoachClient()

# 1. Authenticate
user = client.login("developer@example.com", "password")
print(f"Authenticated as: {user['email']}")

# 2. Discover repositories for a concept
concept = "clean architecture patterns"
repositories = client.discover_repositories(
    concept=concept,
    language="python",
    min_stars=100,
    max_results=5
)

print(f"Found {len(repositories)} repositories for '{concept}':")
for i, repo in enumerate(repositories):
    print(f"{i+1}. {repo['repository_name']} (Score: {repo['overall_score']:.2f})")
    print(f"   {repo['description']}")
    print(f"   Stars: {repo['stars']}, Language: {repo['language']}")
    print()

# 3. Select best repository (highest score)
if repositories:
    best_repo = max(repositories, key=lambda r: r['overall_score'])
    print(f"Selected repository: {best_repo['repository_name']}")
    
    # 4. Create project from discovery
    project = client.create_project_from_discovery(
        title=f"Learning {concept.title()}",
        repository_suggestion=best_repo,
        learning_concept=concept,
        implementation_language="python",
        preferred_frameworks=["fastapi", "sqlalchemy", "pytest"]
    )
    
    print(f"Created project: {project['id']}")
    print(f"Status: {project['status']}")
    print(f"Repository: {project['target_repository']}")
    
    # 5. Monitor project analysis progress
    import time
    while project['status'] in ['created', 'analyzing']:
        time.sleep(5)  # Wait 5 seconds
        updated_project = client.get_project(project['id'])
        print(f"Analysis status: {updated_project['status']}")
        project = updated_project
    
    if project['status'] == 'ready':
        print(f"Project ready! Total tasks: {project['total_tasks']}")
    elif project['status'] == 'failed':
        print("Project analysis failed")
```

### 2. Project Management Workflow

```python
# Project management workflow
client = ReverseEngineerCoachClient()
client.login("developer@example.com", "password")

# Get dashboard overview
dashboard = client.get_dashboard()
print(f"Dashboard Overview:")
print(f"- Total projects: {dashboard['stats']['total_projects']}")
print(f"- In progress: {dashboard['stats']['in_progress_projects']}")
print(f"- Completed: {dashboard['stats']['completed_projects']}")
print(f"- Average completion: {dashboard['stats']['average_completion_percentage']:.1f}%")

# List active projects
active_projects = client.get_dashboard(status="in_progress")
print(f"\nActive Projects ({len(active_projects['projects'])}):")

for project in active_projects['projects']:
    print(f"- {project['title']}")
    print(f"  Progress: {project['completion_percentage']:.1f}%")
    print(f"  Tasks: {project['completed_tasks']}/{project['total_tasks']}")
    print(f"  Last updated: {project['updated_at']}")
    
    # Update progress for demonstration
    if project['completion_percentage'] < 100:
        new_completed = min(project['completed_tasks'] + 1, project['total_tasks'])
        progress = client.update_project_progress(
            project['id'],
            completed_tasks=new_completed
        )
        print(f"  Updated progress: {progress['completion_percentage']:.1f}%")
    print()
```

### 3. File Management Workflow

```python
# File management workflow
client = ReverseEngineerCoachClient()
client.login("developer@example.com", "password")

project_id = "proj_123456789"  # Your project ID

# Create project structure
files_to_create = [
    {
        "file_path": "src/models/user.py",
        "content": '''from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    id: str
    email: str
    name: Optional[str] = None
    is_active: bool = True
''',
        "language": "python"
    },
    {
        "file_path": "src/services/user_service.py",
        "content": '''from src.models.user import User
from src.repositories.user_repository import UserRepository

class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository
    
    def create_user(self, email: str, name: str = None) -> User:
        user = User(
            id=self.generate_id(),
            email=email,
            name=name
        )
        return self.repository.save(user)
    
    def generate_id(self) -> str:
        import uuid
        return str(uuid.uuid4())
''',
        "language": "python"
    },
    {
        "file_path": "tests/test_user_service.py",
        "content": '''import pytest
from src.services.user_service import UserService
from src.models.user import User

def test_create_user():
    # Mock repository
    class MockRepository:
        def save(self, user):
            return user
    
    service = UserService(MockRepository())
    user = service.create_user("test@example.com", "Test User")
    
    assert user.email == "test@example.com"
    assert user.name == "Test User"
    assert user.is_active is True
''',
        "language": "python"
    }
]

# Create all files
created_files = client.create_multiple_files(project_id, files_to_create)
print(f"Created {len(created_files)} files")

# Get project structure
structure = client.get_project_structure(project_id)
print(f"\nProject Structure ({structure['total_files']} files):")

def print_structure(nodes, indent=0):
    for node in nodes:
        prefix = "  " * indent
        if node['type'] == 'directory':
            print(f"{prefix}📁 {node['name']}/")
            if node['children']:
                print_structure(node['children'], indent + 1)
        else:
            size_kb = node['size'] / 1024 if node['size'] else 0
            print(f"{prefix}📄 {node['name']} ({size_kb:.1f} KB)")

print_structure(structure['structure'])

# Search for files
search_results = client.search_files(project_id, "UserService")
print(f"\nFiles containing 'UserService': {search_results['total_count']}")
for file in search_results['files']:
    print(f"- {file['file_path']}")
```

## Error Handling

### Comprehensive Error Handling

```python
import requests
from typing import Dict, Any

class APIError(Exception):
    def __init__(self, message: str, status_code: int, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)

class ReverseEngineerCoachClient:
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response with proper error handling"""
        try:
            data = response.json()
        except ValueError:
            data = {"detail": "Invalid JSON response"}
        
        if response.status_code >= 400:
            error_code = data.get("error_code", "UNKNOWN_ERROR")
            message = data.get("detail", f"HTTP {response.status_code} error")
            
            # Handle specific error types
            if response.status_code == 401:
                if error_code == "TOKEN_EXPIRED":
                    # Try to refresh token automatically
                    try:
                        self._refresh_access_token()
                        # Retry the original request would go here
                        return {"retry": True}
                    except Exception:
                        raise APIError("Authentication failed", 401, error_code)
                else:
                    raise APIError("Authentication required", 401, error_code)
            
            elif response.status_code == 403:
                raise APIError("Access denied", 403, error_code)
            
            elif response.status_code == 404:
                raise APIError("Resource not found", 404, error_code)
            
            elif response.status_code == 429:
                # Rate limiting
                retry_after = response.headers.get("Retry-After", "60")
                raise APIError(f"Rate limited. Retry after {retry_after} seconds", 429, error_code)
            
            elif response.status_code >= 500:
                raise APIError("Server error", response.status_code, error_code)
            
            else:
                raise APIError(message, response.status_code, error_code)
        
        return data

# Usage with error handling
try:
    client = ReverseEngineerCoachClient()
    user = client.login("developer@example.com", "password")
    
    repositories = client.discover_repositories("microservices")
    project = client.create_project_from_discovery(
        "Learning Project",
        repositories[0],
        "microservices"
    )
    
except APIError as e:
    if e.status_code == 401:
        print("Authentication failed. Please check your credentials.")
    elif e.status_code == 429:
        print(f"Rate limited: {e.message}")
    elif e.error_code == "INVALID_GITHUB_TOKEN":
        print("GitHub token is invalid. Please update your credentials.")
    else:
        print(f"API Error: {e.message} (Code: {e.error_code})")

except Exception as e:
    print(f"Unexpected error: {e}")
```

## Rate Limiting

### Rate Limit Handling

The API implements rate limiting to ensure fair usage:

| Endpoint Category | Limit | Window |
|------------------|-------|---------|
| Authentication | 5 requests | 5 minutes |
| Discovery | 20 requests | 1 minute |
| Profile Updates | 10 requests | 5 minutes |
| General API | 100 requests | 1 minute |

```python
import time
from typing import Callable, Any

def with_rate_limit_retry(max_retries: int = 3, backoff_factor: float = 2.0):
    """Decorator for automatic rate limit retry with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except APIError as e:
                    if e.status_code == 429 and attempt < max_retries:
                        # Extract retry-after header or use exponential backoff
                        retry_after = getattr(e, 'retry_after', backoff_factor ** attempt)
                        print(f"Rate limited. Retrying in {retry_after} seconds...")
                        time.sleep(retry_after)
                        continue
                    raise
            return None
        return wrapper
    return decorator

# Apply to client methods
class RateLimitedClient(ReverseEngineerCoachClient):
    @with_rate_limit_retry(max_retries=3)
    def discover_repositories(self, *args, **kwargs):
        return super().discover_repositories(*args, **kwargs)
    
    @with_rate_limit_retry(max_retries=3)
    def create_project(self, *args, **kwargs):
        return super().create_project(*args, **kwargs)
```

## Best Practices

### 1. Security Best Practices

```python
# Secure credential storage
import keyring
import os

class SecureCredentialManager:
    @staticmethod
    def store_credentials(service: str, username: str, password: str):
        """Store credentials securely using keyring"""
        keyring.set_password(service, username, password)
    
    @staticmethod
    def get_credentials(service: str, username: str) -> str:
        """Retrieve credentials securely"""
        return keyring.get_password(service, username)
    
    @staticmethod
    def store_tokens(access_token: str, refresh_token: str):
        """Store JWT tokens securely"""
        # Use environment variables or secure storage
        os.environ['ACCESS_TOKEN'] = access_token
        os.environ['REFRESH_TOKEN'] = refresh_token

# Usage
cred_manager = SecureCredentialManager()
cred_manager.store_credentials("reverse-engineer-coach", "github_token", "ghp_...")
cred_manager.store_credentials("reverse-engineer-coach", "openai_key", "sk-...")

# Retrieve for registration
github_token = cred_manager.get_credentials("reverse-engineer-coach", "github_token")
openai_key = cred_manager.get_credentials("reverse-engineer-coach", "openai_key")
```

### 2. Caching and Performance

```python
import functools
import time
from typing import Dict, Any

class CachedClient(ReverseEngineerCoachClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 300  # 5 minutes
    
    def _get_cache_key(self, method: str, *args, **kwargs) -> str:
        """Generate cache key from method and parameters"""
        import hashlib
        key_data = f"{method}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid"""
        return time.time() - cache_entry['timestamp'] < self._cache_ttl
    
    @functools.lru_cache(maxsize=100)
    def discover_repositories(self, concept: str, **filters):
        """Cached repository discovery"""
        cache_key = self._get_cache_key('discover_repositories', concept, **filters)
        
        if cache_key in self._cache and self._is_cache_valid(self._cache[cache_key]):
            return self._cache[cache_key]['data']
        
        result = super().discover_repositories(concept, **filters)
        
        self._cache[cache_key] = {
            'data': result,
            'timestamp': time.time()
        }
        
        return result
```

### 3. Async/Await Support

```python
import asyncio
import aiohttp
from typing import Dict, Any, List

class AsyncReverseEngineerCoachClient:
    def __init__(self, base_url: str = "https://api.reverseengineercoach.com"):
        self.base_url = base_url
        self.access_token: str = None
        self.session: aiohttp.ClientSession = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """Async login"""
        async with self.session.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password}
        ) as response:
            if response.status == 200:
                data = await response.json()
                self.access_token = data["access_token"]
                return data["user"]
            else:
                error = await response.json()
                raise Exception(f"Login failed: {error['detail']}")
    
    async def discover_repositories(self, concept: str, **filters) -> List[Dict[str, Any]]:
        """Async repository discovery"""
        headers = {"Authorization": f"Bearer {self.access_token}"}
        payload = {"concept": concept, **filters}
        
        async with self.session.post(
            f"{self.base_url}/discover/repositories",
            json=payload,
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data["repositories"]
            else:
                error = await response.json()
                raise Exception(f"Discovery failed: {error['detail']}")
    
    async def create_multiple_projects(self, project_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create multiple projects concurrently"""
        tasks = []
        for config in project_configs:
            task = self.create_project(**config)
            tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=True)

# Usage
async def main():
    async with AsyncReverseEngineerCoachClient() as client:
        await client.login("developer@example.com", "password")
        
        # Discover repositories for multiple concepts concurrently
        concepts = ["microservices", "clean architecture", "design patterns"]
        discovery_tasks = [
            client.discover_repositories(concept, max_results=3)
            for concept in concepts
        ]
        
        results = await asyncio.gather(*discovery_tasks)
        
        for concept, repos in zip(concepts, results):
            print(f"{concept}: {len(repos)} repositories found")

# Run async example
asyncio.run(main())
```

## Webhooks (Future)

The platform will support webhooks for real-time notifications:

```python
# Future webhook implementation
from flask import Flask, request, jsonify
import hmac
import hashlib

app = Flask(__name__)
WEBHOOK_SECRET = "your-webhook-secret"

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify webhook signature"""
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected_signature}", signature)

@app.route('/webhooks/reverse-engineer-coach', methods=['POST'])
def handle_webhook():
    """Handle incoming webhooks"""
    signature = request.headers.get('X-Signature-256')
    payload = request.get_data()
    
    if not verify_webhook_signature(payload, signature):
        return jsonify({"error": "Invalid signature"}), 401
    
    event_data = request.json
    event_type = event_data.get('event_type')
    
    if event_type == 'project.analysis.completed':
        project_id = event_data['data']['project_id']
        status = event_data['data']['status']
        print(f"Project {project_id} analysis completed with status: {status}")
    
    elif event_type == 'project.progress.updated':
        project_id = event_data['data']['project_id']
        completion = event_data['data']['completion_percentage']
        print(f"Project {project_id} progress updated: {completion}%")
    
    return jsonify({"status": "received"}), 200

if __name__ == '__main__':
    app.run(port=5000)
```

## Testing

### Unit Testing with Mock API

```python
import unittest
from unittest.mock import Mock, patch
import responses

class TestReverseEngineerCoachClient(unittest.TestCase):
    def setUp(self):
        self.client = ReverseEngineerCoachClient("http://localhost:8000")
    
    @responses.activate
    def test_login_success(self):
        """Test successful login"""
        responses.add(
            responses.POST,
            "http://localhost:8000/auth/login",
            json={
                "user": {"id": "user_123", "email": "test@example.com"},
                "access_token": "token_123",
                "refresh_token": "refresh_123",
                "expires_in": 86400
            },
            status=200
        )
        
        user = self.client.login("test@example.com", "password")
        
        self.assertEqual(user["email"], "test@example.com")
        self.assertEqual(self.client.access_token, "token_123")
    
    @responses.activate
    def test_discover_repositories(self):
        """Test repository discovery"""
        responses.add(
            responses.POST,
            "http://localhost:8000/discover/repositories",
            json={
                "repositories": [
                    {
                        "repository_url": "https://github.com/example/repo",
                        "repository_name": "example-repo",
                        "description": "Example repository",
                        "stars": 100,
                        "language": "python",
                        "overall_score": 0.85
                    }
                ]
            },
            status=200
        )
        
        self.client.access_token = "token_123"  # Mock authentication
        
        repos = self.client.discover_repositories("microservices")
        
        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]["repository_name"], "example-repo")
    
    def test_error_handling(self):
        """Test error handling"""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {
                "detail": "Invalid credentials",
                "error_code": "INVALID_CREDENTIALS"
            }
            mock_post.return_value = mock_response
            
            with self.assertRaises(Exception) as context:
                self.client.login("invalid@example.com", "wrong_password")
            
            self.assertIn("Login failed", str(context.exception))

if __name__ == '__main__':
    unittest.main()
```

### Integration Testing

```python
import pytest
import os
from dotenv import load_dotenv

load_dotenv()

@pytest.fixture
def client():
    """Create test client"""
    return ReverseEngineerCoachClient("http://localhost:8000")

@pytest.fixture
def authenticated_client(client):
    """Create authenticated test client"""
    email = os.getenv("TEST_EMAIL")
    password = os.getenv("TEST_PASSWORD")
    
    if not email or not password:
        pytest.skip("Test credentials not provided")
    
    client.login(email, password)
    return client

def test_full_workflow(authenticated_client):
    """Test complete workflow from discovery to project creation"""
    # Discover repositories
    repos = authenticated_client.discover_repositories(
        concept="test architecture",
        max_results=1
    )
    
    assert len(repos) > 0
    
    # Create project from discovery
    project = authenticated_client.create_project_from_discovery(
        title="Test Project",
        repository_suggestion=repos[0],
        learning_concept="test architecture"
    )
    
    assert project["status"] in ["created", "analyzing"]
    assert project["title"] == "Test Project"
    
    # Clean up - delete test project
    authenticated_client.delete_project(project["id"])

def test_dashboard_functionality(authenticated_client):
    """Test dashboard functionality"""
    dashboard = authenticated_client.get_dashboard()
    
    assert "projects" in dashboard
    assert "stats" in dashboard
    assert isinstance(dashboard["stats"]["total_projects"], int)
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Authentication Issues

**Problem**: `401 Unauthorized` errors
**Solutions**:
- Check if access token is valid and not expired
- Verify JWT token format
- Ensure proper Authorization header format: `Bearer <token>`
- Try refreshing the access token

```python
# Debug authentication
def debug_auth_headers(client):
    headers = client._get_headers()
    print(f"Authorization header: {headers.get('Authorization', 'Missing')}")
    
    if client.token_expires_at:
        import datetime
        now = datetime.datetime.utcnow()
        expires_at = client.token_expires_at
        print(f"Token expires at: {expires_at}")
        print(f"Current time: {now}")
        print(f"Token valid: {now < expires_at}")
```

#### 2. Rate Limiting

**Problem**: `429 Too Many Requests` errors
**Solutions**:
- Implement exponential backoff
- Check rate limit headers
- Reduce request frequency
- Use caching to avoid duplicate requests

```python
def handle_rate_limit(response):
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 60))
        print(f"Rate limited. Waiting {retry_after} seconds...")
        time.sleep(retry_after)
        return True
    return False
```

#### 3. API Credential Issues

**Problem**: GitHub or AI API validation failures
**Solutions**:
- Verify GitHub token has correct scopes (`public_repo`, `read:user`)
- Check AI API key is valid and has sufficient credits
- Test credentials directly with respective APIs

```python
def validate_github_token(token):
    """Test GitHub token validity"""
    import requests
    response = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"token {token}"}
    )
    return response.status_code == 200

def validate_openai_key(api_key):
    """Test OpenAI API key validity"""
    import openai
    openai.api_key = api_key
    try:
        openai.Model.list()
        return True
    except:
        return False
```

#### 4. Network and Connectivity

**Problem**: Connection timeouts or network errors
**Solutions**:
- Check internet connectivity
- Verify API endpoint URLs
- Implement retry logic with exponential backoff
- Use appropriate timeout values

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_robust_session():
    """Create HTTP session with retry logic"""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session
```

### Debug Mode

```python
class DebugClient(ReverseEngineerCoachClient):
    def __init__(self, *args, debug=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.debug = debug
    
    def _make_request(self, method, url, **kwargs):
        """Make HTTP request with debug logging"""
        if self.debug:
            print(f"DEBUG: {method.upper()} {url}")
            if 'json' in kwargs:
                print(f"DEBUG: Request body: {kwargs['json']}")
            if 'headers' in kwargs:
                headers = kwargs['headers'].copy()
                if 'Authorization' in headers:
                    headers['Authorization'] = 'Bearer ***'
                print(f"DEBUG: Headers: {headers}")
        
        response = requests.request(method, url, **kwargs)
        
        if self.debug:
            print(f"DEBUG: Response status: {response.status_code}")
            try:
                print(f"DEBUG: Response body: {response.json()}")
            except:
                print(f"DEBUG: Response body: {response.text}")
        
        return response

# Usage
debug_client = DebugClient(debug=True)
debug_client.login("developer@example.com", "password")
```

This comprehensive integration guide provides everything developers need to successfully integrate with the Reverse Engineer Coach API, from basic authentication to advanced workflows and troubleshooting.