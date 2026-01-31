from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid


class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # API Keys and tokens (encrypted) - keeping for backward compatibility
    github_token = Column(Text, nullable=True)  # Encrypted GitHub personal access token
    openai_api_key = Column(Text, nullable=True)  # Encrypted OpenAI API key
    gemini_api_key = Column(Text, nullable=True)  # Encrypted Gemini API key
    preferred_ai_provider = Column(String(50), default="openai")  # "openai" or "gemini"
    
    # User preferences
    preferred_language = Column(String(50), default="python")
    preferred_frameworks = Column(JSON, nullable=True)  # List of preferred frameworks
    learning_preferences = Column(JSON, nullable=True)  # User learning preferences
    
    # Relationships
    projects = relationship("LearningProject", back_populates="user", cascade="all, delete-orphan")
    credentials = relationship("UserCredentials", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")


class UserCredentials(Base):
    __tablename__ = "user_credentials"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    github_token_encrypted = Column(Text, nullable=True)
    ai_api_key_encrypted = Column(Text, nullable=True)
    encryption_key_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="credentials")


class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="sessions")


class RepositoryCache(Base):
    __tablename__ = "repository_cache"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    concept_hash = Column(String(255), nullable=False, index=True)
    repositories = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)


class LearningProject(Base):
    __tablename__ = "learning_projects"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    target_repository = Column(String(500), nullable=False)
    architecture_topic = Column(String(255), nullable=False)
    concept_description = Column(Text, nullable=True)  # Enhanced: User's learning concept input
    discovery_metadata = Column(JSON, nullable=True)  # Enhanced: Repository discovery metadata
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
    user = relationship("User", back_populates="projects")


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String(50), nullable=False, default="pending")  # pending, running, completed, failed, cancelled
    current_stage = Column(String(100), nullable=True)
    progress_percentage = Column(Float, default=0.0)
    
    # Input and output data
    input_data = Column(JSON, nullable=True)  # Workflow input parameters
    result_data = Column(JSON, nullable=True)  # Final workflow results
    error_details = Column(JSON, nullable=True)  # Error information if failed
    
    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    estimated_completion = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    workflow_type = Column(String(100), default="enhanced_project_creation")
    execution_metadata = Column(JSON, nullable=True)  # Additional execution metadata
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User")


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
    tasks = relationship("Task", back_populates="spec", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    spec_id = Column(String, ForeignKey("learning_specs.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    instruction = Column(Text, nullable=False)
    completion_criteria = Column(JSON, nullable=True)  # List of criteria as JSON
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Language-specific task details
    target_language = Column(String(50), nullable=True)
    language_specific_hints = Column(JSON, nullable=True)  # Language-specific hints
    framework_recommendations = Column(JSON, nullable=True)  # Recommended frameworks
    
    # Relationships
    spec = relationship("LearningSpec", back_populates="tasks")
    reference_snippets = relationship("TaskReferenceSnippet", back_populates="task", cascade="all, delete-orphan")


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
    
    # Relationships
    task_associations = relationship("TaskReferenceSnippet", back_populates="snippet", cascade="all, delete-orphan")


class TaskReferenceSnippet(Base):
    """Association table for many-to-many relationship between Tasks and ReferenceSnippets"""
    __tablename__ = "task_reference_snippets"
    
    task_id = Column(String, ForeignKey("tasks.id"), primary_key=True)
    snippet_id = Column(String, ForeignKey("reference_snippets.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    task = relationship("Task", back_populates="reference_snippets")
    snippet = relationship("ReferenceSnippet", back_populates="task_associations")


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
    
    # Relationships
    project = relationship("LearningProject")


class ChatHistory(Base):
    """Stores chat conversation history between users and the AI coach"""
    __tablename__ = "chat_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("learning_projects.id"), nullable=False)
    content = Column(Text, nullable=False)
    sender = Column(String(10), nullable=False)  # 'user' or 'coach'
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Additional coach response metadata (stored as JSON strings)
    context_used = Column(Text, nullable=True)  # JSON string of context sources
    hints = Column(Text, nullable=True)  # JSON string of hints
    suggested_actions = Column(Text, nullable=True)  # JSON string of suggested actions
    
    # Relationships
    project = relationship("LearningProject")


class RepositoryAnalysis(Base):
    """Stores analysis results for repositories"""
    __tablename__ = "repository_analyses"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_url = Column(String(500), nullable=False)
    architecture_topic = Column(String(255), nullable=False)
    analysis_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    identified_patterns = Column(JSON, nullable=True)  # List of architectural patterns
    core_files = Column(JSON, nullable=True)  # List of core file paths
    complexity_score = Column(Float, nullable=True)
    recommended_learning_path = Column(JSON, nullable=True)  # List of learning steps
    
    # Add unique constraint on repository_url + architecture_topic for caching
    __table_args__ = (
        {"schema": None}
    )