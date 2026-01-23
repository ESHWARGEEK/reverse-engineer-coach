"""
Unit tests for repository operations
Tests CRUD operations with known data and constraint validation
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tests.test_models import Base, LearningProject, ProjectFile, ReferenceSnippet
from app.repositories import (
    LearningProjectRepository, ProjectFileRepository, ReferenceSnippetRepository,
    RepositoryFactory
)


@pytest.fixture
def test_session():
    """Create a test database session"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture
def repo_factory(test_session):
    """Create repository factory with test session"""
    return RepositoryFactory(test_session)


class TestLearningProjectRepository:
    """Test LearningProject repository operations"""
    
    def test_create_project(self, test_session):
        """Test creating a new learning project"""
        repo = LearningProjectRepository(test_session)
        
        project_data = {
            "user_id": "user123",
            "title": "Learn Redis Architecture",
            "target_repository": "https://github.com/redis/redis",
            "architecture_topic": "Concurrency",
            "status": "created"
        }
        
        project = repo.create(**project_data)
        
        assert project.id is not None
        assert project.user_id == "user123"
        assert project.title == "Learn Redis Architecture"
        assert project.target_repository == "https://github.com/redis/redis"
        assert project.architecture_topic == "Concurrency"
        assert project.status == "created"
        assert project.total_tasks == 0
        assert project.completed_tasks == 0
        assert project.completion_percentage == 0.0
    
    def test_get_by_id(self, test_session):
        """Test retrieving project by ID"""
        repo = LearningProjectRepository(test_session)
        
        # Create a project
        project = repo.create(
            user_id="user123",
            title="Test Project",
            target_repository="https://github.com/test/repo",
            architecture_topic="Testing",
            status="created"
        )
        
        # Retrieve by ID
        retrieved = repo.get_by_id(project.id)
        
        assert retrieved is not None
        assert retrieved.id == project.id
        assert retrieved.title == "Test Project"
    
    def test_get_by_user_id(self, test_session):
        """Test retrieving projects by user ID"""
        repo = LearningProjectRepository(test_session)
        
        # Create multiple projects for different users
        project1 = repo.create(
            user_id="user123",
            title="Project 1",
            target_repository="https://github.com/test/repo1",
            architecture_topic="Testing",
            status="created"
        )
        
        project2 = repo.create(
            user_id="user123",
            title="Project 2",
            target_repository="https://github.com/test/repo2",
            architecture_topic="Testing",
            status="in_progress"
        )
        
        project3 = repo.create(
            user_id="user456",
            title="Project 3",
            target_repository="https://github.com/test/repo3",
            architecture_topic="Testing",
            status="created"
        )
        
        # Get projects for user123
        user_projects = repo.get_by_user_id("user123")
        
        assert len(user_projects) == 2
        assert all(p.user_id == "user123" for p in user_projects)
        assert {p.title for p in user_projects} == {"Project 1", "Project 2"}
    
    def test_update_progress(self, test_session):
        """Test updating project progress"""
        repo = LearningProjectRepository(test_session)
        
        project = repo.create(
            user_id="user123",
            title="Progress Test",
            target_repository="https://github.com/test/repo",
            architecture_topic="Testing",
            status="in_progress"
        )
        
        # Update progress
        updated = repo.update_progress(project.id, completed_tasks=3, total_tasks=10)
        
        assert updated is not None
        assert updated.completed_tasks == 3
        assert updated.total_tasks == 10
        assert updated.completion_percentage == 30.0
    
    def test_search_by_topic(self, test_session):
        """Test searching projects by architecture topic"""
        repo = LearningProjectRepository(test_session)
        
        # Create projects with different topics
        repo.create(
            user_id="user123",
            title="Redis Project",
            target_repository="https://github.com/redis/redis",
            architecture_topic="Concurrency",
            status="created"
        )
        
        repo.create(
            user_id="user123",
            title="Kubernetes Project",
            target_repository="https://github.com/kubernetes/kubernetes",
            architecture_topic="Scheduler",
            status="created"
        )
        
        repo.create(
            user_id="user123",
            title="Another Concurrency Project",
            target_repository="https://github.com/test/concurrent",
            architecture_topic="Concurrency Patterns",
            status="created"
        )
        
        # Search for concurrency projects
        concurrency_projects = repo.search_by_topic("Concurrency")
        
        assert len(concurrency_projects) == 2
        assert all("Concurrency" in p.architecture_topic for p in concurrency_projects)
    
    def test_delete_project(self, test_session):
        """Test deleting a project"""
        repo = LearningProjectRepository(test_session)
        
        project = repo.create(
            user_id="user123",
            title="To Delete",
            target_repository="https://github.com/test/delete",
            architecture_topic="Testing",
            status="created"
        )
        
        # Delete the project
        deleted = repo.delete(project.id)
        
        assert deleted is True
        
        # Verify it's gone
        retrieved = repo.get_by_id(project.id)
        assert retrieved is None


