"""
Enhanced Project Creation Workflow API

Provides endpoints for the AI-powered project creation workflow including:
- Workflow initiation and management
- Real-time progress tracking
- Repository discovery and selection
- Curriculum generation
- Project creation
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db
from ..auth import get_current_user
from ..models import User
from ..services.workflow_orchestration_service import (
    ProjectCreationOrchestrator,
    WorkflowInput,
    WorkflowResult,
    WorkflowProgress,
    WorkflowStatus,
    WorkflowStage
)
from ..services.repository_discovery_agent import (
    RepositoryDiscoveryAgent,
    RepositorySearchCriteria,
    create_repository_discovery_agent
)
from ..services.repository_analysis_agent import RepositoryAnalysisAgent
from ..services.curriculum_generation_agent import CurriculumGenerationAgent
from ..llm_provider import get_llm_provider
from ..github_client import get_github_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/enhanced-workflow", tags=["Enhanced Workflow"])
security = HTTPBearer()

# Pydantic models for API
class SkillAssessmentData(BaseModel):
    experienceLevel: str = Field(..., description="User's experience level")
    currentSkills: List[str] = Field(..., description="Current skills")
    learningGoals: List[str] = Field(..., description="Learning goals")
    timeCommitment: str = Field(..., description="Time commitment")
    learningStyle: str = Field(..., description="Learning style")
    motivation: str = Field(..., description="Learning motivation")

class TechnologyPreference(BaseModel):
    id: str
    name: str
    category: str
    proficiency: str
    isRecommended: Optional[bool] = False

class WorkflowStartRequest(BaseModel):
    skillAssessment: SkillAssessmentData
    technologyPreferences: List[TechnologyPreference]
    manualRepositoryUrl: Optional[str] = None
    customizationOptions: Optional[Dict[str, Any]] = None
    workflowPreferences: Optional[Dict[str, Any]] = None

class WorkflowStatusResponse(BaseModel):
    workflowId: str
    status: str
    currentStage: str
    progressPercentage: float
    currentOperation: str
    estimatedTimeRemaining: Optional[str]
    completedStages: List[str]
    errorMessage: Optional[str]
    detailedProgress: Dict[str, Any]
    startedAt: datetime
    updatedAt: datetime

class RepositoryInfo(BaseModel):
    id: str
    name: str
    fullName: str
    description: str
    url: str
    language: str
    languages: Dict[str, int]
    topics: List[str]
    stars: int
    forks: int
    relevanceScore: float
    finalScore: float
    selectionReasoning: str
    learningPathSuggestions: List[str]

class WorkflowResultResponse(BaseModel):
    workflowId: str
    status: str
    createdProjectId: Optional[str]
    discoveredRepositories: List[RepositoryInfo]
    selectedRepository: Optional[RepositoryInfo]
    executionTime: float
    errorDetails: Optional[Dict[str, Any]]
    createdAt: datetime
    completedAt: Optional[datetime]

# Global orchestrator instance (in production, use dependency injection)
_orchestrator: Optional[ProjectCreationOrchestrator] = None

def get_orchestrator(db: Session = Depends(get_db)) -> ProjectCreationOrchestrator:
    """Get or create workflow orchestrator instance"""
    global _orchestrator
    
    if _orchestrator is None:
        # Create AI agents
        llm_provider = get_llm_provider()
        github_client = get_github_client()
        
        discovery_agent = create_repository_discovery_agent(llm_provider, github_client)
        analysis_agent = RepositoryAnalysisAgent(llm_provider, github_client)
        curriculum_agent = CurriculumGenerationAgent(llm_provider)
        
        _orchestrator = ProjectCreationOrchestrator(
            discovery_agent=discovery_agent,
            analysis_agent=analysis_agent,
            curriculum_agent=curriculum_agent,
            llm_provider=llm_provider,
            github_client=github_client,
            db_session=db
        )
    
    return _orchestrator

# WebSocket connection manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, workflow_id: str):
        await websocket.accept()
        if workflow_id not in self.active_connections:
            self.active_connections[workflow_id] = []
        self.active_connections[workflow_id].append(websocket)

    def disconnect(self, websocket: WebSocket, workflow_id: str):
        if workflow_id in self.active_connections:
            self.active_connections[workflow_id].remove(websocket)
            if not self.active_connections[workflow_id]:
                del self.active_connections[workflow_id]

    async def send_progress_update(self, workflow_id: str, progress: WorkflowProgress):
        if workflow_id in self.active_connections:
            message = {
                "type": "progress_update",
                "data": {
                    "workflowId": progress.workflow_id,
                    "currentStage": progress.current_stage.value,
                    "status": progress.status.value,
                    "progressPercentage": progress.progress_percentage,
                    "currentOperation": progress.current_operation,
                    "estimatedTimeRemaining": progress.estimated_time_remaining,
                    "completedStages": [stage.value for stage in progress.completed_stages],
                    "errorMessage": progress.error_message,
                    "detailedProgress": progress.detailed_progress,
                    "updatedAt": progress.updated_at.isoformat()
                }
            }
            
            disconnected = []
            for connection in self.active_connections[workflow_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
            
            # Remove disconnected connections
            for connection in disconnected:
                self.disconnect(connection, workflow_id)

manager = ConnectionManager()

@router.post("/start", response_model=Dict[str, str])
async def start_workflow(
    request: WorkflowStartRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    orchestrator: ProjectCreationOrchestrator = Depends(get_orchestrator)
):
    """
    Start a new enhanced project creation workflow
    """
    try:
        logger.info(f"Starting enhanced workflow for user {current_user.id}")
        
        # Convert request to workflow input
        workflow_input = WorkflowInput(
            user_id=current_user.id,
            skill_assessment={
                'experienceLevel': request.skillAssessment.experienceLevel,
                'currentSkills': request.skillAssessment.currentSkills,
                'learningGoals': request.skillAssessment.learningGoals,
                'timeCommitment': request.skillAssessment.timeCommitment,
                'learningStyle': request.skillAssessment.learningStyle,
                'motivation': request.skillAssessment.motivation
            },
            technology_preferences=[
                {
                    'id': tech.id,
                    'name': tech.name,
                    'category': tech.category,
                    'proficiency': tech.proficiency,
                    'isRecommended': tech.isRecommended
                }
                for tech in request.technologyPreferences
            ],
            manual_repository_url=request.manualRepositoryUrl,
            customization_options=request.customizationOptions or {},
            workflow_preferences=request.workflowPreferences or {}
        )
        
        # Create progress callback for WebSocket updates
        async def progress_callback(progress: WorkflowProgress):
            await manager.send_progress_update(progress.workflow_id, progress)
        
        # Start workflow in background
        background_tasks.add_task(
            orchestrator.execute_workflow,
            workflow_input,
            progress_callback
        )
        
        # Return workflow ID immediately
        return {
            "workflowId": "temp_id",  # Will be replaced by actual ID from orchestrator
            "status": "started",
            "message": "Enhanced project creation workflow started successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to start workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {str(e)}")

@router.get("/status/{workflow_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    orchestrator: ProjectCreationOrchestrator = Depends(get_orchestrator)
):
    """
    Get the current status of a workflow
    """
    try:
        # Get workflow progress from orchestrator
        progress = orchestrator.active_workflows.get(workflow_id)
        
        if not progress:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return WorkflowStatusResponse(
            workflowId=progress.workflow_id,
            status=progress.status.value,
            currentStage=progress.current_stage.value,
            progressPercentage=progress.progress_percentage,
            currentOperation=progress.current_operation,
            estimatedTimeRemaining=progress.estimated_time_remaining,
            completedStages=[stage.value for stage in progress.completed_stages],
            errorMessage=progress.error_message,
            detailedProgress=progress.detailed_progress,
            startedAt=progress.started_at,
            updatedAt=progress.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow status: {str(e)}")

@router.get("/result/{workflow_id}", response_model=WorkflowResultResponse)
async def get_workflow_result(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the final result of a completed workflow
    """
    try:
        # In production, this would query the database for completed workflow results
        # For now, return a placeholder response
        
        raise HTTPException(status_code=404, detail="Workflow result not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow result: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow result: {str(e)}")

