"""
Property-based test for learning project creation
Feature: reverse-engineer-coach, Property 2: Learning Project Creation
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tests.test_models import Base
from app.repositories import LearningProjectRepository
import re
from contextlib import contextmanager


@contextmanager
def create_test_session():
    """Create a test database session as context manager"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# Strategy for generating valid GitHub repository URLs
github_url_strategy = st.one_of([
    # Standard GitHub URLs
    st.builds(
        lambda owner, repo: f"https://github.com/{owner}/{repo}",
        owner=st.text(min_size=1, max_size=39, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='-_')).filter(lambda x: x and not x.startswith('-') and not x.endswith('-')),
        repo=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='-_.')).filter(lambda x: x and not x.startswith('.') and not x.endswith('.'))
    ),
    # GitHub URLs with .git suffix
    st.builds(
        lambda owner, repo: f"https://github.com/{owner}/{repo}.git",
        owner=st.text(min_size=1, max_size=39, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='-_')).filter(lambda x: x and not x.startswith('-') and not x.endswith('-')),
        repo=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='-_.')).filter(lambda x: x and not x.startswith('.') and not x.endswith('.'))
    )
])

# Strategy for generating valid architecture topics
architecture_topic_strategy = st.one_of([
    st.just("Concurrency"),
    st.just("Distributed Systems"),
    st.just("Microservices"),
    st.just("Data Structures"),
    st.just("Algorithms"),
    st.just("Caching"),
    st.just("Database Design"),
    st.just("Message Queues"),
    st.just("Load Balancing"),
    st.just("Security"),
    st.text(min_size=1, max_size=255, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'), whitelist_characters='-_')).filter(lambda x: x.strip())
])

# Strategy for generating valid user IDs
user_id_strategy = st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='-_@.')).filter(lambda x: x and len(x.strip()) > 0)

# Strategy for generating valid project titles
title_strategy = st.text(min_size=1, max_size=255).filter(lambda x: x.strip() and len(x.strip()) > 0)


@given(
    user_id=user_id_strategy,
    title=title_strategy,
    repository_url=github_url_strategy,
    architecture_topic=architecture_topic_strategy
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=1000)
def test_learning_project_creation_property(user_id, title, repository_url, architecture_topic):
    """
    Property 2: Learning Project Creation
    For any valid architecture topic and repository URL combination, 
    the System should create a Learning_Project with all specified parameters correctly set
    
    Validates: Requirements 1.3
    """
    with create_test_session() as test_session:
        # Arrange
        repo = LearningProjectRepository(test_session)
        
        # Act - Create project with generated inputs
        project = repo.create(
            user_id=user_id.strip(),
            title=title.strip(),
            target_repository=repository_url,
            architecture_topic=architecture_topic.strip(),
            status="created"
        )
        
        # Assert - Verify all parameters are correctly set
        assert project is not None, "Project should be created successfully"
        assert project.id is not None, "Project should have a valid ID"
        assert project.user_id == user_id.strip(), f"User ID should be set correctly: expected {user_id.strip()}, got {project.user_id}"
        assert project.title == title.strip(), f"Title should be set correctly: expected {title.strip()}, got {project.title}"
        assert project.target_repository == repository_url, f"Repository URL should be set correctly: expected {repository_url}, got {project.target_repository}"
        assert project.architecture_topic == architecture_topic.strip(), f"Architecture topic should be set correctly: expected {architecture_topic.strip()}, got {project.architecture_topic}"
        assert project.status == "created", f"Status should be 'created': got {project.status}"
        
        # Verify default values are set correctly
        assert project.total_tasks == 0, f"Total tasks should default to 0: got {project.total_tasks}"
        assert project.completed_tasks == 0, f"Completed tasks should default to 0: got {project.completed_tasks}"
        assert project.completion_percentage == 0.0, f"Completion percentage should default to 0.0: got {project.completion_percentage}"
        assert project.current_task_id is None, f"Current task ID should default to None: got {project.current_task_id}"
        
        # Verify timestamps are set
        assert project.created_at is not None, "Created timestamp should be set"
        assert project.updated_at is not None, "Updated timestamp should be set"
        
        # Verify project can be retrieved by ID
        retrieved_project = repo.get_by_id(project.id)
        assert retrieved_project is not None, "Project should be retrievable by ID"
        assert retrieved_project.id == project.id, "Retrieved project should have the same ID"
        assert retrieved_project.user_id == project.user_id, "Retrieved project should have the same user ID"
        assert retrieved_project.title == project.title, "Retrieved project should have the same title"
        assert retrieved_project.target_repository == project.target_repository, "Retrieved project should have the same repository URL"
        assert retrieved_project.architecture_topic == project.architecture_topic, "Retrieved project should have the same architecture topic"


@given(
    user_id=user_id_strategy,
    title=title_strategy,
    repository_url=github_url_strategy,
    architecture_topic=architecture_topic_strategy
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=1000)
def test_project_creation_with_user_filtering_property(user_id, title, repository_url, architecture_topic):
    """
    Property: Projects created for a user should be retrievable by user ID
    
    This extends Property 2 to verify user-based filtering works correctly
    """
    with create_test_session() as test_session:
        # Arrange
        repo = LearningProjectRepository(test_session)
        
        # Act - Create project
        project = repo.create(
            user_id=user_id.strip(),
            title=title.strip(),
            target_repository=repository_url,
            architecture_topic=architecture_topic.strip(),
            status="created"
        )
        
        # Assert - Project should be retrievable by user ID
        user_projects = repo.get_by_user_id(user_id.strip())
        
        assert len(user_projects) >= 1, "At least one project should exist for the user"
        
        # Find our created project in the user's projects
        created_project = next((p for p in user_projects if p.id == project.id), None)
        assert created_project is not None, "Created project should be found in user's projects"
        assert created_project.user_id == user_id.strip(), "Project should belong to the correct user"