class TestProjectFileRepository:
    """Test ProjectFile repository operations"""
    
    def test_create_and_get_file(self, test_session):
        """Test creating and retrieving project files"""
        project_repo = LearningProjectRepository(test_session)
        file_repo = ProjectFileRepository(test_session)
        
        # Create a parent project
        project = project_repo.create(
            user_id="user123",
            title="File Test Project",
            target_repository="https://github.com/test/files",
            architecture_topic="Testing",
            status="created"
        )
        
        # Create a file
        file_data = {
            "project_id": project.id,
            "file_path": "main.py",
            "content": "print('Hello World')",
            "language": "python"
        }
        
        project_file = file_repo.create(**file_data)
        
        assert project_file.id is not None
        assert project_file.project_id == project.id
        assert project_file.file_path == "main.py"
        assert project_file.content == "print('Hello World')"
        assert project_file.language == "python"
    
    def test_get_by_project_id(self, test_session):
        """Test retrieving all files for a project"""
        project_repo = LearningProjectRepository(test_session)
        file_repo = ProjectFileRepository(test_session)
        
        # Create a project
        project = project_repo.create(
            user_id="user123",
            title="Multi-file Project",
            target_repository="https://github.com/test/multifile",
            architecture_topic="Testing",
            status="created"
        )
        
        # Create multiple files
        files_data = [
            {"file_path": "main.py", "content": "# Main file", "language": "python"},
            {"file_path": "utils.py", "content": "# Utilities", "language": "python"},
            {"file_path": "config.json", "content": "{}", "language": "json"}
        ]
        
        for file_data in files_data:
            file_repo.create(project_id=project.id, **file_data)
        
        # Retrieve all files
        project_files = file_repo.get_by_project_id(project.id)
        
        assert len(project_files) == 3
        assert {f.file_path for f in project_files} == {"main.py", "utils.py", "config.json"}
    
    def test_update_file_content(self, test_session):
        """Test updating file content"""
        project_repo = LearningProjectRepository(test_session)
        file_repo = ProjectFileRepository(test_session)
        
        # Create project and file
        project = project_repo.create(
            user_id="user123",
            title="Update Test",
            target_repository="https://github.com/test/update",
            architecture_topic="Testing",
            status="created"
        )
        
        # Update file content (should create new file)
        updated_file = file_repo.update_file_content(
            project.id, 
            "new_file.py", 
            "print('New content')"
        )
        
        assert updated_file is not None
        assert updated_file.file_path == "new_file.py"
        assert updated_file.content == "print('New content')"
        
        # Update existing file content
        updated_again = file_repo.update_file_content(
            project.id,
            "new_file.py",
            "print('Updated content')"
        )
        
        assert updated_again.content == "print('Updated content')"
        assert updated_again.id == updated_file.id  # Same file, updated
    
    def test_get_by_language(self, test_session):
        """Test retrieving files by programming language"""
        project_repo = LearningProjectRepository(test_session)
        file_repo = ProjectFileRepository(test_session)
        
        # Create project
        project = project_repo.create(
            user_id="user123",
            title="Language Test",
            target_repository="https://github.com/test/lang",
            architecture_topic="Testing",
            status="created"
        )
        
        # Create files in different languages
        file_repo.create(project_id=project.id, file_path="main.py", content="# Python", language="python")
        file_repo.create(project_id=project.id, file_path="app.ts", content="// TypeScript", language="typescript")
        file_repo.create(project_id=project.id, file_path="util.py", content="# More Python", language="python")
        
        # Get Python files
        python_files = file_repo.get_by_language(project.id, "python")
        
        assert len(python_files) == 2
        assert all(f.language == "python" for f in python_files)
        assert {f.file_path for f in python_files} == {"main.py", "util.py"}


