# Dashboard API

The Dashboard API provides comprehensive project management, filtering, sorting, and analytics for user learning projects.

## Base URL
```
/dashboard
```

## Endpoints

### Get User Dashboard

Get user dashboard with projects, filtering, sorting, and statistics.

**Endpoint:** `GET /dashboard/`

**Authentication:** Required (Bearer token)

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (≥1) |
| `page_size` | integer | 20 | Items per page (1-100) |
| `sort_by` | string | "updated_at" | Sort field ("created_at", "updated_at", "title", "completion_percentage", "status") |
| `sort_order` | string | "desc" | Sort order ("asc", "desc") |
| `status` | string | null | Filter by status ("created", "analyzing", "ready", "in_progress", "completed", "failed") |
| `language` | string | null | Filter by programming language |
| `topic_search` | string | null | Search in topics and titles |
| `created_after` | datetime | null | Filter projects created after date |
| `created_before` | datetime | null | Filter projects created before date |
| `completion_min` | float | null | Minimum completion percentage (0-100) |
| `completion_max` | float | null | Maximum completion percentage (0-100) |

**Success Response (200):**
```json
{
  "projects": [
    {
      "id": "proj_123456789",
      "title": "Learning Microservices Architecture",
      "target_repository": "https://github.com/example/microservices-demo",
      "architecture_topic": "microservices architecture",
      "concept_description": "Understanding microservices patterns and implementation",
      "status": "in_progress",
      "created_at": "2024-01-01T10:00:00Z",
      "updated_at": "2024-01-15T14:30:00Z",
      "total_tasks": 12,
      "completed_tasks": 7,
      "completion_percentage": 58.33,
      "current_task_id": "task_789",
      "implementation_language": "python",
      "preferred_frameworks": ["fastapi", "docker", "kubernetes"],
      "days_since_created": 15,
      "days_since_updated": 1,
      "is_recently_active": true
    }
  ],
  "stats": {
    "total_projects": 8,
    "projects_by_status": {
      "created": 1,
      "analyzing": 0,
      "ready": 2,
      "in_progress": 3,
      "completed": 2,
      "failed": 0
    },
    "completed_projects": 2,
    "in_progress_projects": 5,
    "average_completion_percentage": 45.67,
    "total_tasks_completed": 89,
    "most_used_languages": [
      {"language": "python", "count": 4},
      {"language": "javascript", "count": 2},
      {"language": "java", "count": 2}
    ],
    "most_used_topics": [
      {"topic": "microservices architecture", "count": 3},
      {"topic": "clean architecture", "count": 2},
      {"topic": "design patterns", "count": 2}
    ],
    "recent_activity_count": 5
  },
  "total_count": 8,
  "page": 1,
  "page_size": 20,
  "has_next_page": false,
  "has_prev_page": false
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/dashboard/?status=in_progress&sort_by=updated_at&sort_order=desc" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Get Dashboard Statistics

Get dashboard statistics only (without project list).

**Endpoint:** `GET /dashboard/stats`

**Authentication:** Required (Bearer token)

**Success Response (200):**
```json
{
  "total_projects": 8,
  "projects_by_status": {
    "created": 1,
    "analyzing": 0,
    "ready": 2,
    "in_progress": 3,
    "completed": 2,
    "failed": 0
  },
  "completed_projects": 2,
  "in_progress_projects": 5,
  "average_completion_percentage": 45.67,
  "total_tasks_completed": 89,
  "most_used_languages": [
    {"language": "python", "count": 4},
    {"language": "javascript", "count": 2},
    {"language": "java", "count": 2}
  ],
  "most_used_topics": [
    {"topic": "microservices architecture", "count": 3},
    {"topic": "clean architecture", "count": 2},
    {"topic": "design patterns", "count": 2}
  ],
  "recent_activity_count": 5
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/dashboard/stats" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Delete Project from Dashboard

Delete a project with proper authorization.

**Endpoint:** `DELETE /dashboard/projects/{project_id}`

**Authentication:** Required (Bearer token)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `project_id` | string | Project ID to delete |

**Success Response (200):**
```json
{
  "message": "Project deleted successfully",
  "project_id": "proj_123456789"
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
  "detail": "Access denied: You can only delete your own projects",
  "error_code": "ACCESS_DENIED"
}
```

**Example Request:**
```bash
curl -X DELETE "http://localhost:8000/dashboard/projects/proj_123456789" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Get Recent Activity

Get recent project activity for the dashboard.

**Endpoint:** `GET /dashboard/recent-activity`

**Authentication:** Required (Bearer token)

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 7 | Number of days to look back (1-30) |
| `limit` | integer | 10 | Maximum activities to return (1-50) |

**Success Response (200):**
```json
{
  "activities": [
    {
      "project_id": "proj_123456789",
      "title": "Learning Microservices Architecture",
      "status": "in_progress",
      "updated_at": "2024-01-15T14:30:00Z",
      "days_since_updated": 1,
      "completion_percentage": 58.33,
      "architecture_topic": "microservices architecture"
    },
    {
      "project_id": "proj_987654321",
      "title": "Clean Code Principles",
      "status": "completed",
      "updated_at": "2024-01-14T09:15:00Z",
      "days_since_updated": 2,
      "completion_percentage": 100.0,
      "architecture_topic": "clean architecture"
    }
  ],
  "total_count": 2,
  "days_looked_back": 7
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/dashboard/recent-activity?days=14&limit=20" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Dashboard Features

### Project Filtering
- **Status Filter**: Filter by project status (created, analyzing, ready, in_progress, completed, failed)
- **Language Filter**: Filter by implementation language
- **Topic Search**: Search in project titles and architecture topics
- **Date Range**: Filter by creation or update date ranges
- **Completion Range**: Filter by completion percentage ranges

### Project Sorting
- **Created Date**: Sort by project creation date
- **Updated Date**: Sort by last update date (default)
- **Title**: Sort alphabetically by project title
- **Progress**: Sort by completion percentage
- **Status**: Sort by project status

### Dashboard Statistics
- **Project Counts**: Total projects and breakdown by status
- **Progress Metrics**: Average completion percentage and total tasks completed
- **Usage Analytics**: Most used programming languages and topics
- **Activity Tracking**: Recent activity count and project updates

### Pagination
- **Page-based**: Standard page/page_size pagination
- **Metadata**: Includes total count and navigation flags
- **Performance**: Efficient queries with proper indexing

## Project Status Lifecycle

```mermaid
stateDiagram-v2
    [*] --> created: Project Created
    created --> analyzing: Background Analysis Started
    analyzing --> ready: Analysis Complete
    analyzing --> failed: Analysis Failed
    ready --> in_progress: User Starts Learning
    in_progress --> completed: All Tasks Complete
    in_progress --> in_progress: Progress Updates
    completed --> [*]: Project Finished
    failed --> analyzing: Retry Analysis
```

## Error Codes

| Code | Description |
|------|-------------|
| `PROJECT_NOT_FOUND` | Project does not exist |
| `ACCESS_DENIED` | User doesn't own the project |
| `INVALID_FILTER` | Invalid filter parameters |
| `INVALID_SORT` | Invalid sort parameters |
| `INVALID_PAGINATION` | Invalid page or page_size |

## Integration Examples

### Python Example
```python
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

class DashboardClient:
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def get_dashboard(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        language: Optional[str] = None,
        topic_search: Optional[str] = None,
        sort_by: str = "updated_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Get dashboard with filtering and sorting"""
        params = {
            "page": page,
            "page_size": page_size,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
        
        if status:
            params["status"] = status
        if language:
            params["language"] = language
        if topic_search:
            params["topic_search"] = topic_search
        
        response = requests.get(
            f"{self.base_url}/dashboard/",
            params=params,
            headers=self.headers
        )
        return response.json()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics"""
        response = requests.get(
            f"{self.base_url}/dashboard/stats",
            headers=self.headers
        )
        return response.json()
    
    def get_recent_activity(self, days: int = 7, limit: int = 10) -> Dict[str, Any]:
        """Get recent project activity"""
        params = {"days": days, "limit": limit}
        response = requests.get(
            f"{self.base_url}/dashboard/recent-activity",
            params=params,
            headers=self.headers
        )
        return response.json()
    
    def delete_project(self, project_id: str) -> Dict[str, Any]:
        """Delete a project"""
        response = requests.delete(
            f"{self.base_url}/dashboard/projects/{project_id}",
            headers=self.headers
        )
        return response.json()
    
    def get_projects_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all projects with specific status"""
        dashboard = self.get_dashboard(status=status, page_size=100)
        return dashboard["projects"]
    
    def get_completion_summary(self) -> Dict[str, Any]:
        """Get completion summary across all projects"""
        stats = self.get_stats()
        return {
            "total_projects": stats["total_projects"],
            "completed_projects": stats["completed_projects"],
            "completion_rate": stats["completed_projects"] / stats["total_projects"] * 100,
            "average_completion": stats["average_completion_percentage"],
            "total_tasks_completed": stats["total_tasks_completed"]
        }

# Usage
client = DashboardClient("http://localhost:8000", "your-jwt-token")

# Get dashboard with filters
dashboard = client.get_dashboard(
    status="in_progress",
    language="python",
    sort_by="completion_percentage",
    sort_order="desc"
)

print(f"Found {dashboard['total_count']} projects")
for project in dashboard["projects"]:
    print(f"- {project['title']}: {project['completion_percentage']:.1f}% complete")

# Get statistics
stats = client.get_stats()
print(f"Total projects: {stats['total_projects']}")
print(f"Most used language: {stats['most_used_languages'][0]['language']}")

# Get recent activity
activity = client.get_recent_activity(days=14)
print(f"Recent activity: {activity['total_count']} projects updated")
```

### JavaScript Example
```javascript
class DashboardClient {
    constructor(baseUrl, authToken) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json'
        };
    }
    
    async getDashboard(options = {}) {
        const params = new URLSearchParams({
            page: options.page || 1,
            page_size: options.pageSize || 20,
            sort_by: options.sortBy || 'updated_at',
            sort_order: options.sortOrder || 'desc',
            ...options.filters
        });
        
        const response = await fetch(
            `${this.baseUrl}/dashboard/?${params}`,
            { headers: this.headers }
        );
        return response.json();
    }
    
    async getStats() {
        const response = await fetch(
            `${this.baseUrl}/dashboard/stats`,
            { headers: this.headers }
        );
        return response.json();
    }
    
    async getRecentActivity(days = 7, limit = 10) {
        const params = new URLSearchParams({ days, limit });
        const response = await fetch(
            `${this.baseUrl}/dashboard/recent-activity?${params}`,
            { headers: this.headers }
        );
        return response.json();
    }
    
    async deleteProject(projectId) {
        const response = await fetch(
            `${this.baseUrl}/dashboard/projects/${projectId}`,
            { method: 'DELETE', headers: this.headers }
        );
        return response.json();
    }
    
    async getProjectsByStatus(status) {
        const dashboard = await this.getDashboard({
            filters: { status },
            pageSize: 100
        });
        return dashboard.projects;
    }
    
    async getCompletionSummary() {
        const stats = await this.getStats();
        return {
            totalProjects: stats.total_projects,
            completedProjects: stats.completed_projects,
            completionRate: (stats.completed_projects / stats.total_projects) * 100,
            averageCompletion: stats.average_completion_percentage,
            totalTasksCompleted: stats.total_tasks_completed
        };
    }
}

// Usage
const client = new DashboardClient('http://localhost:8000', 'your-jwt-token');

// Get dashboard with filters
const dashboard = await client.getDashboard({
    filters: {
        status: 'in_progress',
        language: 'python'
    },
    sortBy: 'completion_percentage',
    sortOrder: 'desc'
});

console.log(`Found ${dashboard.total_count} projects`);
dashboard.projects.forEach(project => {
    console.log(`- ${project.title}: ${project.completion_percentage.toFixed(1)}% complete`);
});

// Get statistics
const stats = await client.getStats();
console.log(`Total projects: ${stats.total_projects}`);
console.log(`Most used language: ${stats.most_used_languages[0].language}`);

// Get recent activity
const activity = await client.getRecentActivity(14);
console.log(`Recent activity: ${activity.total_count} projects updated`);

// Get completion summary
const summary = await client.getCompletionSummary();
console.log(`Completion rate: ${summary.completionRate.toFixed(1)}%`);
```

## Dashboard Widgets

### Project Status Widget
```javascript
// Example widget for project status distribution
function createStatusWidget(stats) {
    const statusData = stats.projects_by_status;
    const total = stats.total_projects;
    
    return {
        type: 'pie-chart',
        title: 'Project Status Distribution',
        data: Object.entries(statusData).map(([status, count]) => ({
            label: status.replace('_', ' ').toUpperCase(),
            value: count,
            percentage: (count / total * 100).toFixed(1)
        }))
    };
}
```

### Progress Widget
```javascript
// Example widget for progress tracking
function createProgressWidget(stats) {
    return {
        type: 'progress-bar',
        title: 'Overall Progress',
        metrics: [
            {
                label: 'Average Completion',
                value: stats.average_completion_percentage,
                format: 'percentage'
            },
            {
                label: 'Tasks Completed',
                value: stats.total_tasks_completed,
                format: 'number'
            },
            {
                label: 'Projects Completed',
                value: stats.completed_projects,
                total: stats.total_projects,
                format: 'fraction'
            }
        ]
    };
}
```