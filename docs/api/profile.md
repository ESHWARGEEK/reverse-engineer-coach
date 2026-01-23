# User Profile API

The User Profile API handles user profile management, API credential updates, and user preferences for the Reverse Engineer Coach platform.

## Base URL
```
/profile
```

## Endpoints

### Get User Profile

Get current user's profile information with masked API credentials.

**Endpoint:** `GET /profile/`

**Authentication:** Required (Bearer token)

**Success Response (200):**
```json
{
  "id": "user_123456789",
  "email": "user@example.com",
  "is_active": true,
  "last_login": "2024-01-01T12:00:00Z",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "preferred_ai_provider": "openai",
  "preferred_language": "python",
  "preferred_frameworks": ["fastapi", "react", "postgresql"],
  "learning_preferences": {
    "difficulty_level": "intermediate",
    "focus_areas": ["architecture", "patterns"],
    "learning_style": "hands-on"
  },
  "has_github_token": true,
  "has_ai_api_key": true,
  "github_token_masked": "ghp_****...****1234",
  "ai_api_key_masked": "sk-****...****abcd"
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/profile/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Update User Profile

Update user profile information and preferences.

**Endpoint:** `PUT /profile/`

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "email": "newemail@example.com",
  "preferred_ai_provider": "openai",
  "preferred_language": "typescript",
  "preferred_frameworks": ["nestjs", "react", "prisma"],
  "learning_preferences": {
    "difficulty_level": "advanced",
    "focus_areas": ["microservices", "clean-architecture"],
    "learning_style": "theory-first"
  }
}
```

**Request Schema:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | No | New email address |
| `preferred_ai_provider` | string | No | AI provider ("openai" or "gemini") |
| `preferred_language` | string | No | Preferred programming language |
| `preferred_frameworks` | array | No | List of preferred frameworks |
| `learning_preferences` | object | No | Learning preferences and settings |

**Success Response (200):**
```json
{
  "id": "user_123456789",
  "email": "newemail@example.com",
  "is_active": true,
  "preferred_ai_provider": "openai",
  "preferred_language": "typescript",
  "preferred_frameworks": ["nestjs", "react", "prisma"],
  "learning_preferences": {
    "difficulty_level": "advanced",
    "focus_areas": ["microservices", "clean-architecture"],
    "learning_style": "theory-first"
  },
  "has_github_token": true,
  "has_ai_api_key": true,
  "github_token_masked": "ghp_****...****1234",
  "ai_api_key_masked": "sk-****...****abcd"
}
```

**Error Responses:**
```json
// 400 - Email Already Exists
{
  "detail": "Email address is already in use",
  "error_code": "EMAIL_EXISTS"
}
```

**Example Request:**
```bash
curl -X PUT "http://localhost:8000/profile/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "preferred_language": "typescript",
    "preferred_frameworks": ["nestjs", "react", "prisma"]
  }'
```

---

### Update Password

Update user password with current password verification.

**Endpoint:** `PUT /profile/password`

**Authentication:** Required (Bearer token)

**Rate Limit:** 5 requests per 5 minutes

**Request Body:**
```json
{
  "current_password": "CurrentPassword123!",
  "new_password": "NewSecurePassword456!",
  "confirm_new_password": "NewSecurePassword456!"
}
```

**Request Schema:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `current_password` | string | Yes | Current password for verification |
| `new_password` | string | Yes | New password (must meet strength requirements) |
| `confirm_new_password` | string | Yes | Confirmation of new password |

**Success Response (200):**
```json
{
  "message": "Password updated successfully"
}
```

**Error Responses:**
```json
// 400 - Current Password Incorrect
{
  "detail": "Current password is incorrect",
  "error_code": "INVALID_CURRENT_PASSWORD"
}

// 400 - Password Validation Failed
{
  "detail": "New password validation failed: Password must contain at least one uppercase letter",
  "error_code": "WEAK_PASSWORD"
}

// 400 - Passwords Don't Match
{
  "detail": "New passwords do not match",
  "error_code": "PASSWORD_MISMATCH"
}
```

**Example Request:**
```bash
curl -X PUT "http://localhost:8000/profile/password" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "CurrentPassword123!",
    "new_password": "NewSecurePassword456!",
    "confirm_new_password": "NewSecurePassword456!"
  }'
```

---

### Update API Credentials

Update user API credentials with validation.

**Endpoint:** `PUT /profile/credentials`

**Authentication:** Required (Bearer token)

**Rate Limit:** 10 requests per 5 minutes

**Request Body:**
```json
{
  "github_token": "ghp_new_github_token_here",
  "ai_api_key": "sk-new_openai_key_here",
  "ai_provider": "openai"
}
```

**Request Schema:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `github_token` | string | No | New GitHub Personal Access Token |
| `ai_api_key` | string | No | New AI service API key |
| `ai_provider` | string | No | AI provider ("openai" or "gemini") |

**Success Response (200):**
```json
{
  "github_token_valid": true,
  "ai_api_key_valid": true,
  "validation_errors": {}
}
```

**Error Responses:**
```json
// 400 - Credential Validation Failed
{
  "github_token_valid": false,
  "ai_api_key_valid": true,
  "validation_errors": {
    "github_token": "Token validation failed: Invalid token or insufficient permissions"
  }
}
```

**Example Request:**
```bash
curl -X PUT "http://localhost:8000/profile/credentials" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "github_token": "ghp_1234567890abcdef1234567890abcdef12345678",
    "ai_provider": "openai"
  }'
```