class TestReferenceSnippetRepository:
    """Test ReferenceSnippet repository operations"""
    
    def test_create_and_get_snippet(self, test_session):
        """Test creating and retrieving reference snippets"""
        repo = ReferenceSnippetRepository(test_session)
        
        snippet_data = {
            "github_url": "https://github.com/redis/redis/blob/main/src/server.c#L1234",
            "file_path": "src/server.c",
            "start_line": 1234,
            "end_line": 1250,
            "code_content": "void initServer(void) {\n    // Server initialization\n}",
            "commit_sha": "abc123def456789012345678901234567890abcd",
            "explanation": "Server initialization function"
        }
        
        snippet = repo.create(**snippet_data)
        
        assert snippet.id is not None
        assert snippet.github_url == snippet_data["github_url"]
        assert snippet.file_path == "src/server.c"
        assert snippet.start_line == 1234
        assert snippet.end_line == 1250
        assert snippet.commit_sha == "abc123def456789012345678901234567890abcd"
    
    def test_get_by_github_url(self, test_session):
        """Test retrieving snippet by GitHub URL"""
        repo = ReferenceSnippetRepository(test_session)
        
        github_url = "https://github.com/redis/redis/blob/main/src/server.c#L1234"
        
        snippet = repo.create(
            github_url=github_url,
            file_path="src/server.c",
            start_line=1234,
            end_line=1250,
            code_content="test code",
            commit_sha="abc123def456789012345678901234567890abcd"
        )
        
        # Retrieve by URL
        retrieved = repo.get_by_github_url(github_url)
        
        assert retrieved is not None
        assert retrieved.id == snippet.id
        assert retrieved.github_url == github_url
    
    def test_search_by_content(self, test_session):
        """Test searching snippets by code content"""
        repo = ReferenceSnippetRepository(test_session)
        
        # Create snippets with different content
        repo.create(
            github_url="https://github.com/test/repo1/blob/main/file1.c#L1",
            file_path="file1.c",
            start_line=1,
            end_line=5,
            code_content="void initServer(void) { /* initialization */ }",
            commit_sha="abc123def456789012345678901234567890abcd"
        )
        
        repo.create(
            github_url="https://github.com/test/repo2/blob/main/file2.c#L10",
            file_path="file2.c",
            start_line=10,
            end_line=15,
            code_content="int processClient(client *c) { /* client processing */ }",
            commit_sha="def456abc789012345678901234567890abcdef1"
        )
        
        repo.create(
            github_url="https://github.com/test/repo3/blob/main/file3.c#L20",
            file_path="file3.c",
            start_line=20,
            end_line=25,
            code_content="void shutdownServer(void) { /* cleanup */ }",
            commit_sha="789012def456abc345678901234567890abcdef2"
        )
        
        # Search for server-related code
        server_snippets = repo.search_by_content("Server")
        
        assert len(server_snippets) == 2
        assert all("Server" in s.code_content for s in server_snippets)


class TestRepositoryFactory:
    """Test repository factory"""
    
    def test_factory_creates_repositories(self, repo_factory):
        """Test that factory creates all repository types"""
        
        # Test that all repository methods return the correct types
        assert isinstance(repo_factory.learning_project_repo(), LearningProjectRepository)
        assert isinstance(repo_factory.project_file_repo(), ProjectFileRepository)
        assert isinstance(repo_factory.reference_snippet_repo(), ReferenceSnippetRepository)
    
    def test_repositories_share_session(self, test_session):
        """Test that repositories created by factory share the same session"""
        factory = RepositoryFactory(test_session)
        
        project_repo = factory.learning_project_repo()
        file_repo = factory.project_file_repo()
        
        # Both repositories should use the same database session
        assert project_repo.db is test_session
        assert file_repo.db is test_session


class TestConstraintValidation:
    """Test constraint validation and error handling"""
    
    def test_foreign_key_constraint(self, test_session):
        """Test foreign key constraint validation"""
        file_repo = ProjectFileRepository(test_session)
        
        # Try to create a file with non-existent project_id
        with pytest.raises(Exception):  # Should raise integrity error
            file_repo.create(
                project_id="non-existent-id",
                file_path="test.py",
                content="test content",
                language="python"
            )
    
    def test_update_nonexistent_entity(self, test_session):
        """Test updating non-existent entity"""
        repo = LearningProjectRepository(test_session)
        
        # Try to update non-existent project
        result = repo.update("non-existent-id", title="New Title")
        
        assert result is None
    
    def test_delete_nonexistent_entity(self, test_session):
        """Test deleting non-existent entity"""
        repo = LearningProjectRepository(test_session)
        
        # Try to delete non-existent project
        result = repo.delete("non-existent-id")
        
        assert result is False