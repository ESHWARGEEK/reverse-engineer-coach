"""
Repository Discovery API Endpoints
Provides endpoints for intelligent repository discovery based on learning concepts.
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models import User
from app.services.github_search_service import GitHubSearchService, SearchFilters, RepositorySuggestion
from app.services.repository_analyzer import RepositoryAnalyzer
from app.services.auth_service import AuthService
from app.cache import cache
from app.decorators.validation_decorators import (
    validate_repository_discovery,
    validate_json_body,
    validate_query_params,
    rate_limit,
    sanitize_output
)
from app.schemas.validation_schemas import ValidationRules

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discover", tags=["discovery"])
security = HTTPBearer()


class ConceptSearchRequest(BaseModel):
    """Request model for concept-based repository search"""
    concept: str = Field(..., min_length=3, max_length=500, description="Learning concept description")
    max_results: int = Field(default=10, ge=1, le=50, description="Maximum number of results")
    
    # Search filters
    min_stars: Optional[int] = Field(default=10, ge=0, description="Minimum star count")
    max_stars: Optional[int] = Field(default=None, ge=0, description="Maximum star count")
    language: Optional[str] = Field(default=None, description="Programming language filter")
    topics: Optional[List[str]] = Field(default=None, description="GitHub topics filter")
    created_after: Optional[str] = Field(default=None, description="Created after date (ISO format)")
    updated_after: Optional[str] = Field(default=None, description="Updated after date (ISO format)")
    
    @validator('concept')
    def validate_concept(cls, v):
        if not v.strip():
            raise ValueError('Concept cannot be empty')
        return v.strip()
    
    @validator('max_stars')
    def validate_star_range(cls, v, values):
        if v is not None and 'min_stars' in values and values['min_stars'] is not None:
            if v < values['min_stars']:
                raise ValueError('max_stars must be greater than min_stars')
        return v


class RepositoryDiscoveryResponse(BaseModel):
    """Response model for repository discovery"""
    concept: str
    total_results: int
    repositories: List[Dict[str, Any]]
    search_metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True


class RepositoryAnalysisRequest(BaseModel):
    """Request model for repository analysis"""
    repository_url: str = Field(..., description="GitHub repository URL")
    learning_concept: Optional[str] = Field(default=None, description="Learning concept for context")
    
    @validator('repository_url')
    def validate_repository_url(cls, v):
        if not v.strip():
            raise ValueError('Repository URL cannot be empty')
        
        # Basic GitHub URL validation
        if 'github.com' not in v.lower():
            raise ValueError('Must be a GitHub repository URL')
        
        return v.strip()


class RepositoryAnalysisResponse(BaseModel):
    """Response model for repository analysis"""
    repository_url: str
    analysis: Dict[str, Any]
    
    class Config:
        from_attributes = True


class LanguageRepositoriesRequest(BaseModel):
    """Request model for language-specific repository search"""
    language: str = Field(..., min_length=1, max_length=50, description="Programming language")
    concepts: List[str] = Field(..., min_items=1, max_items=10, description="Concept keywords")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum number of results")


@router.post("/repositories", response_model=RepositoryDiscoveryResponse)
@validate_repository_discovery
@rate_limit(max_requests=20, window_seconds=60)  # 20 discovery requests per minute
@sanitize_output(remove_sensitive=True)
async def discover_repositories(
    request: ConceptSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Discover repositories based on learning concept with advanced filtering.
    
    This endpoint uses GitHub's search API combined with AI-powered analysis
    to find the most relevant repositories for learning specific concepts.
    """
    try:
        logger.info(f"Repository discovery request from user {current_user.id} for concept: {request.concept}")
        
        # Get user's GitHub token from credentials
        auth_service = AuthService()
        github_token, _ = auth_service.get_user_credentials(current_user, db)
        
        if not github_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub token not found. Please update your API credentials in your profile."
            )
        
        # Create search filters
        filters = SearchFilters(
            min_stars=request.min_stars or 10,
            max_stars=request.max_stars,
            language=request.language,
            topics=request.topics or [],
            created_after=request.created_after,
            updated_after=request.updated_after,
            has_readme=True,
            has_license=True,
            is_fork=False,
            is_archived=False
        )
        
        # Perform repository discovery
        async with GitHubSearchService(github_token) as search_service:
            suggestions = await search_service.discover_repositories(
                learning_concept=request.concept,
                filters=filters,
                max_results=request.max_results
            )
        
        # Convert suggestions to response format
        repositories = [suggestion.to_dict() for suggestion in suggestions]
        
        # Create search metadata
        search_metadata = {
            'filters_applied': {
                'min_stars': filters.min_stars,
                'max_stars': filters.max_stars,
                'language': filters.language,
                'topics': filters.topics,
                'has_readme': filters.has_readme,
                'has_license': filters.has_license
            },
            'search_timestamp': suggestions[0].quality.to_dict() if suggestions else None,
            'total_github_results': len(repositories)
        }
        
        logger.info(f"Found {len(repositories)} repositories for concept: {request.concept}")
        
        return RepositoryDiscoveryResponse(
            concept=request.concept,
            total_results=len(repositories),
            repositories=repositories,
            search_metadata=search_metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Repository discovery failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Repository discovery failed: {str(e)}"
        )


