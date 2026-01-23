"""
Repository pattern implementation for data access operations
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models import (
    LearningProject, LearningSpec, Task, ReferenceSnippet, 
    TaskReferenceSnippet, ProjectFile, RepositoryAnalysis
)
import uuid


class BaseRepository:
    """Base repository with common CRUD operations"""
    
    def __init__(self, db: Session, model_class):
        self.db = db
        self.model_class = model_class
    
    def create(self, **kwargs) -> Any:
        """Create a new entity"""
        entity = self.model_class(**kwargs)
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity
    
    def get_by_id(self, entity_id: str) -> Optional[Any]:
        """Get entity by ID"""
        return self.db.query(self.model_class).filter(self.model_class.id == entity_id).first()
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[Any]:
        """Get all entities with pagination"""
        return self.db.query(self.model_class).offset(offset).limit(limit).all()
    
    def update(self, entity_id: str, **kwargs) -> Optional[Any]:
        """Update entity by ID"""
        entity = self.get_by_id(entity_id)
        if entity:
            for key, value in kwargs.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            self.db.commit()
            self.db.refresh(entity)
        return entity
    
    def delete(self, entity_id: str) -> bool:
        """Delete entity by ID"""
        entity = self.get_by_id(entity_id)
        if entity:
            self.db.delete(entity)
            self.db.commit()
            return True
        return False


class LearningProjectRepository(BaseRepository):
    """Repository for LearningProject operations"""
    
    def __init__(self, db: Session):
        super().__init__(db, LearningProject)
    
    def get_by_user_id(self, user_id: str, limit: int = 100, offset: int = 0) -> List[LearningProject]:
        """Get all projects for a specific user"""
        return (self.db.query(LearningProject)
                .filter(LearningProject.user_id == user_id)
                .offset(offset)
                .limit(limit)
                .all())
    
    def get_by_status(self, status: str, limit: int = 100, offset: int = 0) -> List[LearningProject]:
        """Get projects by status"""
        return (self.db.query(LearningProject)
                .filter(LearningProject.status == status)
                .offset(offset)
                .limit(limit)
                .all())
    
    def get_by_user_and_status(self, user_id: str, status: str) -> List[LearningProject]:
        """Get projects by user and status"""
        return (self.db.query(LearningProject)
                .filter(and_(LearningProject.user_id == user_id, 
                           LearningProject.status == status))
                .all())
    
    def update_progress(self, project_id: str, completed_tasks: int, total_tasks: int) -> Optional[LearningProject]:
        """Update project progress"""
        completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        return self.update(project_id, 
                         completed_tasks=completed_tasks,
                         total_tasks=total_tasks,
                         completion_percentage=completion_percentage)
    
    def search_by_topic(self, topic: str, limit: int = 100) -> List[LearningProject]:
        """Search projects by architecture topic"""
        return (self.db.query(LearningProject)
                .filter(LearningProject.architecture_topic.ilike(f"%{topic}%"))
                .limit(limit)
                .all())


class LearningSpecRepository(BaseRepository):
    """Repository for LearningSpec operations"""
    
    def __init__(self, db: Session):
        super().__init__(db, LearningSpec)
    
    def get_by_project_id(self, project_id: str) -> List[LearningSpec]:
        """Get all specs for a project"""
        return (self.db.query(LearningSpec)
                .filter(LearningSpec.project_id == project_id)
                .all())
    
    def get_by_complexity_level(self, complexity_level: int, limit: int = 100) -> List[LearningSpec]:
        """Get specs by complexity level"""
        return (self.db.query(LearningSpec)
                .filter(LearningSpec.complexity_level == complexity_level)
                .limit(limit)
                .all())


class TaskRepository(BaseRepository):
    """Repository for Task operations"""
    
    def __init__(self, db: Session):
        super().__init__(db, Task)
    
    def get_by_spec_id(self, spec_id: str) -> List[Task]:
        """Get all tasks for a spec, ordered by step number"""
        return (self.db.query(Task)
                .filter(Task.spec_id == spec_id)
                .order_by(Task.step_number)
                .all())
    
    def get_completed_tasks(self, spec_id: str) -> List[Task]:
        """Get completed tasks for a spec"""
        return (self.db.query(Task)
                .filter(and_(Task.spec_id == spec_id, Task.is_completed == True))
                .order_by(Task.step_number)
                .all())
    
    def get_next_task(self, spec_id: str) -> Optional[Task]:
        """Get the next incomplete task"""
        return (self.db.query(Task)
                .filter(and_(Task.spec_id == spec_id, Task.is_completed == False))
                .order_by(Task.step_number)
                .first())
    
    def mark_completed(self, task_id: str) -> Optional[Task]:
        """Mark a task as completed"""
        return self.update(task_id, is_completed=True)
    
    def get_task_with_snippets(self, task_id: str) -> Optional[Task]:
        """Get task with associated reference snippets"""
        return (self.db.query(Task)
                .filter(Task.id == task_id)
                .first())


class ReferenceSnippetRepository(BaseRepository):
    """Repository for ReferenceSnippet operations"""
    
    def __init__(self, db: Session):
        super().__init__(db, ReferenceSnippet)
    
    def get_by_github_url(self, github_url: str) -> Optional[ReferenceSnippet]:
        """Get snippet by GitHub URL"""
        return (self.db.query(ReferenceSnippet)
                .filter(ReferenceSnippet.github_url == github_url)
                .first())
    
    def get_by_file_path(self, file_path: str, limit: int = 100) -> List[ReferenceSnippet]:
        """Get snippets by file path"""
        return (self.db.query(ReferenceSnippet)
                .filter(ReferenceSnippet.file_path == file_path)
                .limit(limit)
                .all())
    
    def get_by_commit_sha(self, commit_sha: str, limit: int = 100) -> List[ReferenceSnippet]:
        """Get snippets by commit SHA"""
        return (self.db.query(ReferenceSnippet)
                .filter(ReferenceSnippet.commit_sha == commit_sha)
                .limit(limit)
                .all())
    
    def search_by_content(self, search_term: str, limit: int = 100) -> List[ReferenceSnippet]:
        """Search snippets by code content"""
        return (self.db.query(ReferenceSnippet)
                .filter(ReferenceSnippet.code_content.ilike(f"%{search_term}%"))
                .limit(limit)
                .all())


class ProjectFileRepository(BaseRepository):
    """Repository for ProjectFile operations"""
    
    def __init__(self, db: Session):
        super().__init__(db, ProjectFile)
    
    def get_by_project_id(self, project_id: str) -> List[ProjectFile]:
        """Get all files for a project"""
        return (self.db.query(ProjectFile)
                .filter(ProjectFile.project_id == project_id)
                .order_by(ProjectFile.file_path)
                .all())
    
    def get_by_file_path(self, project_id: str, file_path: str) -> Optional[ProjectFile]:
        """Get a specific file by path within a project"""
        return (self.db.query(ProjectFile)
                .filter(and_(ProjectFile.project_id == project_id,
                           ProjectFile.file_path == file_path))
                .first())
    
    def get_by_language(self, project_id: str, language: str) -> List[ProjectFile]:
        """Get files by programming language"""
        return (self.db.query(ProjectFile)
                .filter(and_(ProjectFile.project_id == project_id,
                           ProjectFile.language == language))
                .all())
    
    def update_file_content(self, project_id: str, file_path: str, content: str) -> Optional[ProjectFile]:
        """Update file content or create if doesn't exist"""
        existing_file = self.get_by_file_path(project_id, file_path)
        if existing_file:
            return self.update(existing_file.id, content=content)
        else:
            return self.create(project_id=project_id, file_path=file_path, content=content)
    
    def delete_by_path(self, project_id: str, file_path: str) -> bool:
        """Delete a file by path within a project"""
        file_obj = self.get_by_file_path(project_id, file_path)
        if file_obj:
            return self.delete(file_obj.id)
        return False