@given(
    user_id=user_id_strategy,
    title=title_strategy,
    repository_url=github_url_strategy,
    architecture_topic=architecture_topic_strategy,
    status=st.one_of([
        st.just("created"),
        st.just("analyzing"),
        st.just("ready"),
        st.just("in_progress"),
        st.just("completed"),
        st.just("failed")
    ])
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=1000)
def test_project_creation_with_status_filtering_property(user_id, title, repository_url, architecture_topic, status):
    """
    Property: Projects created with a specific status should be retrievable by that status
    
    This extends Property 2 to verify status-based filtering works correctly
    """
    with create_test_session() as test_session:
        # Arrange
        repo = LearningProjectRepository(test_session)
        
        # Act - Create project with specific status
        project = repo.create(
            user_id=user_id.strip(),
            title=title.strip(),
            target_repository=repository_url,
            architecture_topic=architecture_topic.strip(),
            status=status
        )
        
        # Assert - Project should be retrievable by status
        status_projects = repo.get_by_status(status)
        
        assert len(status_projects) >= 1, f"At least one project should exist with status '{status}'"
        
        # Find our created project in the status-filtered projects
        created_project = next((p for p in status_projects if p.id == project.id), None)
        assert created_project is not None, f"Created project should be found in projects with status '{status}'"
        assert created_project.status == status, f"Project should have the correct status: expected {status}, got {created_project.status}"


@given(
    user_id=user_id_strategy,
    title=title_strategy,
    repository_url=github_url_strategy,
    architecture_topic=architecture_topic_strategy
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=1000)
def test_project_creation_topic_search_property(user_id, title, repository_url, architecture_topic):
    """
    Property: Projects created with an architecture topic should be findable by topic search
    
    This extends Property 2 to verify topic-based search works correctly
    """
    with create_test_session() as test_session:
        # Arrange
        repo = LearningProjectRepository(test_session)
        
        # Act - Create project
        project = repo.create(
            user_id=user_id.strip(),
            title=title.strip(),
            target_repository=repository_url,
            architecture_topic=architecture_topic.strip(),
            status="created"
        )
        
        # Assert - Project should be findable by topic search
        # Search using the full topic
        topic_projects = repo.search_by_topic(architecture_topic.strip())
        
        # Find our created project in the search results
        found_project = next((p for p in topic_projects if p.id == project.id), None)
        assert found_project is not None, f"Created project should be found when searching for topic '{architecture_topic.strip()}'"
        assert architecture_topic.strip().lower() in found_project.architecture_topic.lower(), "Found project should contain the searched topic"
        
        # If the topic has multiple words, test partial search
        topic_words = architecture_topic.strip().split()
        if len(topic_words) > 1:
            # Search using the first word
            first_word = topic_words[0]
            if len(first_word) > 2:  # Only test if word is meaningful
                partial_projects = repo.search_by_topic(first_word)
                # Our project might be found (depending on other projects in the session)
                # But if found, it should contain the search term
                found_partial = next((p for p in partial_projects if p.id == project.id), None)
                if found_partial:
                    assert first_word.lower() in found_partial.architecture_topic.lower(), "Partial search should match the topic"


# Additional edge case tests for boundary conditions
def test_project_creation_empty_database_property():
    """
    Property: Project creation should work correctly in an empty database
    """
    with create_test_session() as test_session:
        repo = LearningProjectRepository(test_session)
        
        # Verify database is empty
        all_projects = repo.get_all()
        assert len(all_projects) == 0, "Database should be empty initially"
        
        # Create a project
        project = repo.create(
            user_id="test_user",
            title="First Project",
            target_repository="https://github.com/test/repo",
            architecture_topic="Testing",
            status="created"
        )
        
        # Verify it's the only project
        all_projects = repo.get_all()
        assert len(all_projects) == 1, "Database should contain exactly one project"
        assert all_projects[0].id == project.id, "The project should be the one we created"


@given(st.integers(min_value=1, max_value=10))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=2000)
def test_multiple_project_creation_property(num_projects):
    """
    Property: Multiple projects can be created and each maintains its unique identity
    """
    with create_test_session() as test_session:
        repo = LearningProjectRepository(test_session)
        created_projects = []
        
        # Create multiple projects
        for i in range(num_projects):
            project = repo.create(
                user_id=f"user_{i}",
                title=f"Project {i}",
                target_repository=f"https://github.com/test/repo{i}",
                architecture_topic=f"Topic {i}",
                status="created"
            )
            created_projects.append(project)
        
        # Verify all projects exist and are unique
        all_projects = repo.get_all()
        assert len(all_projects) >= num_projects, f"At least {num_projects} projects should exist"
        
        # Verify each created project can be retrieved and has correct data
        for i, project in enumerate(created_projects):
            retrieved = repo.get_by_id(project.id)
            assert retrieved is not None, f"Project {i} should be retrievable"
            assert retrieved.user_id == f"user_{i}", f"Project {i} should have correct user_id"
            assert retrieved.title == f"Project {i}", f"Project {i} should have correct title"
            assert retrieved.target_repository == f"https://github.com/test/repo{i}", f"Project {i} should have correct repository"
            assert retrieved.architecture_topic == f"Topic {i}", f"Project {i} should have correct topic"
        
        # Verify all project IDs are unique
        project_ids = [p.id for p in created_projects]
        assert len(set(project_ids)) == len(project_ids), "All project IDs should be unique"