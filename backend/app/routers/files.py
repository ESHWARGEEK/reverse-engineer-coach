"""
Code editor integration API endpoints for file management with enhanced authentication
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from app.database import get_db
from app.repositories import RepositoryFactory
from app.models import ProjectFile, User
from app.middleware.auth_middleware import get_current_active_user

router = APIRouter()

# Pydantic models for request/response
class FileCreateRequest(BaseModel):
    file_path: str = Field(..., description="Relative file path within project")
    content: str = Field(default="", description="File content")
    language: Optional[str] = Field(None, description="Programming language")

class FileUpdateRequest(BaseModel):
    content: str = Field(..., description="Updated file content")
    language: Optional[str] = Field(None, description="Programming language")

class FileResponse(BaseModel):
    id: str
    project_id: str
    file_path: str
    content: str
    language: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class FileListResponse(BaseModel):
    files: List[FileResponse]
    total_count: int

class ProjectStructureNode(BaseModel):
    name: str
    path: str
    type: str  # "file" or "directory"
    children: Optional[List['ProjectStructureNode']] = None
    language: Optional[str] = None
    size: Optional[int] = None

class ProjectStructureResponse(BaseModel):
    project_id: str
    structure: List[ProjectStructureNode]
    total_files: int

# Update forward reference
ProjectStructureNode.model_rebuild()

@router.post("/{project_id}/files", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def create_file(
    project_id: str,
    request: FileCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new file within a project (only if user owns the project)
    """
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        file_repo = repo_factory.project_file_repo()
        
        # Verify project exists and user owns it
        project = project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        if project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only modify your own projects"
            )
        
        # Check if file already exists
        existing_file = file_repo.get_by_file_path(project_id, request.file_path)
        if existing_file:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"File '{request.file_path}' already exists"
            )
        
        # Create the file
        project_file = file_repo.create(
            project_id=project_id,
            file_path=request.file_path,
            content=request.content,
            language=request.language
        )
        
        return FileResponse.model_validate(project_file)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create file: {str(e)}"
        )

@router.get("/{project_id}/files", response_model=FileListResponse)
async def list_files(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    language: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all files in a project, optionally filtered by language (only if user owns the project)
    """
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        file_repo = repo_factory.project_file_repo()
        
        # Verify project exists and user owns it
        project = project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        if project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access your own projects"
            )
        
        # Get files, optionally filtered by language
        if language:
            files = file_repo.get_by_language(project_id, language)
        else:
            files = file_repo.get_by_project_id(project_id)
        
        file_responses = [FileResponse.model_validate(f) for f in files]
        
        return FileListResponse(
            files=file_responses,
            total_count=len(file_responses)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )

@router.get("/{project_id}/files/{file_path:path}", response_model=FileResponse)
async def get_file(
    project_id: str,
    file_path: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific file by path within a project (only if user owns the project)
    """
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        file_repo = repo_factory.project_file_repo()
        
        # Verify project exists and user owns it
        project = project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        if project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access your own projects"
            )
        
        # Get the file
        project_file = file_repo.get_by_file_path(project_id, file_path)
        if not project_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File '{file_path}' not found"
            )
        
        return FileResponse.model_validate(project_file)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get file: {str(e)}"
        )


@router.put("/{project_id}/files/{file_path:path}", response_model=FileResponse)
async def update_file(
    project_id: str,
    file_path: str,
    request: FileUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update file content (creates file if it doesn't exist - upsert behavior) (only if user owns the project)
    """
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        file_repo = repo_factory.project_file_repo()
        
        # Verify project exists and user owns it
        project = project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        if project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only modify your own projects"
            )
        
        # Update or create file content
        project_file = file_repo.update_file_content(
            project_id, 
            file_path, 
            request.content
        )
        
        # Update language if provided
        if request.language and project_file:
            project_file = file_repo.update(project_file.id, language=request.language)
        
        return FileResponse.model_validate(project_file)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update file: {str(e)}"
        )

@router.delete("/{project_id}/files/{file_path:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    project_id: str,
    file_path: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a file from a project (only if user owns the project)
    """
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        file_repo = repo_factory.project_file_repo()
        
        # Verify project exists and user owns it
        project = project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        if project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only modify your own projects"
            )
        
        # Delete the file
        success = file_repo.delete_by_path(project_id, file_path)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File '{file_path}' not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )


