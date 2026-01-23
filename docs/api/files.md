# Files API

The Files API handles code editor integration and file management within learning projects with enhanced authentication and project isolation.

## Base URL
```
/projects/{project_id}/files
```

## Endpoints

### Create File

Create a new file within a project (only if user owns the project).

**Endpoint:** `POST /projects/{project_id}/files`

**Authentication:** Required (Bearer token)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `project_id` | string | Project ID |

**Request Body:**
```json
{
  "file_path": "src/services/user_service.py",
  "content": "class UserService:\n    def __init__(self):\n        pass",
  "language": "python"
}
```

**Request Schema:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file_path` | string | Yes | Relative file path within project |
| `content` | string | No | File content (default: "") |
| `language` | string | No | Programming language |

**Success Response (201):**
```json
{
  "id": "file_123456789",
  "project_id": "proj_123456789",
  "file_path": "src/services/user_service.py",
  "content": "class UserService:\n    def __init__(self):\n        pass",
  "language": "python",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

**Error Responses:**
```json
// 404 - Project Not Found
{
  "detail": "Project not found",
  "error_code": "PROJECT_NOT_FOUND"
}

// 403 - Access Denied
{
  "detail": "Access denied: You can only modify your own projects",
  "error_code": "ACCESS_DENIED"
}

// 409 - File Already Exists
{
  "detail": "File 'src/services/user_service.py' already exists",
  "error_code": "FILE_EXISTS"
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/projects/proj_123456789/files" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "src/services/user_service.py",
    "content": "class UserService:\n    def __init__(self):\n        pass",
    "language": "python"
  }'
```

---

### List Files

List all files in a project, optionally filtered by language.

**Endpoint:** `GET /projects/{project_id}/files`

**Authentication:** Required (Bearer token)

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `language` | string | Filter by programming language |

**Success Response (200):**
```json
{
  "files": [
    {
      "id": "file_123456789",
      "project_id": "proj_123456789",
      "file_path": "src/services/user_service.py",
      "content": "class UserService:\n    def __init__(self):\n        pass",
      "language": "python",
      "created_at": "2024-01-01T10:00:00Z",
      "updated_at": "2024-01-01T10:00:00Z"
    },
    {
      "id": "file_987654321",
      "project_id": "proj_123456789",
      "file_path": "src/models/user.py",
      "content": "from dataclasses import dataclass\n\n@dataclass\nclass User:\n    id: str\n    email: str",
      "language": "python",
      "created_at": "2024-01-01T11:00:00Z",
      "updated_at": "2024-01-01T11:00:00Z"
    }
  ],
  "total_count": 2
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/projects/proj_123456789/files?language=python" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Get File

Get a specific file by path within a project.

**Endpoint:** `GET /projects/{project_id}/files/{file_path}`

**Authentication:** Required (Bearer token)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `project_id` | string | Project ID |
| `file_path` | string | File path (URL encoded) |

**Success Response (200):**
```json
{
  "id": "file_123456789",
  "project_id": "proj_123456789",
  "file_path": "src/services/user_service.py",
  "content": "class UserService:\n    def __init__(self, repository):\n        self.repository = repository\n    \n    def create_user(self, user_data):\n        return self.repository.save(user_data)",
  "language": "python",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T14:30:00Z"
}
```

**Error Responses:**
```json
// 404 - File Not Found
{
  "detail": "File 'src/services/user_service.py' not found",
  "error_code": "FILE_NOT_FOUND"
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/projects/proj_123456789/files/src%2Fservices%2Fuser_service.py" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Update File

Update file content (creates file if it doesn't exist - upsert behavior).

**Endpoint:** `PUT /projects/{project_id}/files/{file_path}`

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "content": "class UserService:\n    def __init__(self, repository):\n        self.repository = repository\n    \n    def create_user(self, user_data):\n        # Validate user data\n        if not user_data.get('email'):\n            raise ValueError('Email is required')\n        \n        return self.repository.save(user_data)",
  "language": "python"
}
```

**Request Schema:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | string | Yes | Updated file content |
| `language` | string | No | Programming language |

**Success Response (200):**
```json
{
  "id": "file_123456789",
  "project_id": "proj_123456789",
  "file_path": "src/services/user_service.py",
  "content": "class UserService:\n    def __init__(self, repository):\n        self.repository = repository\n    \n    def create_user(self, user_data):\n        # Validate user data\n        if not user_data.get('email'):\n            raise ValueError('Email is required')\n        \n        return self.repository.save(user_data)",
  "language": "python",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T15:45:00Z"
}
```

**Example Request:**
```bash
curl -X PUT "http://localhost:8000/projects/proj_123456789/files/src%2Fservices%2Fuser_service.py" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "content": "class UserService:\n    def create_user(self, data):\n        return self.repo.save(data)",
    "language": "python"
  }'
```

---

### Delete File

Delete a file from a project.

**Endpoint:** `DELETE /projects/{project_id}/files/{file_path}`

**Authentication:** Required (Bearer token)

**Success Response (204):** No content

**Error Responses:**
```json
// 404 - File Not Found
{
  "detail": "File 'src/services/user_service.py' not found",
  "error_code": "FILE_NOT_FOUND"
}
```

**Example Request:**
```bash
curl -X DELETE "http://localhost:8000/projects/proj_123456789/files/src%2Fservices%2Fuser_service.py" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Get Project Structure

Get the hierarchical structure of files in a project.

**Endpoint:** `GET /projects/{project_id}/structure`

**Authentication:** Required (Bearer token)

**Success Response (200):**
```json
{
  "project_id": "proj_123456789",
  "structure": [
    {
      "name": "src",
      "path": "src",
      "type": "directory",
      "children": [
        {
          "name": "services",
          "path": "src/services",
          "type": "directory",
          "children": [
            {
              "name": "user_service.py",
              "path": "src/services/user_service.py",
              "type": "file",
              "children": null,
              "language": "python",
              "size": 245
            }
          ],
          "language": null,
          "size": null
        },
        {
          "name": "models",
          "path": "src/models",
          "type": "directory",
          "children": [
            {
              "name": "user.py",
              "path": "src/models/user.py",
              "type": "file",
              "children": null,
              "language": "python",
              "size": 128
            }
          ],
          "language": null,
          "size": null
        }
      ],
      "language": null,
      "size": null
    },
    {
      "name": "README.md",
      "path": "README.md",
      "type": "file",
      "children": null,
      "language": "markdown",
      "size": 512
    }
  ],
  "total_files": 3
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/projects/proj_123456789/structure" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Create Multiple Files

Create multiple files in a project at once (batch operation).

**Endpoint:** `POST /projects/{project_id}/files/batch`

**Authentication:** Required (Bearer token)

**Request Body:**
```json
[
  {
    "file_path": "src/models/user.py",
    "content": "from dataclasses import dataclass\n\n@dataclass\nclass User:\n    id: str\n    email: str",
    "language": "python"
  },
  {
    "file_path": "src/services/user_service.py",
    "content": "class UserService:\n    def __init__(self):\n        pass",
    "language": "python"
  },
  {
    "file_path": "tests/test_user_service.py",
    "content": "import pytest\nfrom src.services.user_service import UserService\n\ndef test_user_service_creation():\n    service = UserService()\n    assert service is not None",
    "language": "python"
  }
]
```

**Success Response (200):**
```json
[
  {
    "id": "file_111111111",
    "project_id": "proj_123456789",
    "file_path": "src/models/user.py",
    "content": "from dataclasses import dataclass\n\n@dataclass\nclass User:\n    id: str\n    email: str",
    "language": "python",
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T10:00:00Z"
  },
  {
    "id": "file_222222222",
    "project_id": "proj_123456789",
    "file_path": "src/services/user_service.py",
    "content": "class UserService:\n    def __init__(self):\n        pass",
    "language": "python",
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T10:00:00Z"
  },
  {
    "id": "file_333333333",
    "project_id": "proj_123456789",
    "file_path": "tests/test_user_service.py",
    "content": "import pytest\nfrom src.services.user_service import UserService\n\ndef test_user_service_creation():\n    service = UserService()\n    assert service is not None",
    "language": "python",
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T10:00:00Z"
  }
]
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/projects/proj_123456789/files/batch" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '[
    {
      "file_path": "src/models/user.py",
      "content": "class User:\n    pass",
      "language": "python"
    }
  ]'
