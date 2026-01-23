"""
GitHub integration API endpoints for enhanced repository management with authentication
"""

from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from app.database import get_db
from app.github_client import GitHubClient, GitHubAPIError, RepositoryChange, CommitInfo
from app.models import User
from app.middleware.auth_middleware import get_current_active_user

router = APIRouter()

# Pydantic models for request/response
class RepositoryChangeResponse(BaseModel):
    """Response model for repository changes"""
    change_type: str
    old_value: Optional[str]
    new_value: Optional[str]
    detected_at: str
    description: str

class CommitInfoResponse(BaseModel):
    """Response model for commit information"""
    sha: str
    message: str
    author: str
    author_email: str
    date: str
    url: str

class ActivitySummaryResponse(BaseModel):
    """Response model for repository activity summary"""
    period_days: int
    commit_count: int
    unique_contributors: int
    issues_count: int
    pull_requests_count: int
    total_activity_items: int
    most_recent_commit: Optional[Dict[str, Any]]
    activity_level: str
    error: Optional[str] = None

class StableLinkResponse(BaseModel):
    """Response model for stable file links"""
    stable_url: str
    commit_sha: Optional[str]
    file_path: str
    line_number: Optional[int]

class RefreshCacheResponse(BaseModel):
    """Response model for cache refresh operations"""
    success: bool
    message: str
    refreshed_at: str

class FileValidationResponse(BaseModel):
    """Response model for file validation"""
    exists: bool
    file_path: str
    repository_url: str
    ref: Optional[str]


class RepositoryChangeRequest(BaseModel):
    repository_url: str = Field(..., description="GitHub repository URL")
    last_known_commit: Optional[str] = Field(None, description="Last known commit SHA")

@router.post("/repositories/detect-changes", response_model=List[RepositoryChangeResponse])
async def detect_repository_changes(
    request: RepositoryChangeRequest
):
    """
    Detect changes in a repository since the last known state.
    
    This endpoint helps track repository updates for learning projects,
    allowing the system to refresh content when the source repository changes.
    """
    try:
        async with GitHubClient() as github_client:
            changes = await github_client.detect_repository_changes(
                request.repository_url, request.last_known_commit
            )
            
            return [
                RepositoryChangeResponse(
                    change_type=change.change_type,
                    old_value=change.old_value,
                    new_value=change.new_value,
                    detected_at=change.detected_at,
                    description=change.description
                )
                for change in changes
            ]
            
    except GitHubAPIError as e:
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GitHub API error: {e.message}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid repository URL: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect repository changes: {str(e)}"
        )


class RefreshCacheRequest(BaseModel):
    repository_url: str = Field(..., description="GitHub repository URL")

@router.post("/repositories/refresh-cache", response_model=RefreshCacheResponse)
async def refresh_repository_cache(
    request: RefreshCacheRequest
):
    """
    Refresh cached repository data by invalidating cache and fetching fresh data.
    
    Use this endpoint when you need to ensure you have the latest repository
    information, especially after detecting changes.
    """
    try:
        async with GitHubClient() as github_client:
            success = await github_client.refresh_repository_cache(request.repository_url)
            
            return RefreshCacheResponse(
                success=success,
                message="Repository cache refreshed successfully" if success else "Failed to refresh cache",
                refreshed_at=datetime.now().isoformat()
            )
            
    except GitHubAPIError as e:
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GitHub API error: {e.message}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid repository URL: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh repository cache: {str(e)}"
        )


@router.get("/repositories/stable-link", response_model=StableLinkResponse)
async def get_stable_file_link(
    repository_url: str = Query(..., description="GitHub repository URL"),
    file_path: str = Query(..., description="Path to the file"),
    line_number: Optional[int] = Query(None, description="Optional line number")
):
    """
    Generate a stable link to a file using the latest commit SHA.
    
    Stable links use commit SHAs instead of branch names, ensuring the link
    always points to the same version of the file even if the repository changes.
    """
    try:
        async with GitHubClient() as github_client:
            stable_url = await github_client.get_stable_file_link(
                repository_url, file_path, line_number
            )
            
            # Extract commit SHA from the URL if present
            commit_sha = None
            if "/blob/" in stable_url:
                parts = stable_url.split("/blob/")
                if len(parts) > 1:
                    commit_part = parts[1].split("/")[0]
                    if len(commit_part) == 40:  # SHA length
                        commit_sha = commit_part
            
            return StableLinkResponse(
                stable_url=stable_url,
                commit_sha=commit_sha,
                file_path=file_path,
                line_number=line_number
            )
            
    except GitHubAPIError as e:
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GitHub API error: {e.message}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid repository URL: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate stable link: {str(e)}"
        )


