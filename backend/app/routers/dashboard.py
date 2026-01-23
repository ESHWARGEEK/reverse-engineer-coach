"""
User Dashboard API endpoints
Provides dashboard functionality for user project management, filtering, and statistics
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum

from app.database import get_db
from app.repositories import RepositoryFactory
from app.models import User, LearningProject
from app.middleware.auth_middleware import get_current_active_user

router = APIRouter()


class ProjectStatus(str, Enum):
    """Project status enumeration."""
    CREATED = "created"
    ANALYZING = "analyzing"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectSortBy(str, Enum):
    """Project sorting options."""
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    TITLE = "title"
    PROGRESS = "completion_percentage"
    STATUS = "status"


class SortOrder(str, Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


class DashboardProjectResponse(BaseModel):
    """Dashboard project response model with additional metadata."""
    id: str
    title: str
    target_repository: str
    architecture_topic: str
    concept_description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    total_tasks: int
    completed_tasks: int
    completion_percentage: float
    current_task_id: Optional[str]
    implementation_language: Optional[str]
    preferred_frameworks: Optional[List[str]]
    
    # Additional dashboard-specific fields
    days_since_created: int
    days_since_updated: int
    is_recently_active: bool
    
    class Config:
        from_attributes = True


class DashboardStatsResponse(BaseModel):
    """Dashboard statistics response model."""
    total_projects: int
    projects_by_status: Dict[str, int]
    completed_projects: int
    in_progress_projects: int
    average_completion_percentage: float
    total_tasks_completed: int
    most_used_languages: List[Dict[str, Any]]
    most_used_topics: List[Dict[str, Any]]
    recent_activity_count: int  # Projects updated in last 7 days


class DashboardResponse(BaseModel):
    """Complete dashboard response model."""
    projects: List[DashboardProjectResponse]
    stats: DashboardStatsResponse
    total_count: int
    page: int
    page_size: int
    has_next_page: bool
    has_prev_page: bool


class ProjectFilterRequest(BaseModel):
    """Project filtering request model."""
    status: Optional[ProjectStatus] = None
    language: Optional[str] = None
    topic_search: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    completion_min: Optional[float] = Field(None, ge=0, le=100)
    completion_max: Optional[float] = Field(None, ge=0, le=100)


def _calculate_dashboard_metadata(project: LearningProject) -> Dict[str, Any]:
    """Calculate additional dashboard metadata for a project."""
    now = datetime.utcnow()
    
    days_since_created = (now - project.created_at).days
    days_since_updated = (now - project.updated_at).days
    is_recently_active = days_since_updated <= 7
    
    return {
        "days_since_created": days_since_created,
        "days_since_updated": days_since_updated,
        "is_recently_active": is_recently_active
    }


def _apply_project_filters(
    projects: List[LearningProject], 
    filters: ProjectFilterRequest
) -> List[LearningProject]:
    """Apply filters to project list."""
    filtered_projects = projects
    
    if filters.status:
        filtered_projects = [p for p in filtered_projects if p.status == filters.status.value]
    
    if filters.language:
        filtered_projects = [
            p for p in filtered_projects 
            if p.implementation_language and filters.language.lower() in p.implementation_language.lower()
        ]
    
    if filters.topic_search:
        search_term = filters.topic_search.lower()
        filtered_projects = [
            p for p in filtered_projects 
            if (search_term in p.architecture_topic.lower() or 
                (p.concept_description and search_term in p.concept_description.lower()) or
                search_term in p.title.lower())
        ]
    
    if filters.created_after:
        filtered_projects = [p for p in filtered_projects if p.created_at >= filters.created_after]
    
    if filters.created_before:
        filtered_projects = [p for p in filtered_projects if p.created_at <= filters.created_before]
    
    if filters.completion_min is not None:
        filtered_projects = [p for p in filtered_projects if p.completion_percentage >= filters.completion_min]
    
    if filters.completion_max is not None:
        filtered_projects = [p for p in filtered_projects if p.completion_percentage <= filters.completion_max]
    
    return filtered_projects


def _sort_projects(
    projects: List[LearningProject], 
    sort_by: ProjectSortBy, 
    sort_order: SortOrder
) -> List[LearningProject]:
    """Sort projects based on specified criteria."""
    reverse = sort_order == SortOrder.DESC
    
    if sort_by == ProjectSortBy.CREATED_AT:
        return sorted(projects, key=lambda p: p.created_at, reverse=reverse)
    elif sort_by == ProjectSortBy.UPDATED_AT:
        return sorted(projects, key=lambda p: p.updated_at, reverse=reverse)
    elif sort_by == ProjectSortBy.TITLE:
        return sorted(projects, key=lambda p: p.title.lower(), reverse=reverse)
    elif sort_by == ProjectSortBy.PROGRESS:
        return sorted(projects, key=lambda p: p.completion_percentage, reverse=reverse)
    elif sort_by == ProjectSortBy.STATUS:
        return sorted(projects, key=lambda p: p.status, reverse=reverse)
    else:
        return projects


def _calculate_dashboard_stats(projects: List[LearningProject]) -> DashboardStatsResponse:
    """Calculate dashboard statistics from project list."""
    total_projects = len(projects)
    
    # Count projects by status
    projects_by_status = {}
    for status in ProjectStatus:
        projects_by_status[status.value] = len([p for p in projects if p.status == status.value])
    
    completed_projects = projects_by_status.get("completed", 0)
    in_progress_projects = projects_by_status.get("in_progress", 0) + projects_by_status.get("ready", 0)
    
    # Calculate average completion percentage
    if total_projects > 0:
        average_completion = sum(p.completion_percentage for p in projects) / total_projects
    else:
        average_completion = 0.0
    
    # Calculate total tasks completed
    total_tasks_completed = sum(p.completed_tasks for p in projects)
    
    # Most used languages
    language_counts = {}
    for project in projects:
        if project.implementation_language:
            lang = project.implementation_language
            language_counts[lang] = language_counts.get(lang, 0) + 1
    
    most_used_languages = [
        {"language": lang, "count": count} 
        for lang, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    
    # Most used topics
    topic_counts = {}
    for project in projects:
        topic = project.architecture_topic
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
    
    most_used_topics = [
        {"topic": topic, "count": count} 
        for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    
    # Recent activity (projects updated in last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_activity_count = len([p for p in projects if p.updated_at >= seven_days_ago])
    
    return DashboardStatsResponse(
        total_projects=total_projects,
        projects_by_status=projects_by_status,
        completed_projects=completed_projects,
        in_progress_projects=in_progress_projects,
        average_completion_percentage=round(average_completion, 2),
        total_tasks_completed=total_tasks_completed,
        most_used_languages=most_used_languages,
        most_used_topics=most_used_topics,
        recent_activity_count=recent_activity_count
    )


@router.get("/", response_model=DashboardResponse)
async def get_user_dashboard(
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: ProjectSortBy = Query(ProjectSortBy.UPDATED_AT, description="Sort field"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order"),
    status: Optional[ProjectStatus] = Query(None, description="Filter by status"),
    language: Optional[str] = Query(None, description="Filter by language"),
    topic_search: Optional[str] = Query(None, description="Search in topics and titles"),
    created_after: Optional[datetime] = Query(None, description="Filter projects created after date"),
    created_before: Optional[datetime] = Query(None, description="Filter projects created before date"),
    completion_min: Optional[float] = Query(None, ge=0, le=100, description="Minimum completion percentage"),
    completion_max: Optional[float] = Query(None, ge=0, le=100, description="Maximum completion percentage"),
    db: Session = Depends(get_db)
):
    """
    Get user dashboard with projects, filtering, sorting, and statistics.
    
    Provides comprehensive dashboard functionality including:
    - Project list with filtering and sorting
    - Dashboard statistics and analytics
    - Pagination support
    - Recent activity tracking
    """
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        
        # Get all user projects
        all_projects = project_repo.get_by_user_id(current_user.id, limit=10000)  # Get all projects
        
        # Apply filters
        filters = ProjectFilterRequest(
            status=status,
            language=language,
            topic_search=topic_search,
            created_after=created_after,
            created_before=created_before,
            completion_min=completion_min,
            completion_max=completion_max
        )
        
        filtered_projects = _apply_project_filters(all_projects, filters)
        
        # Sort projects
        sorted_projects = _sort_projects(filtered_projects, sort_by, sort_order)
        
        # Apply pagination
        total_count = len(sorted_projects)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_projects = sorted_projects[start_idx:end_idx]
        
        # Convert to dashboard response models with metadata
        dashboard_projects = []
        for project in paginated_projects:
            metadata = _calculate_dashboard_metadata(project)
            
            dashboard_project = DashboardProjectResponse(
                id=project.id,
                title=project.title,
                target_repository=project.target_repository,
                architecture_topic=project.architecture_topic,
                concept_description=project.concept_description,
                status=project.status,
                created_at=project.created_at,
                updated_at=project.updated_at,
                total_tasks=project.total_tasks,
                completed_tasks=project.completed_tasks,
                completion_percentage=project.completion_percentage,
                current_task_id=project.current_task_id,
                implementation_language=project.implementation_language,
                preferred_frameworks=project.preferred_frameworks,
                **metadata
            )
            dashboard_projects.append(dashboard_project)
        
        # Calculate statistics from all user projects (not just filtered ones)
        stats = _calculate_dashboard_stats(all_projects)
        
        # Pagination metadata
        has_next_page = end_idx < total_count
        has_prev_page = page > 1
        
        return DashboardResponse(
            projects=dashboard_projects,
            stats=stats,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next_page=has_next_page,
            has_prev_page=has_prev_page
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard: {str(e)}"
        )


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics only (without project list).
    
    Useful for dashboard widgets or when only statistics are needed.
    """
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        
        # Get all user projects
        all_projects = project_repo.get_by_user_id(current_user.id, limit=10000)
        
        # Calculate and return statistics
        return _calculate_dashboard_stats(all_projects)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard stats: {str(e)}"
        )


