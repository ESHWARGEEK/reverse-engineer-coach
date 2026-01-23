# Projects API

The Projects API handles learning project creation, management, and progress tracking with enhanced authentication and repository discovery integration.

## Base URL
```
/projects
```

## Endpoints

### Create Project

Create a new learning project with repository analysis.

**Endpoint:** `POST /projects/`

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "title": "Learning Microservices Architecture",
  "target_repository": "https://github.com/example/microservices-demo",
  "architecture_topic": "microservices architecture",
  "implementation_language": "python",
  "preferred_frameworks": ["fastapi", "docker", "kubernetes"],
  "language_specific_config": {
    "python_version": "3.9",
    "package_manager": "pip"
  },
  "concept_description": "Understanding microservices patterns and implementation",
  "discovery_metadata": {
    "source": "manual_entry",
    "search_terms": ["microservices", "architecture"]
  }
}
```

**Request Schema:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Project title (1-255 chars) |
| `target_repository` | string | Yes | GitHub repository URL |
| `architecture_topic` | string | Yes | Architecture topic to focus on |
| `implementation_language` | string | No | Target language (default: "python") |
| `preferred_frameworks` | array | No | Preferred frameworks for implementation |
| `language_specific_config` | object | No | Language-specific configuration |
| `concept_description` | string | No | Learning concept description |
| `discovery_metadata` | object | No | Repository discovery metadata |

**Success Response (201):**
```json
{
  "id": "proj_123456789",
  "user_id": "user_123456789",
  "title": "Learning Microservices Architecture",
  "target_repository": "https://github.com/example/microservices-demo",
  "architecture_topic": "microservices architecture",
  "status": "created",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z",
  "total_tasks": 0,
  "completed_tasks": 0,
  "current_task_id": null,
  "completion_percentage": 0.0,
  "implementation_language": "python",
  "preferred_frameworks": ["fastapi", "docker", "kubernetes"],
  "concept_description": "Understanding microservices patterns and implementation",
  "discovery_metadata": {
    "source": "manual_entry",
    "search_terms": ["microservices", "architecture"]
  }
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/projects/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Learning Microservices Architecture",
    "target_repository": "https://github.com/example/microservices-demo",
    "architecture_topic": "microservices architecture",
    "implementation_language": "python"
  }'
```

---

### Create Project from Discovery

Create a project from a discovered repository suggestion with enhanced analysis.

**Endpoint:** `POST /projects/from-discovery`

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "title": "Learning Microservices with Spring Boot",
  "repository_suggestion": {
    "repository_url": "https://github.com/example/spring-microservices",
    "repository_name": "spring-microservices",
    "description": "Spring Boot microservices with Eureka and Zuul",
    "stars": 890,
    "language": "java",
    "quality_score": 0.78,
    "educational_value": 0.85,
    "overall_score": 0.82
  },
  "learning_concept": "microservices architecture patterns",
  "implementation_language": "java",
  "preferred_frameworks": ["spring-boot", "eureka", "zuul"]
}
```

**Request Schema:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Project title (1-255 chars) |
| `repository_suggestion` | object | Yes | Repository suggestion from discovery |
| `learning_concept` | string | Yes | Original learning concept (3-500 chars) |
| `implementation_language` | string | No | Target language (default: "python") |
| `preferred_frameworks` | array | No | Preferred frameworks |

**Success Response (201):**
```json
{
  "id": "proj_987654321",
  "user_id": "user_123456789",
  "title": "Learning Microservices with Spring Boot",
  "target_repository": "https://github.com/example/spring-microservices",
  "architecture_topic": "microservices architecture patterns",
  "status": "created",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z",
  "total_tasks": 0,
  "completed_tasks": 0,
  "current_task_id": null,
  "completion_percentage": 0.0,
  "implementation_language": "java",
  "preferred_frameworks": ["spring-boot", "eureka", "zuul"],
  "concept_description": "microservices architecture patterns",
  "discovery_metadata": {
    "repository_suggestion": {
      "repository_url": "https://github.com/example/spring-microservices",
      "quality_score": 0.78,
      "educational_value": 0.85
    },
    "learning_concept": "microservices architecture patterns",
    "discovery_timestamp": "2024-01-01T10:00:00Z"
  }
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/projects/from-discovery" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Learning Microservices with Spring Boot",
    "repository_suggestion": {
      "repository_url": "https://github.com/example/spring-microservices",
      "quality_score": 0.78,
      "educational_value": 0.85
    },
    "learning_concept": "microservices architecture patterns",
    "implementation_language": "java"
  }'
```