@router.get("/repositories/commit-info", response_model=CommitInfoResponse)
async def get_commit_info(
    repository_url: str = Query(..., description="GitHub repository URL"),
    commit_sha: str = Query(..., description="Commit SHA")
):
    """
    Get detailed information about a specific commit.
    
    Useful for understanding what changed in a particular commit
    and providing context for learning materials.
    """
    try:
        async with GitHubClient() as github_client:
            commit_info = await github_client.get_commit_info(repository_url, commit_sha)
            
            return CommitInfoResponse(
                sha=commit_info.sha,
                message=commit_info.message,
                author=commit_info.author,
                author_email=commit_info.author_email,
                date=commit_info.date,
                url=commit_info.url
            )
            
    except GitHubAPIError as e:
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GitHub API error: {e.message}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid repository URL or commit SHA: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get commit info: {str(e)}"
        )


@router.get("/repositories/activity-summary", response_model=ActivitySummaryResponse)
async def get_repository_activity_summary(
    repository_url: str = Query(..., description="GitHub repository URL"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze (1-365)")
):
    """
    Get a summary of repository activity over the specified period.
    
    Provides insights into repository health and development activity,
    helping users understand if a repository is actively maintained.
    """
    try:
        async with GitHubClient() as github_client:
            activity_summary = await github_client.get_repository_activity_summary(
                repository_url, days
            )
            
            return ActivitySummaryResponse(**activity_summary)
            
    except GitHubAPIError as e:
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GitHub API error: {e.message}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid repository URL: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get activity summary: {str(e)}"
        )


@router.get("/repositories/validate-file", response_model=FileValidationResponse)
async def validate_file_exists(
    repository_url: str = Query(..., description="GitHub repository URL"),
    file_path: str = Query(..., description="Path to the file"),
    ref: Optional[str] = Query(None, description="Git reference (branch, tag, or commit SHA)")
):
    """
    Validate that a specific file exists in the repository.
    
    Useful for checking if reference snippets and learning materials
    are still available in the target repository.
    """
    try:
        async with GitHubClient() as github_client:
            exists = await github_client.validate_file_exists(
                repository_url, file_path, ref
            )
            
            return FileValidationResponse(
                exists=exists,
                file_path=file_path,
                repository_url=repository_url,
                ref=ref
            )
            
    except GitHubAPIError as e:
        # For validation, we want to return exists=False for 404s
        if e.status_code == 404:
            return FileValidationResponse(
                exists=False,
                file_path=file_path,
                repository_url=repository_url,
                ref=ref
            )
        else:
            raise HTTPException(
                status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"GitHub API error: {e.message}"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid repository URL: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate file: {str(e)}"
        )


@router.get("/repositories/permalink", response_model=Dict[str, str])
async def generate_permalink(
    repository_url: str = Query(..., description="GitHub repository URL"),
    file_path: str = Query(..., description="Path to the file"),
    line_number: Optional[int] = Query(None, description="Optional line number"),
    commit_sha: Optional[str] = Query(None, description="Optional commit SHA for stable linking")
):
    """
    Generate a GitHub permalink for a file or specific line.
    
    If commit_sha is provided, creates a stable link that won't change.
    Otherwise, creates a branch-based link that points to the latest version.
    """
    try:
        async with GitHubClient() as github_client:
            permalink = github_client.get_permalink_url(
                repository_url, file_path, line_number, commit_sha
            )
            
            return {
                "permalink": permalink,
                "file_path": file_path,
                "line_number": str(line_number) if line_number else None,
                "commit_sha": commit_sha,
                "is_stable": commit_sha is not None
            }
            
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid repository URL: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate permalink: {str(e)}"
        )