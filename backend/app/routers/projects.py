"""
Project management API endpoints with enhanced authentication
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from app.database import get_db
from app.repositories import RepositoryFactory
from app.models import LearningProject, User
from app.mcp_client import MCPClient
from app.spec_generator import SpecificationGenerator
from app.language_support import LanguageSupport, ProgrammingLanguage
from app.middleware.auth_middleware import get_current_active_user

router = APIRouter()

# Pydantic models for request/response
class ProjectCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Project title")
    target_repository: str = Field(..., description="GitHub repository URL")
    architecture_topic: str = Field(..., min_length=1, max_length=255, description="Architecture topic to focus on")
    implementation_language: Optional[str] = Field("python", description="Target implementation language")
    preferred_frameworks: Optional[List[str]] = Field(None, description="Preferred frameworks for implementation")
    language_specific_config: Optional[Dict[str, Any]] = Field(None, description="Language-specific configuration")
    
    # Enhanced fields for discovery integration
    concept_description: Optional[str] = Field(None, description="Learning concept description for discovery context")
    discovery_metadata: Optional[Dict[str, Any]] = Field(None, description="Repository discovery metadata")


class ProjectCreateFromDiscoveryRequest(BaseModel):
    """Request model for creating project from discovered repository"""
    title: str = Field(..., min_length=1, max_length=255, description="Project title")
    repository_suggestion: Dict[str, Any] = Field(..., description="Repository suggestion from discovery")
    learning_concept: str = Field(..., min_length=3, max_length=500, description="Original learning concept")
    implementation_language: Optional[str] = Field("python", description="Target implementation language")
    preferred_frameworks: Optional[List[str]] = Field(None, description="Preferred frameworks for implementation")

class ProjectUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(None, description="Project status")
    current_task_id: Optional[str] = Field(None, description="Current task ID")
    implementation_language: Optional[str] = Field(None, description="Target implementation language")
    preferred_frameworks: Optional[List[str]] = Field(None, description="Preferred frameworks")

class ProjectResponse(BaseModel):
    id: str
    user_id: str
    title: str
    target_repository: str
    architecture_topic: str
    status: str
    created_at: datetime
    updated_at: datetime
    total_tasks: int
    completed_tasks: int
    current_task_id: Optional[str]
    completion_percentage: float
    implementation_language: Optional[str]
    preferred_frameworks: Optional[List[str]]
    
    # Enhanced fields for discovery integration
    concept_description: Optional[str]
    discovery_metadata: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True

class ProjectProgressResponse(BaseModel):
    project_id: str
    total_tasks: int
    completed_tasks: int
    completion_percentage: float
    current_task_id: Optional[str]
    status: str

class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total_count: int
    page: int
    page_size: int

# Background task for repository analysis
async def analyze_repository_background(
    project_id: str, 
    repository_url: str, 
    architecture_topic: str,
    implementation_language: str,
    preferred_frameworks: Optional[List[str]],
    user_id: str,
    db: Session
):
    """Background task to analyze repository and generate learning spec with user-specific credentials"""
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        
        # Update project status to analyzing
        project_repo.update(project_id, status="analyzing")
        
        # Get user's credentials for API access
        from app.services.auth_service import AuthService
        from app.models import User
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            project_repo.update(project_id, status="failed")
            return
        
        auth_service = AuthService()
        github_token, ai_api_key = auth_service.get_user_credentials(user, db)
        
        if not github_token:
            project_repo.update(project_id, status="failed")
            logger.error(f"No GitHub token found for user {user_id}")
            return
        
        # Initialize MCP client with user's credentials
        mcp_client = MCPClient(github_token=github_token)
        spec_generator = SpecificationGenerator(
            github_token=github_token,
            ai_api_key=ai_api_key,
            ai_provider=user.preferred_ai_provider or "openai"
        )
        
        # Convert language string to enum
        try:
            target_language = ProgrammingLanguage(implementation_language.lower())
        except ValueError:
            target_language = ProgrammingLanguage.PYTHON  # Default fallback
        
        # Analyze repository and generate spec with language support
        analysis_result = await spec_generator.generate_learning_spec_with_language(
            repository_url, 
            architecture_topic,
            target_language,
            preferred_frameworks
        )
        
        if analysis_result:
            # Update project with analysis results
            project_repo.update(
                project_id, 
                status="ready",
                total_tasks=len(analysis_result.get("tasks", [])),
                completion_percentage=0.0
            )
        else:
            # Mark project as failed
            project_repo.update(project_id, status="failed")
            
    except Exception as e:
        # Mark project as failed on error
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        project_repo.update(project_id, status="failed")
        logger.error(f"Repository analysis failed for project {project_id}: {str(e)}")


async def analyze_discovered_repository_background(
    project_id: str,
    repository_suggestion: Dict[str, Any],
    learning_concept: str,
    implementation_language: str,
    preferred_frameworks: Optional[List[str]],
    user_id: str,
    db: Session
):
    """Background task to analyze discovered repository with enhanced context"""
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        
        # Update project status to analyzing
        project_repo.update(project_id, status="analyzing")
        
        # Get user's credentials
        from app.services.auth_service import AuthService
        from app.models import User
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            project_repo.update(project_id, status="failed")
            return
        
        auth_service = AuthService()
        github_token, ai_api_key = auth_service.get_user_credentials(user, db)
        
        if not github_token:
            project_repo.update(project_id, status="failed")
            logger.error(f"No GitHub token found for user {user_id}")
            return
        
        # Use repository analyzer for enhanced analysis
        from app.services.repository_analyzer import RepositoryAnalyzer
        
        async with RepositoryAnalyzer(
            github_token=github_token,
            ai_api_key=ai_api_key,
            ai_provider=user.preferred_ai_provider or "openai"
        ) as analyzer:
            # Perform detailed repository analysis
            repository_url = repository_suggestion['repository_url']
            analysis = await analyzer.analyze_repository(repository_url, learning_concept)
            
            # Initialize enhanced spec generator
            spec_generator = SpecificationGenerator(
                github_token=github_token,
                ai_api_key=ai_api_key,
                ai_provider=user.preferred_ai_provider or "openai"
            )
            
            # Convert language string to enum
            try:
                target_language = ProgrammingLanguage(implementation_language.lower())
            except ValueError:
                target_language = ProgrammingLanguage.PYTHON
            
            # Generate learning spec with enhanced context from analysis
            analysis_result = await spec_generator.generate_enhanced_learning_spec(
                repository_url=repository_url,
                architecture_topic=learning_concept,
                target_language=target_language,
                preferred_frameworks=preferred_frameworks,
                repository_analysis=analysis,
                repository_suggestion=repository_suggestion
            )
            
            if analysis_result:
                # Update project with enhanced analysis results
                project_repo.update(
                    project_id,
                    status="ready",
                    total_tasks=len(analysis_result.get("tasks", [])),
                    completion_percentage=0.0,
                    discovery_metadata={
                        'repository_analysis': analysis.to_dict(),
                        'repository_suggestion': repository_suggestion,
                        'learning_concept': learning_concept,
                        'analysis_timestamp': analysis.analysis_timestamp
                    }
                )
            else:
                project_repo.update(project_id, status="failed")
                
    except Exception as e:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        project_repo.update(project_id, status="failed")
        logger.error(f"Enhanced repository analysis failed for project {project_id}: {str(e)}")

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new learning project with repository analysis trigger
    
    This endpoint creates a project and triggers background repository analysis
    to generate the learning specification and tasks.
    """
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        
        # Create project with current user and language settings
        project = project_repo.create(
            user_id=current_user.id,
            title=request.title,
            target_repository=request.target_repository,
            architecture_topic=request.architecture_topic,
            status="created",
            implementation_language=request.implementation_language or current_user.preferred_language,
            preferred_frameworks=request.preferred_frameworks or current_user.preferred_frameworks,
            language_specific_config=request.language_specific_config,
            concept_description=request.concept_description,
            discovery_metadata=request.discovery_metadata
        )
        
        # Trigger background repository analysis with language support
        background_tasks.add_task(
            analyze_repository_background,
            project.id,
            request.target_repository,
            request.architecture_topic,
            request.implementation_language or "python",
            request.preferred_frameworks,
            current_user.id,  # Pass user ID for credential access
            db
        )
        
        return ProjectResponse.model_validate(project)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


