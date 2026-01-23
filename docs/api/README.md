# Reverse Engineer Coach API Documentation

This documentation covers all API endpoints for the Reverse Engineer Coach platform, including authentication, repository discovery, user management, and project operations.

## Table of Contents

1. [Authentication API](authentication.md)
2. [Repository Discovery API](discovery.md)
3. [User Profile API](profile.md)
4. [Dashboard API](dashboard.md)
5. [Projects API](projects.md)
6. [Files API](files.md)
7. [Integration Guide](integration-guide.md)

## API Overview

### Base URL
```
Production: https://api.reverseengineercoach.com
Development: http://localhost:8000
```

### Authentication
All API endpoints (except registration and login) require JWT authentication via the `Authorization` header:

```http
Authorization: Bearer <your-jwt-token>
```

### Content Type
All requests should use JSON content type:

```http
Content-Type: application/json
```

### Rate Limiting
API endpoints are rate-limited to prevent abuse:

- **Authentication endpoints**: 5 requests per 5 minutes
- **Discovery endpoints**: 20 requests per minute
- **Profile updates**: 10 requests per 5 minutes
- **General endpoints**: 100 requests per minute

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

### Error Responses
All errors follow a consistent format:

```json
{
  "detail": "Error message describing what went wrong",
  "error_code": "SPECIFIC_ERROR_CODE",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (invalid/missing token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error

### Pagination
List endpoints support pagination with these query parameters:

- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20, max: 100)

Paginated responses include metadata:
```json
{
  "items": [...],
  "total_count": 150,
  "page": 1,
  "page_size": 20,
  "has_next_page": true,
  "has_prev_page": false
}
```

## Quick Start

### 1. Register a New User
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "github_token": "ghp_your_github_token",
    "ai_api_key": "sk-your_openai_key"
  }'
```

### 2. Login
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'
```

### 3. Discover Repositories
```bash
curl -X POST "http://localhost:8000/discover/repositories" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "concept": "microservices architecture",
    "max_results": 5
  }'
```

### 4. Get User Dashboard
```bash
curl -X GET "http://localhost:8000/dashboard/" \
  -H "Authorization: Bearer <your-jwt-token>"
```

## API Endpoints Summary

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `POST /auth/refresh` - Refresh JWT token
- `GET /auth/me` - Get current user info
- `PUT /auth/me` - Update current user
- `GET /auth/api-keys/test` - Test API keys

### Repository Discovery
- `POST /discover/repositories` - Discover repositories by concept
- `POST /discover/analyze` - Analyze specific repository
- `POST /discover/by-language` - Discover by programming language
- `GET /discover/suggestions` - Get concept suggestions
- `GET /discover/popular-concepts` - Get popular concepts

### User Profile
- `GET /profile/` - Get user profile
- `PUT /profile/` - Update user profile
- `PUT /profile/password` - Update password
- `PUT /profile/credentials` - Update API credentials
- `GET /profile/credentials/validate` - Validate credentials
- `DELETE /profile/credentials` - Delete credentials

### Dashboard
- `GET /dashboard/` - Get user dashboard with projects
- `GET /dashboard/stats` - Get dashboard statistics
- `GET /dashboard/recent-activity` - Get recent project activity
- `DELETE /dashboard/projects/{id}` - Delete project

### Projects
- `POST /projects/` - Create new learning project
- `POST /projects/from-discovery` - Create project from discovery
- `GET /projects/` - List user projects
- `GET /projects/{id}` - Get specific project
- `PUT /projects/{id}` - Update project
- `DELETE /projects/{id}` - Delete project
- `GET /projects/{id}/progress` - Get project progress
- `POST /projects/{id}/progress` - Update project progress
- `GET /projects/search/{topic}` - Search projects by topic
- `GET /projects/languages/supported` - Get supported languages
- `POST /projects/languages/translate` - Translate code cross-language

### Files Management
- `POST /projects/{id}/files` - Create file in project
- `GET /projects/{id}/files` - List project files
- `GET /projects/{id}/files/{path}` - Get specific file
- `PUT /projects/{id}/files/{path}` - Update file content
- `DELETE /projects/{id}/files/{path}` - Delete file
- `GET /projects/{id}/structure` - Get project structure
- `POST /projects/{id}/files/batch` - Create multiple files
- `GET /projects/{id}/files/search/{query}` - Search files

## Security Considerations

### API Key Storage
- All API credentials are encrypted using AES-256 encryption
- User-specific encryption keys ensure data isolation
- Credentials are never logged or exposed in error messages

### Authentication Security
- JWT tokens expire after 24 hours (configurable)
- Refresh tokens allow seamless token renewal
- Rate limiting prevents brute force attacks
- Password hashing uses bcrypt with 12+ rounds

### Data Privacy
- User data is isolated by user ID
- No cross-user data access possible
- API responses exclude sensitive information
- Audit logging tracks all API access

## SDKs and Libraries

### Python SDK
```python
from reverse_engineer_coach import Client

client = Client(
    base_url="https://api.reverseengineercoach.com",
    email="user@example.com",
    password="your_password"
)

# Discover repositories
repositories = client.discover_repositories("microservices patterns")

# Create learning project
project = client.create_project(
    title="Learning Microservices",
    repository_url=repositories[0]["repository_url"],
    concept="microservices architecture"
)
```

### JavaScript SDK
```javascript
import { ReverseEngineerCoachClient } from '@reverse-engineer-coach/sdk';

const client = new ReverseEngineerCoachClient({
  baseUrl: 'https://api.reverseengineercoach.com',
  email: 'user@example.com',
  password: 'your_password'
});

// Discover repositories
const repositories = await client.discoverRepositories('react hooks');

// Get dashboard
const dashboard = await client.getDashboard();
```

## Webhooks (Future Feature)

The platform will support webhooks for real-time notifications:

- Project completion events
- Repository analysis completion
- Credential validation failures
- System maintenance notifications

## API Versioning

The API uses URL-based versioning:
- Current version: `v1` (default)
- Future versions: `v2`, `v3`, etc.

Example:
```
https://api.reverseengineercoach.com/v1/auth/login
https://api.reverseengineercoach.com/v2/auth/login  # Future version
```

## Support and Resources

- **API Status**: [status.reverseengineercoach.com](https://status.reverseengineercoach.com)
- **Rate Limits**: Monitor usage in your dashboard
- **Support**: Contact support with API-related issues
- **Changelog**: Track API updates and changes

---

For detailed endpoint documentation, see the specific API guides linked above.