---

### Validate Current Credentials

Test current user's stored API credentials against their respective APIs.

**Endpoint:** `GET /profile/credentials/validate`

**Authentication:** Required (Bearer token)

**Success Response (200):**
```json
{
  "github_token_valid": true,
  "ai_api_key_valid": false,
  "validation_errors": {
    "ai_api_key": "API key has expired or been revoked"
  }
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/profile/credentials/validate" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Delete API Credentials

Delete all stored API credentials for security purposes.

**Endpoint:** `DELETE /profile/credentials`

**Authentication:** Required (Bearer token)

**Success Response (200):**
```json
{
  "message": "All API credentials have been deleted"
}
```

**Example Request:**
```bash
curl -X DELETE "http://localhost:8000/profile/credentials" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Security Features

### Credential Protection
- **Encryption**: All API credentials encrypted with AES-256
- **Masking**: Credentials never displayed in full
- **Validation**: Real API calls to verify credential validity
- **Isolation**: User-specific encryption keys

### Password Security
- **Current Password Required**: Must provide current password to change
- **Strength Validation**: Enforces strong password requirements
- **Rate Limiting**: Prevents brute force password changes

### Data Privacy
- **User Isolation**: Profile data scoped to authenticated user
- **Audit Logging**: Profile changes logged for security
- **Secure Transmission**: All data encrypted in transit

## Error Codes

| Code | Description |
|------|-------------|
| `EMAIL_EXISTS` | Email address already in use |
| `INVALID_CURRENT_PASSWORD` | Current password verification failed |
| `WEAK_PASSWORD` | New password doesn't meet requirements |
| `PASSWORD_MISMATCH` | Password confirmation doesn't match |
| `INVALID_GITHUB_TOKEN` | GitHub token validation failed |
| `INVALID_AI_API_KEY` | AI API key validation failed |
| `CREDENTIAL_ENCRYPTION_ERROR` | Failed to encrypt credentials |

## Integration Examples

### Python Example
```python
import requests

class ProfileClient:
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def get_profile(self):
        """Get user profile"""
        response = requests.get(f"{self.base_url}/profile/", headers=self.headers)
        return response.json()
    
    def update_profile(self, **updates):
        """Update profile fields"""
        response = requests.put(
            f"{self.base_url}/profile/",
            json=updates,
            headers=self.headers
        )
        return response.json()
    
    def update_password(self, current_password: str, new_password: str):
        """Update user password"""
        payload = {
            "current_password": current_password,
            "new_password": new_password,
            "confirm_new_password": new_password
        }
        response = requests.put(
            f"{self.base_url}/profile/password",
            json=payload,
            headers=self.headers
        )
        return response.json()
    
    def update_credentials(self, github_token: str = None, ai_api_key: str = None):
        """Update API credentials"""
        payload = {}
        if github_token:
            payload["github_token"] = github_token
        if ai_api_key:
            payload["ai_api_key"] = ai_api_key
        
        response = requests.put(
            f"{self.base_url}/profile/credentials",
            json=payload,
            headers=self.headers
        )
        return response.json()
    
    def validate_credentials(self):
        """Validate stored credentials"""
        response = requests.get(
            f"{self.base_url}/profile/credentials/validate",
            headers=self.headers
        )
        return response.json()

# Usage
client = ProfileClient("http://localhost:8000", "your-jwt-token")

# Get profile
profile = client.get_profile()
print(f"User: {profile['email']}")

# Update preferences
client.update_profile(
    preferred_language="typescript",
    preferred_frameworks=["nestjs", "react"]
)

# Validate credentials
validation = client.validate_credentials()
if not validation["github_token_valid"]:
    print("GitHub token needs updating")
```

### JavaScript Example
```javascript
class ProfileClient {
    constructor(baseUrl, authToken) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json'
        };
    }
    
    async getProfile() {
        const response = await fetch(`${this.baseUrl}/profile/`, {
            headers: this.headers
        });
        return response.json();
    }
    
    async updateProfile(updates) {
        const response = await fetch(`${this.baseUrl}/profile/`, {
            method: 'PUT',
            headers: this.headers,
            body: JSON.stringify(updates)
        });
        return response.json();
    }
    
    async updatePassword(currentPassword, newPassword) {
        const payload = {
            current_password: currentPassword,
            new_password: newPassword,
            confirm_new_password: newPassword
        };
        
        const response = await fetch(`${this.baseUrl}/profile/password`, {
            method: 'PUT',
            headers: this.headers,
            body: JSON.stringify(payload)
        });
        return response.json();
    }
    
    async updateCredentials(credentials) {
        const response = await fetch(`${this.baseUrl}/profile/credentials`, {
            method: 'PUT',
            headers: this.headers,
            body: JSON.stringify(credentials)
        });
        return response.json();
    }
    
    async validateCredentials() {
        const response = await fetch(`${this.baseUrl}/profile/credentials/validate`, {
            headers: this.headers
        });
        return response.json();
    }
}

// Usage
const client = new ProfileClient('http://localhost:8000', 'your-jwt-token');

// Get and display profile
const profile = await client.getProfile();
console.log(`User: ${profile.email}`);

// Update preferences
await client.updateProfile({
    preferred_language: 'typescript',
    preferred_frameworks: ['nestjs', 'react', 'prisma']
});

// Check credential validity
const validation = await client.validateCredentials();
if (!validation.github_token_valid) {
    console.log('GitHub token needs updating');
}
```