@router.delete("/cancel/{workflow_id}")
async def cancel_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    orchestrator: ProjectCreationOrchestrator = Depends(get_orchestrator)
):
    """
    Cancel a running workflow
    """
    try:
        # Check if workflow exists
        progress = orchestrator.active_workflows.get(workflow_id)
        
        if not progress:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        if progress.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]:
            raise HTTPException(status_code=400, detail="Workflow is not running")
        
        # Cancel workflow (implementation depends on orchestrator capabilities)
        # For now, just mark as cancelled
        progress.status = WorkflowStatus.CANCELLED
        progress.error_message = "Workflow cancelled by user"
        progress.updated_at = datetime.now()
        
        # Notify WebSocket connections
        await manager.send_progress_update(workflow_id, progress)
        
        return {"message": "Workflow cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel workflow: {str(e)}")

@router.websocket("/ws/{workflow_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    workflow_id: str,
    # Note: WebSocket authentication would need to be handled differently
    # For now, we'll skip authentication for WebSocket connections
):
    """
    WebSocket endpoint for real-time workflow progress updates
    """
    await manager.connect(websocket, workflow_id)
    
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_text()
            
            # Handle ping/pong or other control messages
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, workflow_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, workflow_id)

@router.get("/repositories/discover")
async def discover_repositories(
    technologies: str,
    experience_level: str = "intermediate",
    max_results: int = 10,
    current_user: User = Depends(get_current_user),
    orchestrator: ProjectCreationOrchestrator = Depends(get_orchestrator)
):
    """
    Discover repositories based on criteria (for testing/preview)
    """
    try:
        # Parse technologies
        tech_list = [tech.strip() for tech in technologies.split(',')]
        
        # Create search criteria
        criteria = RepositorySearchCriteria(
            technologies=tech_list,
            experience_level=experience_level,
            learning_goals=[],
            time_commitment="moderate",
            learning_style="hands_on",
            current_skills=tech_list,
            preferred_languages=tech_list,
            exclude_forks=True,
            min_stars=10,
            max_age_months=24,
            require_documentation=True
        )
        
        # Discover repositories
        repositories = await orchestrator.discovery_agent.discover_repositories(
            criteria=criteria,
            user_id=current_user.id,
            max_results=max_results
        )
        
        # Convert to response format
        repo_responses = []
        for repo in repositories:
            repo_responses.append(RepositoryInfo(
                id=repo.id,
                name=repo.name,
                fullName=repo.full_name,
                description=repo.description,
                url=repo.url,
                language=repo.language,
                languages=repo.languages,
                topics=repo.topics,
                stars=repo.quality_metrics.stars,
                forks=repo.quality_metrics.forks,
                relevanceScore=repo.relevance_score,
                finalScore=repo.final_score,
                selectionReasoning=repo.selection_reasoning,
                learningPathSuggestions=repo.learning_path_suggestions
            ))
        
        return {
            "repositories": repo_responses,
            "total": len(repo_responses),
            "criteria": {
                "technologies": tech_list,
                "experienceLevel": experience_level
            }
        }
        
    except Exception as e:
        logger.error(f"Repository discovery failed: {e}")
        raise HTTPException(status_code=500, detail=f"Repository discovery failed: {str(e)}")