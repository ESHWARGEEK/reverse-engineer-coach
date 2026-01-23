# Authentication API

The Authentication API handles user registration, login, logout, and JWT token management for the Reverse Engineer Coach platform.

## Base URL
```
/auth
```

## Endpoints

### Register User

Register a new user account with API credentials.

**Endpoint:** `POST /auth/register`

**Rate Limit:** 3 requests per hour per IP

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "github_token": "ghp_your_github_personal_access_token",
  "ai_api_key": "sk-your_openai_api_key",
  "ai_provider": "openai"
}
```

**Request Schema:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | Valid email address |
| `password` | string | Yes | Password (min 8 chars, must include uppercase, lowercase, number, special char) |
| `github_token` | string | Yes | GitHub Personal Access Token with `public_repo` and `read:user` scopes |
| `ai_api_key` | string | Yes | OpenAI or compatible AI service API key |
| `ai_provider` | string | No | AI provider ("openai" or "gemini", default: "openai") |

**Success Response (201):**
```json
{
  "user": {
    "id": "user_123456789",
    "email": "user@example.com",
    "is_active": true,
    "created_at": "2024-01-01T12:00:00Z",
    "preferred_ai_provider": "openai"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**Error Responses:**
```json
// 400 - Validation Error
{
  "detail": "Email already exists",
  "error_code": "EMAIL_EXISTS"
}

// 400 - Invalid API Credentials
{
  "detail": "GitHub token validation failed: Invalid token or insufficient permissions",
  "error_code": "INVALID_GITHUB_TOKEN"
}

// 429 - Rate Limited
{
  "detail": "Too many registration attempts. Please try again later.",
  "error_code": "RATE_LIMIT_EXCEEDED"
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "developer@example.com",
    "password": "MySecurePass123!",
    "github_token": "ghp_1234567890abcdef1234567890abcdef12345678",
    "ai_api_key": "sk-1234567890abcdef1234567890abcdef1234567890abcdef",
    "ai_provider": "openai"
  }'
```

---

### Login User

Authenticate user and receive JWT tokens.

**Endpoint:** `POST /auth/login`

**Rate Limit:** 5 requests per 5 minutes per IP

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Success Response (200):**
```json
{
  "user": {
    "id": "user_123456789",
    "email": "user@example.com",
    "is_active": true,
    "last_login": "2024-01-01T12:00:00Z",
    "preferred_ai_provider": "openai"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**Error Responses:**
```json
// 401 - Invalid Credentials
{
  "detail": "Invalid email or password",
  "error_code": "INVALID_CREDENTIALS"
}

// 429 - Rate Limited
{
  "detail": "Too many login attempts. Please try again later.",
  "error_code": "RATE_LIMIT_EXCEEDED"
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "developer@example.com",
    "password": "MySecurePass123!"
  }'
```

---

### Refresh Token

Get a new access token using a refresh token.

**Endpoint:** `POST /auth/refresh`

**Rate Limit:** 10 requests per minute

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**Error Responses:**
```json
// 401 - Invalid Refresh Token
{
  "detail": "Invalid or expired refresh token",
  "error_code": "INVALID_REFRESH_TOKEN"
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

---

### Logout User

Logout user and invalidate tokens.

**Endpoint:** `POST /auth/logout`

**Authentication:** Required (Bearer token)

**Request Body:** None

**Success Response (200):**
```json
{
  "message": "Successfully logged out"
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/auth/logout" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Get Current User

Get current authenticated user information.

**Endpoint:** `GET /auth/me`

**Authentication:** Required (Bearer token)

**Success Response (200):**
```json
{
  "id": "user_123456789",
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "last_login": "2024-01-01T12:00:00Z",
  "preferred_ai_provider": "openai",
  "preferred_language": "python",
  "preferred_frameworks": ["fastapi", "react"],
  "has_github_token": true,
  "has_ai_api_key": true,
  "github_token_masked": "ghp_****...****1234",
  "ai_api_key_masked": "sk-****...****abcd"
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Update Current User

Update current user information and preferences.

**Endpoint:** `PUT /auth/me`

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "preferred_ai_provider": "openai",
  "preferred_language": "python",
  "preferred_frameworks": ["fastapi", "react", "postgresql"],
  "github_token": "ghp_new_token_if_updating",
  "openai_api_key": "sk-new_key_if_updating"
}
```

**Success Response (200):**
```json
{
  "id": "user_123456789",
  "email": "user@example.com",
  "is_active": true,
  "preferred_ai_provider": "openai",
  "preferred_language": "python",
  "preferred_frameworks": ["fastapi", "react", "postgresql"],
  "has_github_token": true,
  "has_ai_api_key": true,
  "github_token_masked": "ghp_****...****5678",
  "ai_api_key_masked": "sk-****...****efgh"
}
```

**Example Request:**
```bash
curl -X PUT "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "preferred_language": "typescript",
    "preferred_frameworks": ["nestjs", "react", "prisma"]
  }'
```

---

### Test API Keys

Test if stored API keys are valid.

**Endpoint:** `GET /auth/api-keys/test`

**Authentication:** Required (Bearer token)

**Success Response (200):**
```json
{
  "github_token": true,
  "openai_api_key": true,
  "gemini_api_key": false,
  "preferred_provider": "openai"
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/auth/api-keys/test" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Authentication Flow

### 1. Registration Flow
```mermaid
sequenceDiagram
    participant Client
    participant API
    participant GitHub
    participant AI_Service
    
    Client->>API: POST /auth/register
    API->>GitHub: Validate GitHub token
    GitHub-->>API: Token validation result
    API->>AI_Service: Validate AI API key
    AI_Service-->>API: Key validation result
    API->>API: Create user & encrypt credentials
    API-->>Client: JWT tokens + user info
```

### 2. Login Flow
```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Database
    
    Client->>API: POST /auth/login
    API->>Database: Verify credentials
    Database-->>API: User data
    API->>API: Generate JWT tokens
    API-->>Client: JWT tokens + user info
```

### 3. Token Refresh Flow
```mermaid
sequenceDiagram
    participant Client
    participant API
    
    Client->>API: POST /auth/refresh
    API->>API: Validate refresh token
    API->>API: Generate new access token
    API-->>Client: New access token
```

## Security Features

### Password Requirements
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter  
- At least one number
- At least one special character (!@#$%^&*)

### Token Security
- **Access tokens**: 24-hour expiration (configurable)
- **Refresh tokens**: 30-day expiration (configurable)
- **JWT signing**: HS256 algorithm with secure secret
- **Token revocation**: Logout invalidates all user tokens

### Rate Limiting
- **Registration**: 3 attempts per hour per IP
- **Login**: 5 attempts per 5 minutes per IP
- **Token refresh**: 10 attempts per minute
- **Profile updates**: 10 attempts per 5 minutes

### API Credential Security
- **Encryption**: AES-256 encryption for stored credentials
- **Validation**: Real API calls to validate credentials during registration
- **Masking**: Credentials are masked in all API responses
- **Isolation**: User-specific encryption keys prevent cross-user access

## Error Codes

| Code | Description |
|------|-------------|
| `EMAIL_EXISTS` | Email address already registered |
| `INVALID_CREDENTIALS` | Invalid email or password |
| `INVALID_GITHUB_TOKEN` | GitHub token validation failed |
| `INVALID_AI_API_KEY` | AI API key validation failed |
| `WEAK_PASSWORD` | Password doesn't meet security requirements |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `INVALID_REFRESH_TOKEN` | Refresh token is invalid or expired |
| `TOKEN_EXPIRED` | Access token has expired |
| `INSUFFICIENT_PERMISSIONS` | GitHub token lacks required scopes |

## Best Practices

### For Clients
1. **Store tokens securely** - Use secure storage (keychain, encrypted storage)
2. **Handle token expiration** - Implement automatic token refresh
3. **Validate credentials** - Test API keys before storing
4. **Use HTTPS** - Always use secure connections
5. **Handle rate limits** - Implement exponential backoff

### For Security
1. **Rotate tokens regularly** - Refresh tokens before expiration
2. **Monitor API usage** - Track unusual authentication patterns
3. **Use strong passwords** - Follow password requirements
4. **Keep credentials private** - Never share API keys or tokens
5. **Logout when done** - Always logout to invalidate tokens

## Integration Examples

### Python Example
```python
import requests
import json

class AuthClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.access_token = None
        self.refresh_token = None
    
    def register(self, email, password, github_token, ai_api_key):
        response = requests.post(f"{self.base_url}/auth/register", json={
            "email": email,
            "password": password,
            "github_token": github_token,
            "ai_api_key": ai_api_key
        })
        
        if response.status_code == 201:
            data = response.json()
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]
            return data["user"]
        else:
            raise Exception(f"Registration failed: {response.json()}")
    
    def login(self, email, password):
        response = requests.post(f"{self.base_url}/auth/login", json={
            "email": email,
            "password": password
        })
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]
            return data["user"]
        else:
            raise Exception(f"Login failed: {response.json()}")
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}
    
    def refresh_access_token(self):
        response = requests.post(f"{self.base_url}/auth/refresh", json={
            "refresh_token": self.refresh_token
        })
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            return True
        else:
            return False

# Usage
client = AuthClient("http://localhost:8000")
user = client.login("user@example.com", "password")
print(f"Logged in as: {user['email']}")
```

### JavaScript Example
```javascript
class AuthClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
        this.accessToken = localStorage.getItem('access_token');
        this.refreshToken = localStorage.getItem('refresh_token');
    }
    
    async register(email, password, githubToken, aiApiKey) {
        const response = await fetch(`${this.baseUrl}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email,
                password,
                github_token: githubToken,
                ai_api_key: aiApiKey
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            this.setTokens(data.access_token, data.refresh_token);
            return data.user;
        } else {
            const error = await response.json();
            throw new Error(error.detail);
        }
    }
    
    async login(email, password) {
        const response = await fetch(`${this.baseUrl}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        if (response.ok) {
            const data = await response.json();
            this.setTokens(data.access_token, data.refresh_token);
            return data.user;
        } else {
            const error = await response.json();
            throw new Error(error.detail);
        }
    }
    
    setTokens(accessToken, refreshToken) {
        this.accessToken = accessToken;
        this.refreshToken = refreshToken;
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
    }
    
    getAuthHeaders() {
        return {
            'Authorization': `Bearer ${this.accessToken}`,
            'Content-Type': 'application/json'
        };
    }
    
    async refreshAccessToken() {
        const response = await fetch(`${this.baseUrl}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: this.refreshToken })
        });
        
        if (response.ok) {
            const data = await response.json();
            this.accessToken = data.access_token;
            localStorage.setItem('access_token', data.access_token);
            return true;
        }
        return false;
    }
}

// Usage
const client = new AuthClient('http://localhost:8000');
const user = await client.login('user@example.com', 'password');
console.log(`Logged in as: ${user.email}`);
```