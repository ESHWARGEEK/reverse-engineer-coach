"""Test-specific models to avoid import issues"""

from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()


class LearningProject(Base):
    __tablename__ = "learning_projects"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    title = Column(String(255), nullable=False)
    target_repository = Column(String(500), nullable=False)
    architecture_topic = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="created")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Language support
    implementation_language = Column(String(50), nullable=True, default="python")
    preferred_frameworks = Column(JSON, nullable=True)  # List of preferred frameworks
    language_specific_config = Column(JSON, nullable=True)  # Language-specific settings
    
    # Progress tracking
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    current_task_id = Column(String, nullable=True)
    completion_percentage = Column(Float, default=0.0)
    
    # Relationships
    learning_specs = relationship("LearningSpec", back_populates="project", cascade="all, delete-orphan")


class LearningSpec(Base):
    __tablename__ = "learning_specs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("learning_projects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    complexity_level = Column(Integer, nullable=False, default=1)
    requirements_doc = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("LearningProject", back_populates="learning_specs")


class ProjectFile(Base):
    """Stores user's code files for each project"""
    __tablename__ = "project_files"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("learning_projects.id"), nullable=False)
    file_path = Column(String(500), nullable=False)  # Relative path within project
    content = Column(Text, nullable=False)
    language = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ReferenceSnippet(Base):
    __tablename__ = "reference_snippets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    github_url = Column(String(1000), nullable=False)
    file_path = Column(String(500), nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    code_content = Column(Text, nullable=False)
    commit_sha = Column(String(40), nullable=False)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())