@router.post("/analyze", response_model=RepositoryAnalysisResponse)
@validate_json_body(max_size=2000, required_fields=["repository_url"])
@rate_limit(max_requests=10, window_seconds=60)  # 10 analysis requests per minute
@sanitize_output(remove_sensitive=True)
async def analyze_repository(
    request: RepositoryAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze a specific repository for educational value and architectural complexity.
    
    This endpoint provides detailed analysis of a repository including:
    - Architectural patterns identification
    - Educational value assessment
    - Complexity analysis
    - Learning recommendations
    """
    try:
        logger.info(f"Repository analysis request from user {current_user.id} for: {request.repository_url}")
        
        # Get user's credentials
        auth_service = AuthService()
        github_token, ai_api_key = auth_service.get_user_credentials(current_user, db)
        
        if not github_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub token not found. Please update your API credentials in your profile."
            )
        
        # Perform repository analysis
        async with RepositoryAnalyzer(
            github_token=github_token,
            ai_api_key=ai_api_key,
            ai_provider=current_user.preferred_ai_provider or "openai"
        ) as analyzer:
            analysis = await analyzer.analyze_repository(
                repository_url=request.repository_url,
                learning_concept=request.learning_concept
            )
        
        logger.info(f"Completed analysis for repository: {request.repository_url}")
        
        return RepositoryAnalysisResponse(
            repository_url=request.repository_url,
            analysis=analysis.to_dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Repository analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Repository analysis failed: {str(e)}"
        )


@router.post("/by-language", response_model=RepositoryDiscoveryResponse)
async def discover_repositories_by_language(
    request: LanguageRepositoriesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Discover repositories filtered by programming language and concept keywords.
    
    This endpoint is optimized for finding repositories in a specific programming
    language that demonstrate particular concepts or patterns.
    """
    try:
        logger.info(f"Language-specific discovery request from user {current_user.id} for {request.language}")
        
        # Get user's GitHub token
        auth_service = AuthService()
        github_token, _ = auth_service.get_user_credentials(current_user, db)
        
        if not github_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub token not found. Please update your API credentials in your profile."
            )
        
        # Perform language-specific search
        async with GitHubSearchService(github_token) as search_service:
            suggestions = await search_service.get_repository_suggestions_by_language(
                language=request.language,
                concept_keywords=request.concepts,
                max_results=request.max_results
            )
        
        # Convert to response format
        repositories = [suggestion.to_dict() for suggestion in suggestions]
        
        search_metadata = {
            'language_filter': request.language,
            'concept_keywords': request.concepts,
            'search_timestamp': suggestions[0].quality.to_dict() if suggestions else None
        }
        
        logger.info(f"Found {len(repositories)} {request.language} repositories")
        
        return RepositoryDiscoveryResponse(
            concept=' '.join(request.concepts),
            total_results=len(repositories),
            repositories=repositories,
            search_metadata=search_metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Language-specific discovery failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Language-specific discovery failed: {str(e)}"
        )