@router.delete("/projects/{project_id}")
async def delete_project_from_dashboard(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a project from the dashboard with proper authorization.
    
    This endpoint provides the same functionality as the projects router
    but is included here for dashboard-specific operations.
    """
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        
        # Check if project exists
        existing_project = project_repo.get_by_id(project_id)
        if not existing_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Ensure user can only delete their own projects
        if existing_project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only delete your own projects"
            )
        
        # Delete project (cascade will handle related data)
        success = project_repo.delete(project_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete project"
            )
        
        return {"message": "Project deleted successfully", "project_id": project_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )


@router.get("/recent-activity")
async def get_recent_activity(
    current_user: User = Depends(get_current_active_user),
    days: int = Query(7, ge=1, le=30, description="Number of days to look back"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of activities"),
    db: Session = Depends(get_db)
):
    """
    Get recent project activity for the dashboard.
    
    Returns projects that have been updated within the specified number of days.
    """
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        
        # Get all user projects
        all_projects = project_repo.get_by_user_id(current_user.id, limit=10000)
        
        # Filter for recent activity
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_projects = [
            p for p in all_projects 
            if p.updated_at >= cutoff_date
        ]
        
        # Sort by most recent first and limit
        recent_projects.sort(key=lambda p: p.updated_at, reverse=True)
        recent_projects = recent_projects[:limit]
        
        # Convert to response format
        activities = []
        for project in recent_projects:
            metadata = _calculate_dashboard_metadata(project)
            activity = {
                "project_id": project.id,
                "title": project.title,
                "status": project.status,
                "updated_at": project.updated_at,
                "days_since_updated": metadata["days_since_updated"],
                "completion_percentage": project.completion_percentage,
                "architecture_topic": project.architecture_topic
            }
            activities.append(activity)
        
        return {
            "activities": activities,
            "total_count": len(activities),
            "days_looked_back": days
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recent activity: {str(e)}"
        )