@router.get("/{project_id}/structure", response_model=ProjectStructureResponse)
async def get_project_structure(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the hierarchical structure of files in a project (only if user owns the project)
    """
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        file_repo = repo_factory.project_file_repo()
        
        # Verify project exists and user owns it
        project = project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        if project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access your own projects"
            )
        
        # Get all files
        files = file_repo.get_by_project_id(project_id)
        
        # Build hierarchical structure
        structure = _build_project_structure(files)
        
        return ProjectStructureResponse(
            project_id=project_id,
            structure=structure,
            total_files=len(files)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project structure: {str(e)}"
        )

@router.post("/{project_id}/files/batch", response_model=List[FileResponse])
async def create_multiple_files(
    project_id: str,
    files: List[FileCreateRequest],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create multiple files in a project at once (only if user owns the project)
    """
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        file_repo = repo_factory.project_file_repo()
        
        # Verify project exists and user owns it
        project = project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        if project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only modify your own projects"
            )
        
        created_files = []
        
        for file_request in files:
            # Check if file already exists
            existing_file = file_repo.get_by_file_path(project_id, file_request.file_path)
            if existing_file:
                # Skip existing files or update them based on preference
                # For now, we'll update existing files
                updated_file = file_repo.update_file_content(
                    project_id,
                    file_request.file_path,
                    file_request.content
                )
                if file_request.language and updated_file:
                    updated_file = file_repo.update(updated_file.id, language=file_request.language)
                created_files.append(updated_file)
            else:
                # Create new file
                project_file = file_repo.create(
                    project_id=project_id,
                    file_path=file_request.file_path,
                    content=file_request.content,
                    language=file_request.language
                )
                created_files.append(project_file)
        
        return [FileResponse.model_validate(f) for f in created_files]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create files: {str(e)}"
        )


@router.get("/{project_id}/files/search/{query}")
async def search_files(
    project_id: str,
    query: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Search files by content or filename (only if user owns the project)
    """
    try:
        repo_factory = RepositoryFactory(db)
        project_repo = repo_factory.learning_project_repo()
        file_repo = repo_factory.project_file_repo()
        
        # Verify project exists and user owns it
        project = project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        if project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access your own projects"
            )
        
        # Get all files for the project
        all_files = file_repo.get_by_project_id(project_id)
        
        # Filter files that match the query (filename or content)
        matching_files = []
        for file in all_files:
            if (query.lower() in file.file_path.lower() or 
                query.lower() in file.content.lower()):
                matching_files.append(file)
        
        file_responses = [FileResponse.model_validate(f) for f in matching_files]
        
        return FileListResponse(
            files=file_responses,
            total_count=len(file_responses)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search files: {str(e)}"
        )

def _build_project_structure(files: List[ProjectFile]) -> List[ProjectStructureNode]:
    """
    Build a hierarchical structure from a flat list of files
    """
    structure = {}
    
    for file in files:
        path_parts = file.file_path.split('/')
        current_level = structure
        
        # Build the directory structure
        for i, part in enumerate(path_parts):
            if part not in current_level:
                is_file = i == len(path_parts) - 1
                current_level[part] = {
                    'name': part,
                    'path': '/'.join(path_parts[:i+1]),
                    'type': 'file' if is_file else 'directory',
                    'children': {} if not is_file else None,
                    'language': file.language if is_file else None,
                    'size': len(file.content) if is_file else None
                }
            
            if current_level[part]['type'] == 'directory':
                current_level = current_level[part]['children']
    
    # Convert nested dict to list of ProjectStructureNode
    def dict_to_nodes(node_dict: Dict) -> List[ProjectStructureNode]:
        nodes = []
        for key, value in node_dict.items():
            children = None
            if value['children'] is not None:
                children = dict_to_nodes(value['children'])
            
            node = ProjectStructureNode(
                name=value['name'],
                path=value['path'],
                type=value['type'],
                children=children,
                language=value['language'],
                size=value['size']
            )
            nodes.append(node)
        
        # Sort: directories first, then files, both alphabetically
        nodes.sort(key=lambda x: (x.type == 'file', x.name.lower()))
        return nodes
    
    return dict_to_nodes(structure)