---

### List Projects

List projects for the authenticated user with filtering and pagination.

**Endpoint:** `GET /projects/`

**Authentication:** Required (Bearer token)

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status_filter` | string | null | Filter by status |
| `page` | integer | 1 | Page number |
| `page_size` | integer | 20 | Items per page |

**Success Response (200):**
```json
{
  "projects": [
    {
      "id": "proj_123456789",
      "user_id": "user_123456789",
      "title": "Learning Microservices Architecture",
      "target_repository": "https://github.com/example/microservices-demo",
      "architecture_topic": "microservices architecture",
      "status": "in_progress",
      "created_at": "2024-01-01T10:00:00Z",
      "updated_at": "2024-01-15T14:30:00Z",
      "total_tasks": 12,
      "completed_tasks": 7,
      "current_task_id": "task_789",
      "completion_percentage": 58.33,
      "implementation_language": "python",
      "preferred_frameworks": ["fastapi", "docker", "kubernetes"],
      "concept_description": "Understanding microservices patterns",
      "discovery_metadata": null
    }
  ],
  "total_count": 1,
  "page": 1,
  "page_size": 20
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/projects/?status_filter=in_progress&page=1&page_size=10" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Get Project

Get a specific project by ID (only if owned by current user).

**Endpoint:** `GET /projects/{project_id}`

**Authentication:** Required (Bearer token)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `project_id` | string | Project ID |

**Success Response (200):**
```json
{
  "id": "proj_123456789",
  "user_id": "user_123456789",
  "title": "Learning Microservices Architecture",
  "target_repository": "https://github.com/example/microservices-demo",
  "architecture_topic": "microservices architecture",
  "status": "in_progress",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-15T14:30:00Z",
  "total_tasks": 12,
  "completed_tasks": 7,
  "current_task_id": "task_789",
  "completion_percentage": 58.33,
  "implementation_language": "python",
  "preferred_frameworks": ["fastapi", "docker", "kubernetes"],
  "concept_description": "Understanding microservices patterns",
  "discovery_metadata": {
    "analysis_results": {
      "educational_value": 0.92,
      "complexity_level": "intermediate"
    }
  }
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
  "detail": "Access denied: You can only access your own projects",
  "error_code": "ACCESS_DENIED"
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/projects/proj_123456789" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Update Project

Update a project's details (only if owned by current user).

**Endpoint:** `PUT /projects/{project_id}`

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "title": "Advanced Microservices Architecture",
  "status": "in_progress",
  "current_task_id": "task_890",
  "implementation_language": "typescript",
  "preferred_frameworks": ["nestjs", "docker", "kubernetes"]
}
```

**Request Schema:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | No | New project title |
| `status` | string | No | Project status |
| `current_task_id` | string | No | Current task ID |
| `implementation_language` | string | No | Implementation language |
| `preferred_frameworks` | array | No | Preferred frameworks |

**Success Response (200):**
```json
{
  "id": "proj_123456789",
  "user_id": "user_123456789",
  "title": "Advanced Microservices Architecture",
  "target_repository": "https://github.com/example/microservices-demo",
  "architecture_topic": "microservices architecture",
  "status": "in_progress",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-16T09:15:00Z",
  "total_tasks": 12,
  "completed_tasks": 7,
  "current_task_id": "task_890",
  "completion_percentage": 58.33,
  "implementation_language": "typescript",
  "preferred_frameworks": ["nestjs", "docker", "kubernetes"],
  "concept_description": "Understanding microservices patterns",
  "discovery_metadata": null
}
```

**Example Request:**
```bash
curl -X PUT "http://localhost:8000/projects/proj_123456789" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Advanced Microservices Architecture",
    "implementation_language": "typescript"
  }'
```

---

### Delete Project

Delete a project and all associated data (only if owned by current user).

**Endpoint:** `DELETE /projects/{project_id}`

**Authentication:** Required (Bearer token)

**Success Response (204):** No content

**Error Responses:**
```json
// 404 - Project Not Found
{
  "detail": "Project not found",
  "error_code": "PROJECT_NOT_FOUND"
}

// 403 - Access Denied
{
  "detail": "Access denied: You can only delete your own projects",
  "error_code": "ACCESS_DENIED"
}
```

**Example Request:**
```bash
curl -X DELETE "http://localhost:8000/projects/proj_123456789" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Get Project Progress

Get detailed progress information for a project.

**Endpoint:** `GET /projects/{project_id}/progress`

**Authentication:** Required (Bearer token)

**Success Response (200):**
```json
{
  "project_id": "proj_123456789",
  "total_tasks": 12,
  "completed_tasks": 7,
  "completion_percentage": 58.33,
  "current_task_id": "task_789",
  "status": "in_progress"
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/projects/proj_123456789/progress" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Update Project Progress

Update project progress tracking.

**Endpoint:** `POST /projects/{project_id}/progress`

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "completed_tasks": 8,
  "current_task_id": "task_890"
}
```

**Request Schema:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `completed_tasks` | integer | Yes | Number of completed tasks (≥0) |
| `current_task_id` | string | No | Current task ID |

**Success Response (200):**
```json
{
  "project_id": "proj_123456789",
  "total_tasks": 12,
  "completed_tasks": 8,
  "completion_percentage": 66.67,
  "current_task_id": "task_890",
  "status": "in_progress"
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/projects/proj_123456789/progress" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "completed_tasks": 8,
    "current_task_id": "task_890"
  }'
```

---

### Search Projects by Topic

Search projects by architecture topic (only user's own projects).

**Endpoint:** `GET /projects/search/{topic}`

**Authentication:** Required (Bearer token)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `topic` | string | Topic to search for |

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `page_size` | integer | 20 | Items per page |

**Success Response (200):**
```json
{
  "projects": [
    {
      "id": "proj_123456789",
      "title": "Learning Microservices Architecture",
      "architecture_topic": "microservices architecture",
      "status": "in_progress",
      "completion_percentage": 58.33
    }
  ],
  "total_count": 1,
  "page": 1,
  "page_size": 20
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/projects/search/microservices" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Get Supported Languages

Get list of supported programming languages for implementation.

**Endpoint:** `GET /projects/languages/supported`

**Authentication:** Not required

**Success Response (200):**
```json
{
  "languages": [
    {
      "language": "python",
      "display_name": "Python",
      "frameworks": ["fastapi", "django", "flask"],
      "syntax_style": "indentation",
      "package_manager": "pip",
      "test_framework": "pytest",
      "conventions": {
        "naming": "snake_case",
        "file_extension": ".py"
      }
    },
    {
      "language": "javascript",
      "display_name": "JavaScript",
      "frameworks": ["express", "react", "vue"],
      "syntax_style": "braces",
      "package_manager": "npm",
      "test_framework": "jest",
      "conventions": {
        "naming": "camelCase",
        "file_extension": ".js"
      }
    }
  ],
  "default_language": "python"
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/projects/languages/supported"
```

---

### Translate Code Cross-Language

Translate code from one programming language to another while preserving architectural patterns.

**Endpoint:** `POST /projects/languages/translate`

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "source_code": "class UserService:\n    def __init__(self, repository):\n        self.repository = repository\n    \n    def create_user(self, user_data):\n        return self.repository.save(user_data)",
  "source_language": "python",
  "target_language": "java",
  "patterns": ["dependency-injection", "repository-pattern"]
}
```

**Request Schema:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_code` | string | Yes | Source code to translate |
| `source_language` | string | Yes | Source programming language |
| `target_language` | string | Yes | Target programming language |
| `patterns` | array | No | Architectural patterns to preserve |

**Success Response (200):**
```json
{
  "success": true,
  "translated_code": "@Service\npublic class UserService {\n    private final UserRepository repository;\n    \n    public UserService(UserRepository repository) {\n        this.repository = repository;\n    }\n    \n    public User createUser(UserData userData) {\n        return repository.save(userData);\n    }\n}",
  "source_language": "python",
  "target_language": "java",
  "preserved_patterns": ["dependency-injection", "repository-pattern"],
  "translation_notes": [
    "Added @Service annotation for Spring dependency injection",
    "Converted snake_case to camelCase naming convention",
    "Added explicit type declarations"
  ],
  "tokens_used": 150,
  "error": null
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/projects/languages/translate" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "source_code": "class UserService:\n    def create_user(self, data):\n        return self.repo.save(data)",
    "source_language": "python",
    "target_language": "java",
    "patterns": ["dependency-injection"]
  }'
```

## Project Lifecycle

### Status Flow
```mermaid
stateDiagram-v2
    [*] --> created: Project Created
    created --> analyzing: Background Analysis
    analyzing --> ready: Analysis Complete
    analyzing --> failed: Analysis Failed
    ready --> in_progress: User Starts
    in_progress --> completed: All Tasks Done
    failed --> analyzing: Retry Analysis
    completed --> [*]: Project Finished
```

### Background Processing
1. **Project Creation**: Project created with "created" status
2. **Repository Analysis**: Background task analyzes repository and generates learning spec
3. **Status Update**: Project status updated to "ready" when analysis completes
4. **User Interaction**: User can start learning when project is "ready"
5. **Progress Tracking**: Progress updated as user completes tasks

## Error Codes

| Code | Description |
|------|-------------|
| `PROJECT_NOT_FOUND` | Project does not exist |
| `ACCESS_DENIED` | User doesn't own the project |
| `INVALID_REPOSITORY_URL` | Repository URL format is invalid |
| `REPOSITORY_ANALYSIS_FAILED` | Background analysis failed |
| `UNSUPPORTED_LANGUAGE` | Programming language not supported |
| `TRANSLATION_FAILED` | Code translation failed |
| `INVALID_PROGRESS_UPDATE` | Progress update validation failed |

## Integration Examples

### Python Example
```python
import requests
from typing import List, Dict, Any, Optional

class ProjectsClient:
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def create_project(
        self,
        title: str,
        repository_url: str,
        architecture_topic: str,
        language: str = "python",
        frameworks: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a new learning project"""
        payload = {
            "title": title,
            "target_repository": repository_url,
            "architecture_topic": architecture_topic,
            "implementation_language": language
        }
        
        if frameworks:
            payload["preferred_frameworks"] = frameworks
        
        response = requests.post(
            f"{self.base_url}/projects/",
            json=payload,
            headers=self.headers
        )
        return response.json()
    
    def create_from_discovery(
        self,
        title: str,
        repository_suggestion: Dict[str, Any],
        learning_concept: str,
        language: str = "python"
    ) -> Dict[str, Any]:
        """Create project from discovery suggestion"""
        payload = {
            "title": title,
            "repository_suggestion": repository_suggestion,
            "learning_concept": learning_concept,
            "implementation_language": language
        }
        
        response = requests.post(
            f"{self.base_url}/projects/from-discovery",
            json=payload,
            headers=self.headers
        )
        return response.json()
    
    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get project by ID"""
        response = requests.get(
            f"{self.base_url}/projects/{project_id}",
            headers=self.headers
        )
        return response.json()
    
    def list_projects(
        self,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """List user projects"""
        params = {"page": page, "page_size": page_size}
        if status_filter:
            params["status_filter"] = status_filter
        
        response = requests.get(
            f"{self.base_url}/projects/",
            params=params,
            headers=self.headers
        )
        return response.json()
    
    def update_progress(
        self,
        project_id: str,
        completed_tasks: int,
        current_task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update project progress"""
        payload = {"completed_tasks": completed_tasks}
        if current_task_id:
            payload["current_task_id"] = current_task_id
        
        response = requests.post(
            f"{self.base_url}/projects/{project_id}/progress",
            json=payload,
            headers=self.headers
        )
        return response.json()
    
    def translate_code(
        self,
        source_code: str,
        source_language: str,
        target_language: str,
        patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Translate code between languages"""
        payload = {
            "source_code": source_code,
            "source_language": source_language,
            "target_language": target_language
        }
        
        if patterns:
            payload["patterns"] = patterns
        
        response = requests.post(
            f"{self.base_url}/projects/languages/translate",
            json=payload,
            headers=self.headers
        )
        return response.json()

# Usage
client = ProjectsClient("http://localhost:8000", "your-jwt-token")

# Create a project
project = client.create_project(
    title="Learning Clean Architecture",
    repository_url="https://github.com/example/clean-architecture",
    architecture_topic="clean architecture",
    language="python",
    frameworks=["fastapi", "sqlalchemy"]
)

print(f"Created project: {project['id']}")

# List projects
projects = client.list_projects(status_filter="in_progress")
print(f"Found {projects['total_count']} in-progress projects")

# Update progress
progress = client.update_progress(
    project_id=project['id'],
    completed_tasks=5,
    current_task_id="task_123"
)
print(f"Progress: {progress['completion_percentage']:.1f}%")
```

### JavaScript Example
```javascript
class ProjectsClient {
    constructor(baseUrl, authToken) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json'
        };
    }
    
    async createProject(title, repositoryUrl, architectureTopic, options = {}) {
        const payload = {
            title,
            target_repository: repositoryUrl,
            architecture_topic: architectureTopic,
            implementation_language: options.language || 'python',
            ...options
        };
        
        const response = await fetch(`${this.baseUrl}/projects/`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(payload)
        });
        
        return response.json();
    }
    
    async createFromDiscovery(title, repositorySuggestion, learningConcept, language = 'python') {
        const payload = {
            title,
            repository_suggestion: repositorySuggestion,
            learning_concept: learningConcept,
            implementation_language: language
        };
        
        const response = await fetch(`${this.baseUrl}/projects/from-discovery`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(payload)
        });
        
        return response.json();
    }
    
    async getProject(projectId) {
        const response = await fetch(`${this.baseUrl}/projects/${projectId}`, {
            headers: this.headers
        });
        return response.json();
    }
    
    async listProjects(options = {}) {
        const params = new URLSearchParams({
            page: options.page || 1,
            page_size: options.pageSize || 20
        });
        
        if (options.statusFilter) {
            params.append('status_filter', options.statusFilter);
        }
        
        const response = await fetch(`${this.baseUrl}/projects/?${params}`, {
            headers: this.headers
        });
        return response.json();
    }
    
    async updateProgress(projectId, completedTasks, currentTaskId = null) {
        const payload = { completed_tasks: completedTasks };
        if (currentTaskId) {
            payload.current_task_id = currentTaskId;
        }
        
        const response = await fetch(`${this.baseUrl}/projects/${projectId}/progress`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(payload)
        });
        
        return response.json();
    }
    
    async translateCode(sourceCode, sourceLanguage, targetLanguage, patterns = []) {
        const payload = {
            source_code: sourceCode,
            source_language: sourceLanguage,
            target_language: targetLanguage,
            patterns
        };
        
        const response = await fetch(`${this.baseUrl}/projects/languages/translate`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(payload)
        });
        
        return response.json();
    }
}

// Usage
const client = new ProjectsClient('http://localhost:8000', 'your-jwt-token');

// Create a project
const project = await client.createProject(
    'Learning Clean Architecture',
    'https://github.com/example/clean-architecture',
    'clean architecture',
    {
        language: 'python',
        preferred_frameworks: ['fastapi', 'sqlalchemy']
    }
);

console.log(`Created project: ${project.id}`);

// List projects
const projects = await client.listProjects({ statusFilter: 'in_progress' });
console.log(`Found ${projects.total_count} in-progress projects`);

// Update progress
const progress = await client.updateProgress(project.id, 5, 'task_123');
console.log(`Progress: ${progress.completion_percentage.toFixed(1)}%`);
```