```

---

### Search Files

Search files by content or filename.

**Endpoint:** `GET /projects/{project_id}/files/search/{query}`

**Authentication:** Required (Bearer token)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `project_id` | string | Project ID |
| `query` | string | Search query |

**Success Response (200):**
```json
{
  "files": [
    {
      "id": "file_123456789",
      "project_id": "proj_123456789",
      "file_path": "src/services/user_service.py",
      "content": "class UserService:\n    def create_user(self, user_data):\n        return self.repository.save(user_data)",
      "language": "python",
      "created_at": "2024-01-01T10:00:00Z",
      "updated_at": "2024-01-01T14:30:00Z"
    }
  ],
  "total_count": 1
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/projects/proj_123456789/files/search/UserService" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## File Management Features

### File Operations
- **Create**: Create new files with content and language detection
- **Read**: Retrieve file content and metadata
- **Update**: Modify file content (upsert behavior)
- **Delete**: Remove files from project
- **Batch Create**: Create multiple files in one operation

### Project Structure
- **Hierarchical View**: Tree structure of directories and files
- **File Metadata**: Size, language, timestamps
- **Directory Organization**: Automatic directory structure building

### Search and Discovery
- **Content Search**: Search within file content
- **Filename Search**: Search by file path/name
- **Language Filtering**: Filter files by programming language

### Security and Access Control
- **User Isolation**: Users can only access their own project files
- **Project Ownership**: File operations require project ownership
- **Path Validation**: Secure file path handling

## Error Codes

| Code | Description |
|------|-------------|
| `PROJECT_NOT_FOUND` | Project does not exist |
| `ACCESS_DENIED` | User doesn't own the project |
| `FILE_NOT_FOUND` | File does not exist |
| `FILE_EXISTS` | File already exists (create operation) |
| `INVALID_FILE_PATH` | File path format is invalid |
| `FILE_TOO_LARGE` | File content exceeds size limit |

## Integration Examples

### Python Example
```python
import requests
from typing import List, Dict, Any, Optional

class FilesClient:
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def create_file(
        self,
        project_id: str,
        file_path: str,
        content: str = "",
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new file in project"""
        payload = {
            "file_path": file_path,
            "content": content
        }
        
        if language:
            payload["language"] = language
        
        response = requests.post(
            f"{self.base_url}/projects/{project_id}/files",
            json=payload,
            headers=self.headers
        )
        return response.json()
    
    def get_file(self, project_id: str, file_path: str) -> Dict[str, Any]:
        """Get file by path"""
        # URL encode the file path
        import urllib.parse
        encoded_path = urllib.parse.quote(file_path, safe='')
        
        response = requests.get(
            f"{self.base_url}/projects/{project_id}/files/{encoded_path}",
            headers=self.headers
        )
        return response.json()
    
    def update_file(
        self,
        project_id: str,
        file_path: str,
        content: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update file content"""
        import urllib.parse
        encoded_path = urllib.parse.quote(file_path, safe='')
        
        payload = {"content": content}
        if language:
            payload["language"] = language
        
        response = requests.put(
            f"{self.base_url}/projects/{project_id}/files/{encoded_path}",
            json=payload,
            headers=self.headers
        )
        return response.json()
    
    def list_files(
        self,
        project_id: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """List all files in project"""
        params = {}
        if language:
            params["language"] = language
        
        response = requests.get(
            f"{self.base_url}/projects/{project_id}/files",
            params=params,
            headers=self.headers
        )
        return response.json()
    
    def get_project_structure(self, project_id: str) -> Dict[str, Any]:
        """Get project file structure"""
        response = requests.get(
            f"{self.base_url}/projects/{project_id}/structure",
            headers=self.headers
        )
        return response.json()
    
    def create_multiple_files(
        self,
        project_id: str,
        files: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create multiple files at once"""
        response = requests.post(
            f"{self.base_url}/projects/{project_id}/files/batch",
            json=files,
            headers=self.headers
        )
        return response.json()
    
    def search_files(
        self,
        project_id: str,
        query: str
    ) -> Dict[str, Any]:
        """Search files by content or filename"""
        response = requests.get(
            f"{self.base_url}/projects/{project_id}/files/search/{query}",
            headers=self.headers
        )
        return response.json()
    
    def delete_file(self, project_id: str, file_path: str) -> bool:
        """Delete a file"""
        import urllib.parse
        encoded_path = urllib.parse.quote(file_path, safe='')
        
        response = requests.delete(
            f"{self.base_url}/projects/{project_id}/files/{encoded_path}",
            headers=self.headers
        )
        return response.status_code == 204

# Usage
client = FilesClient("http://localhost:8000", "your-jwt-token")

# Create a file
file_data = client.create_file(
    project_id="proj_123456789",
    file_path="src/services/user_service.py",
    content="class UserService:\n    def __init__(self):\n        pass",
    language="python"
)

print(f"Created file: {file_data['id']}")

# Get project structure
structure = client.get_project_structure("proj_123456789")
print(f"Project has {structure['total_files']} files")

# Create multiple files
files_to_create = [
    {
        "file_path": "src/models/user.py",
        "content": "class User:\n    pass",
        "language": "python"
    },
    {
        "file_path": "tests/test_user.py",
        "content": "def test_user():\n    pass",
        "language": "python"
    }
]

created_files = client.create_multiple_files("proj_123456789", files_to_create)
print(f"Created {len(created_files)} files")

# Search files
search_results = client.search_files("proj_123456789", "UserService")
print(f"Found {search_results['total_count']} files matching 'UserService'")
```

### JavaScript Example
```javascript
class FilesClient {
    constructor(baseUrl, authToken) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json'
        };
    }
    
    async createFile(projectId, filePath, content = '', language = null) {
        const payload = { file_path: filePath, content };
        if (language) payload.language = language;
        
        const response = await fetch(`${this.baseUrl}/projects/${projectId}/files`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(payload)
        });
        
        return response.json();
    }
    
    async getFile(projectId, filePath) {
        const encodedPath = encodeURIComponent(filePath);
        const response = await fetch(
            `${this.baseUrl}/projects/${projectId}/files/${encodedPath}`,
            { headers: this.headers }
        );
        return response.json();
    }
    
    async updateFile(projectId, filePath, content, language = null) {
        const encodedPath = encodeURIComponent(filePath);
        const payload = { content };
        if (language) payload.language = language;
        
        const response = await fetch(
            `${this.baseUrl}/projects/${projectId}/files/${encodedPath}`,
            {
                method: 'PUT',
                headers: this.headers,
                body: JSON.stringify(payload)
            }
        );
        
        return response.json();
    }
    
    async listFiles(projectId, language = null) {
        const params = new URLSearchParams();
        if (language) params.append('language', language);
        
        const url = `${this.baseUrl}/projects/${projectId}/files${params.toString() ? '?' + params : ''}`;
        const response = await fetch(url, { headers: this.headers });
        return response.json();
    }
    
    async getProjectStructure(projectId) {
        const response = await fetch(
            `${this.baseUrl}/projects/${projectId}/structure`,
            { headers: this.headers }
        );
        return response.json();
    }
    
    async createMultipleFiles(projectId, files) {
        const response = await fetch(`${this.baseUrl}/projects/${projectId}/files/batch`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(files)
        });
        
        return response.json();
    }
    
    async searchFiles(projectId, query) {
        const response = await fetch(
            `${this.baseUrl}/projects/${projectId}/files/search/${encodeURIComponent(query)}`,
            { headers: this.headers }
        );
        return response.json();
    }
    
    async deleteFile(projectId, filePath) {
        const encodedPath = encodeURIComponent(filePath);
        const response = await fetch(
            `${this.baseUrl}/projects/${projectId}/files/${encodedPath}`,
            { method: 'DELETE', headers: this.headers }
        );
        return response.status === 204;
    }
}

// Usage
const client = new FilesClient('http://localhost:8000', 'your-jwt-token');

// Create a file
const fileData = await client.createFile(
    'proj_123456789',
    'src/services/user_service.py',
    'class UserService:\n    def __init__(self):\n        pass',
    'python'
);

console.log(`Created file: ${fileData.id}`);

// Get project structure
const structure = await client.getProjectStructure('proj_123456789');
console.log(`Project has ${structure.total_files} files`);

// Create multiple files
const filesToCreate = [
    {
        file_path: 'src/models/user.py',
        content: 'class User:\n    pass',
        language: 'python'
    },
    {
        file_path: 'tests/test_user.py',
        content: 'def test_user():\n    pass',
        language: 'python'
    }
];

const createdFiles = await client.createMultipleFiles('proj_123456789', filesToCreate);
console.log(`Created ${createdFiles.length} files`);

// Search files
const searchResults = await client.searchFiles('proj_123456789', 'UserService');
console.log(`Found ${searchResults.total_count} files matching 'UserService'`);
```

## File Structure Best Practices

### Directory Organization
```
project/
├── src/
│   ├── models/          # Data models
│   ├── services/        # Business logic
│   ├── controllers/     # API controllers
│   └── utils/           # Utility functions
├── tests/
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   └── fixtures/       # Test data
├── docs/               # Documentation
└── config/             # Configuration files
```

### File Naming Conventions
- **Python**: `snake_case.py` (e.g., `user_service.py`)
- **JavaScript**: `camelCase.js` or `kebab-case.js`
- **Java**: `PascalCase.java` (e.g., `UserService.java`)
- **Tests**: `test_*.py`, `*.test.js`, `*Test.java`