@router.post("/from-discovery", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project_from_discovery(
    request: ProjectCreateFromDiscoveryRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new learning project from a discovered repository suggestion.
    
    This endpoint creates a project using enhanced repository analysis from the
    discovery system, providing better context and learning recommendations.
    """
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        
        # Extract repository URL from suggestion
        repository_url = request.repository_suggestion.get('repository_url')
        if not repository_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Repository URL not found in suggestion"
            )
        
        # Create project with discovery metadata
        project = project_repo.create(
            user_id=current_user.id,
            title=request.title,
            target_repository=repository_url,
            architecture_topic=request.learning_concept,
            status="created",
            implementation_language=request.implementation_language or current_user.preferred_language,
            preferred_frameworks=request.preferred_frameworks or current_user.preferred_frameworks,
            concept_description=request.learning_concept,
            discovery_metadata={
                'repository_suggestion': request.repository_suggestion,
                'learning_concept': request.learning_concept,
                'discovery_timestamp': datetime.utcnow().isoformat()
            }
        )
        
        # Trigger enhanced background repository analysis
        background_tasks.add_task(
            analyze_discovered_repository_background,
            project.id,
            request.repository_suggestion,
            request.learning_concept,
            request.implementation_language or "python",
            request.preferred_frameworks,
            current_user.id,
            db
        )
        
        return ProjectResponse.model_validate(project)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project from discovery: {str(e)}"
        )

@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    current_user: User = Depends(get_current_active_user),
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    """
    List projects for the current authenticated user with optional filtering and pagination
    """
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        
        offset = (page - 1) * page_size
        
        # Always filter by current user
        if status_filter:
            projects = project_repo.get_by_user_and_status(current_user.id, status_filter)
        else:
            projects = project_repo.get_by_user_id(current_user.id, limit=page_size, offset=offset)
        
        # Convert to response models
        project_responses = [ProjectResponse.model_validate(p) for p in projects]
        
        return ProjectListResponse(
            projects=project_responses,
            total_count=len(projects),
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}"
        )

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str, 
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific project by ID (only if owned by current user)
    """
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        
        project = project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Ensure user can only access their own projects
        if project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access your own projects"
            )
        
        return ProjectResponse.model_validate(project)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project: {str(e)}"
        )

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    request: ProjectUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update a project's details (only if owned by current user)
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
        
        # Ensure user can only update their own projects
        if existing_project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only update your own projects"
            )
        
        # Update only provided fields
        update_data = {k: v for k, v in request.model_dump().items() if v is not None}
        
        updated_project = project_repo.update(project_id, **update_data)
        
        return ProjectResponse.model_validate(updated_project)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str, 
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a project and all associated data (only if owned by current user)
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
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )

@router.get("/{project_id}/progress", response_model=ProjectProgressResponse)
async def get_project_progress(
    project_id: str, 
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed progress information for a project (only if owned by current user)
    """
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        
        project = project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Ensure user can only access their own projects
        if project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access your own projects"
            )
        
        return ProjectProgressResponse(
            project_id=project.id,
            total_tasks=project.total_tasks,
            completed_tasks=project.completed_tasks,
            completion_percentage=project.completion_percentage,
            current_task_id=project.current_task_id,
            status=project.status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project progress: {str(e)}"
        )

class ProjectProgressUpdate(BaseModel):
    completed_tasks: int = Field(..., ge=0, description="Number of completed tasks")
    current_task_id: Optional[str] = Field(None, description="Current task ID")

@router.post("/{project_id}/progress", response_model=ProjectProgressResponse)
async def update_project_progress(
    project_id: str,
    progress_update: ProjectProgressUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update project progress tracking (only if owned by current user)
    """
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        
        project = project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Ensure user can only update their own projects
        if project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only update your own projects"
            )
        
        # Update progress
        updated_project = project_repo.update_progress(
            project_id, progress_update.completed_tasks, project.total_tasks
        )
        
        # Update current task if provided
        if progress_update.current_task_id is not None:
            updated_project = project_repo.update(project_id, current_task_id=progress_update.current_task_id)
        
        return ProjectProgressResponse(
            project_id=updated_project.id,
            total_tasks=updated_project.total_tasks,
            completed_tasks=updated_project.completed_tasks,
            completion_percentage=updated_project.completion_percentage,
            current_task_id=updated_project.current_task_id,
            status=updated_project.status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project progress: {str(e)}"
        )