class RepositoryAnalysisRepository(BaseRepository):
    """Repository for RepositoryAnalysis operations"""
    
    def __init__(self, db: Session):
        super().__init__(db, RepositoryAnalysis)
    
    def get_by_repository_and_topic(self, repository_url: str, architecture_topic: str) -> Optional[RepositoryAnalysis]:
        """Get analysis by repository URL and topic (for caching)"""
        return (self.db.query(RepositoryAnalysis)
                .filter(and_(RepositoryAnalysis.repository_url == repository_url,
                           RepositoryAnalysis.architecture_topic == architecture_topic))
                .first())
    
    def get_by_repository_url(self, repository_url: str, limit: int = 100) -> List[RepositoryAnalysis]:
        """Get all analyses for a repository"""
        return (self.db.query(RepositoryAnalysis)
                .filter(RepositoryAnalysis.repository_url == repository_url)
                .limit(limit)
                .all())
    
    def get_recent_analyses(self, limit: int = 50) -> List[RepositoryAnalysis]:
        """Get most recent analyses"""
        return (self.db.query(RepositoryAnalysis)
                .order_by(RepositoryAnalysis.analysis_timestamp.desc())
                .limit(limit)
                .all())


class TaskReferenceSnippetRepository:
    """Repository for managing Task-ReferenceSnippet associations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def link_snippet_to_task(self, task_id: str, snippet_id: str) -> TaskReferenceSnippet:
        """Link a reference snippet to a task"""
        association = TaskReferenceSnippet(task_id=task_id, snippet_id=snippet_id)
        self.db.add(association)
        self.db.commit()
        return association
    
    def unlink_snippet_from_task(self, task_id: str, snippet_id: str) -> bool:
        """Unlink a reference snippet from a task"""
        association = (self.db.query(TaskReferenceSnippet)
                      .filter(and_(TaskReferenceSnippet.task_id == task_id,
                                 TaskReferenceSnippet.snippet_id == snippet_id))
                      .first())
        if association:
            self.db.delete(association)
            self.db.commit()
            return True
        return False
    
    def get_snippets_for_task(self, task_id: str) -> List[ReferenceSnippet]:
        """Get all reference snippets for a task"""
        return (self.db.query(ReferenceSnippet)
                .join(TaskReferenceSnippet)
                .filter(TaskReferenceSnippet.task_id == task_id)
                .all())
    
    def get_tasks_for_snippet(self, snippet_id: str) -> List[Task]:
        """Get all tasks that reference a snippet"""
        return (self.db.query(Task)
                .join(TaskReferenceSnippet)
                .filter(TaskReferenceSnippet.snippet_id == snippet_id)
                .all())


# Repository factory for dependency injection
class RepositoryFactory:
    """Factory for creating repository instances"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def learning_project_repo(self) -> LearningProjectRepository:
        return LearningProjectRepository(self.db)
    
    def learning_spec_repo(self) -> LearningSpecRepository:
        return LearningSpecRepository(self.db)
    
    def task_repo(self) -> TaskRepository:
        return TaskRepository(self.db)
    
    def reference_snippet_repo(self) -> ReferenceSnippetRepository:
        return ReferenceSnippetRepository(self.db)
    
    def project_file_repo(self) -> ProjectFileRepository:
        return ProjectFileRepository(self.db)
    
    def repository_analysis_repo(self) -> RepositoryAnalysisRepository:
        return RepositoryAnalysisRepository(self.db)
    
    def task_reference_snippet_repo(self) -> TaskReferenceSnippetRepository:
        return TaskReferenceSnippetRepository(self.db)