@router.get("/suggestions")
@validate_query_params(
    allowed_params=["query", "limit"],
    required_params=["query"],
    param_validators={
        "query": lambda x: len(x.strip()) >= 1 and len(x) <= 100,
        "limit": lambda x: 1 <= int(x) <= 50
    }
)
@rate_limit(max_requests=50, window_seconds=60)  # 50 suggestion requests per minute
async def get_concept_suggestions(
    query: str = Query(..., min_length=1, max_length=100, description="Partial concept query"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum number of suggestions")
):
    """
    Get concept suggestions for autocomplete functionality.
    
    This endpoint provides popular programming concepts and architectural patterns
    that can be used for repository discovery.
    """
    try:
        # Define popular concepts and patterns
        concept_suggestions = [
            # Architectural patterns
            "microservices architecture",
            "mvc pattern",
            "mvp pattern",
            "clean architecture",
            "hexagonal architecture",
            "layered architecture",
            "domain driven design",
            "cqrs pattern",
            "event sourcing",
            
            # Design patterns
            "factory pattern",
            "singleton pattern",
            "observer pattern",
            "strategy pattern",
            "adapter pattern",
            "decorator pattern",
            "facade pattern",
            "repository pattern",
            
            # Web development
            "rest api",
            "graphql api",
            "websocket implementation",
            "authentication system",
            "authorization patterns",
            "oauth implementation",
            "jwt authentication",
            
            # Framework-specific
            "spring boot application",
            "django web application",
            "flask microservice",
            "express.js server",
            "react application",
            "vue.js project",
            "angular application",
            
            # DevOps and deployment
            "docker containerization",
            "kubernetes deployment",
            "ci/cd pipeline",
            "monitoring system",
            "logging framework",
            
            # Data and persistence
            "database design",
            "orm implementation",
            "caching strategies",
            "message queues",
            "event streaming",
            
            # Testing
            "test driven development",
            "behavior driven development",
            "unit testing",
            "integration testing",
            "end-to-end testing"
        ]
        
        # Filter suggestions based on query
        query_lower = query.lower()
        filtered_suggestions = [
            concept for concept in concept_suggestions
            if query_lower in concept.lower()
        ]
        
        # Limit results
        limited_suggestions = filtered_suggestions[:limit]
        
        return {
            "query": query,
            "suggestions": limited_suggestions,
            "total_matches": len(filtered_suggestions)
        }
        
    except Exception as e:
        logger.error(f"Failed to get concept suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get concept suggestions"
        )


@router.get("/popular-concepts")
async def get_popular_concepts():
    """
    Get list of popular learning concepts for discovery.
    
    This endpoint returns trending and popular concepts that users
    commonly search for when learning software architecture.
    """
    try:
        popular_concepts = {
            "architectural_patterns": [
                "microservices",
                "clean architecture",
                "hexagonal architecture",
                "mvc pattern",
                "domain driven design"
            ],
            "web_development": [
                "rest api",
                "graphql",
                "authentication",
                "websockets",
                "oauth"
            ],
            "design_patterns": [
                "factory pattern",
                "observer pattern",
                "strategy pattern",
                "repository pattern",
                "singleton pattern"
            ],
            "frameworks": [
                "spring boot",
                "django",
                "react",
                "express.js",
                "flask"
            ],
            "devops": [
                "docker",
                "kubernetes",
                "ci/cd",
                "monitoring",
                "microservices deployment"
            ]
        }
        
        return {
            "categories": popular_concepts,
            "trending": [
                "microservices architecture",
                "clean architecture",
                "docker containerization",
                "react hooks",
                "graphql api"
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get popular concepts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get popular concepts"
        )


@router.post("/refresh-cache")
async def refresh_discovery_cache(
    concept: str = Query(..., min_length=3, max_length=500, description="Learning concept to refresh"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Refresh cached repository discovery results for a specific concept.
    
    This endpoint allows users to get fresh repository suggestions by
    invalidating cached results and performing a new search.
    """
    try:
        logger.info(f"Cache refresh request from user {current_user.id} for concept: {concept}")
        
        # Get user's GitHub token
        auth_service = AuthService()
        github_token, _ = auth_service.get_user_credentials(current_user, db)
        
        if not github_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub token not found. Please update your API credentials in your profile."
            )
        
        # Refresh cache
        async with GitHubSearchService(github_token) as search_service:
            success = await search_service.refresh_repository_cache(concept)
        
        if success:
            return {
                "message": f"Cache refreshed successfully for concept: {concept}",
                "concept": concept,
                "refreshed_at": "2024-01-01T00:00:00Z"  # Would be actual timestamp
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to refresh cache"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cache refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache refresh failed: {str(e)}"
        )


@router.get("/stats")
async def get_discovery_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get repository discovery statistics and cache information.
    
    This endpoint provides insights into discovery performance,
    cache hit rates, and popular search concepts.
    """
    try:
        # Get cache statistics
        cache_stats = await cache.get_stats()
        
        # Mock discovery statistics (would be real data in production)
        discovery_stats = {
            "total_searches_today": 42,
            "unique_concepts_searched": 15,
            "average_results_per_search": 8.5,
            "most_popular_languages": ["Python", "JavaScript", "Java", "Go", "TypeScript"],
            "most_searched_concepts": [
                "microservices architecture",
                "clean architecture",
                "rest api",
                "docker containerization",
                "react patterns"
            ],
            "cache_performance": {
                "hit_rate": cache_stats.get("hit_rate", 0.0),
                "total_hits": cache_stats.get("hits", 0),
                "total_misses": cache_stats.get("misses", 0)
            }
        }
        
        return discovery_stats
        
    except Exception as e:
        logger.error(f"Failed to get discovery stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get discovery statistics"
        )