@router.get("/user/{user_id}", response_model=ProjectListResponse)
async def get_user_projects(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get all projects for a specific user (only accessible by the user themselves)
    """
    # Ensure users can only access their own projects
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only access your own projects"
        )
    
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        
        offset = (page - 1) * page_size
        
        if status_filter:
            projects = project_repo.get_by_user_and_status(user_id, status_filter)
        else:
            projects = project_repo.get_by_user_id(user_id, limit=page_size, offset=offset)
        
        project_responses = [ProjectResponse.model_validate(p) for p in projects]
        
        return ProjectListResponse(
            projects=project_responses,
            total_count=len(projects),
            page=page,
            page_size=page_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user projects: {str(e)}"
        )

@router.get("/search/{topic}", response_model=ProjectListResponse)
async def search_projects_by_topic(
    topic: str,
    current_user: User = Depends(get_current_active_user),
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    """
    Search projects by architecture topic (only user's own projects)
    """
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        
        # Get user's projects first, then filter by topic
        user_projects = project_repo.get_by_user_id(current_user.id, limit=1000)  # Get all user projects
        
        # Filter by topic
        filtered_projects = [
            p for p in user_projects 
            if topic.lower() in p.architecture_topic.lower()
        ]
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_projects = filtered_projects[start_idx:end_idx]
        
        project_responses = [ProjectResponse.model_validate(p) for p in paginated_projects]
        
        return ProjectListResponse(
            projects=project_responses,
            total_count=len(filtered_projects),
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search projects: {str(e)}"
        )


class LanguageInfo(BaseModel):
    """Language information response model"""
    language: str
    display_name: str
    frameworks: List[str]
    syntax_style: str
    package_manager: str
    test_framework: str
    conventions: Dict[str, str]


class SupportedLanguagesResponse(BaseModel):
    """Response model for supported languages"""
    languages: List[LanguageInfo]
    default_language: str


@router.get("/languages/supported", response_model=SupportedLanguagesResponse)
async def get_supported_languages():
    """
    Get list of supported programming languages for implementation
    """
    try:
        supported_languages = LanguageSupport.get_supported_languages()
        language_infos = []
        
        for lang in supported_languages:
            config = LanguageSupport.get_language_config(lang)
            language_info = LanguageInfo(
                language=lang.value,
                display_name=lang.value.title(),
                frameworks=[f.value for f in config.frameworks],
                syntax_style=config.syntax_style,
                package_manager=config.package_manager,
                test_framework=config.test_framework,
                conventions=config.conventions
            )
            language_infos.append(language_info)
        
        return SupportedLanguagesResponse(
            languages=language_infos,
            default_language="python"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get supported languages: {str(e)}"
        )


class CrossLanguageTranslationRequest(BaseModel):
    """Request model for cross-language translation"""
    source_code: str = Field(..., description="Source code to translate")
    source_language: str = Field(..., description="Source programming language")
    target_language: str = Field(..., description="Target programming language")
    patterns: List[str] = Field(default_factory=list, description="Architectural patterns to preserve")


class CrossLanguageTranslationResponse(BaseModel):
    """Response model for cross-language translation"""
    success: bool
    translated_code: Optional[str]
    source_language: str
    target_language: str
    preserved_patterns: List[str]
    translation_notes: List[str]
    tokens_used: Optional[int]
    error: Optional[str]


@router.post("/languages/translate", response_model=CrossLanguageTranslationResponse)
async def translate_code_cross_language(request: CrossLanguageTranslationRequest):
    """
    Translate code from one programming language to another while preserving architectural patterns
    """
    try:
        from app.language_support import CrossLanguageTranslator, ArchitecturalPattern
        from app.llm_provider import LLMProviderFactory
        
        # Convert language strings to enums
        try:
            source_lang = ProgrammingLanguage(request.source_language.lower())
            target_lang = ProgrammingLanguage(request.target_language.lower())
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported language: {str(e)}"
            )
        
        # Convert pattern strings to enums
        patterns = []
        for pattern_str in request.patterns:
            try:
                # Find matching pattern by value
                for pattern in ArchitecturalPattern:
                    if pattern.value.lower() == pattern_str.lower():
                        patterns.append(pattern)
                        break
            except:
                continue  # Skip unknown patterns
        
        # Initialize translator
        llm_provider = LLMProviderFactory.get_default_provider()
        translator = CrossLanguageTranslator(llm_provider)
        
        # Perform translation
        result = await translator.translate_concepts(
            request.source_code,
            source_lang,
            target_lang,
            patterns
        )
        
        return CrossLanguageTranslationResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Translation failed: {str(e)}"
        )