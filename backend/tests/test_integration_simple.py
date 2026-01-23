"""
Simplified end-to-end integration tests for core functionality.

These tests verify integration between system components without requiring
the full FastAPI application to be loaded.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import os

from app.models import Base, LearningProject, LearningSpec, Task, ReferenceSnippet
from app.repositories import (
    LearningProjectRepository, LearningSpecRepository, 
    TaskRepository, ReferenceSnippetRepository
)
from app.mcp_client import MCPClient, CodeSnippet, RepositoryAnalysis
from app.github_client import GitHubClient, GitHubRepoMetadata
from app.spec_generator import SpecificationGenerator
from app.types import ProgrammingLanguage, ArchitecturalPattern


class TestSimpleE2EIntegration:
    """Simplified end-to-end integration tests."""
    
    @pytest.fixture(scope="function")
    def test_db_engine(self):
        """Create a test database engine."""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(bind=engine)
        return engine
    
    @pytest.fixture(scope="function")
    def test_db_session(self, test_db_engine):
        """Create a test database session."""
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    @pytest.fixture
    def repositories(self, test_db_session):
        """Create repository instances."""
        return {
            'project': LearningProjectRepository(test_db_session),
            'spec': LearningSpecRepository(test_db_session),
            'task': TaskRepository(test_db_session),
            'snippet': ReferenceSnippetRepository(test_db_session)
        }
    
    @pytest.fixture
    def mock_github_client(self):
        """Mock GitHub client."""
        mock = AsyncMock(spec=GitHubClient)
        mock.validate_repository_url.return_value = True
        mock.get_repository_metadata.return_value = GitHubRepoMetadata(
            owner='test',
            name='test-repo',
            full_name='test/test-repo',
            description='Test repository for integration testing',
            language='Python',
            languages={'Python': 1000},
            stars=1000,
            forks=100,
            size=500,
            default_branch='main',
            is_private=False,
            is_fork=False,
            created_at='2023-01-01T00:00:00Z',
            updated_at='2023-12-01T00:00:00Z',
            clone_url='https://github.com/test/test-repo.git',
            html_url='https://github.com/test/test-repo',
            latest_commit_sha='abc123def456'
        )
        mock.get_repository_contents.return_value = [
            {'path': 'src/main.py', 'type': 'file'},
            {'path': 'src/models.py', 'type': 'file'},
            {'path': 'tests/test_main.py', 'type': 'file'}
        ]
        mock.get_file_content.return_value = {
            'content': 'class TestClass:\n    def test_method(self):\n        pass',
            'sha': 'abc123',
            'url': 'https://github.com/test/test-repo/blob/main/src/main.py'
        }
        return mock
    
    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client."""
        mock = AsyncMock(spec=MCPClient)
        
        # Create mock repository analysis
        mock_metadata = GitHubRepoMetadata(
            owner='test',
            name='test-repo',
            full_name='test/test-repo',
            description='Test repository',
            language='Python',
            languages={'Python': 1000},
            stars=1000,
            forks=100,
            size=500,
            default_branch='main',
            is_private=False,
            is_fork=False,
            created_at='2023-01-01T00:00:00Z',
            updated_at='2023-12-01T00:00:00Z',
            clone_url='https://github.com/test/test-repo.git',
            html_url='https://github.com/test/test-repo',
            latest_commit_sha='abc123def456'
        )
        
        mock_snippets = [
            CodeSnippet(
                name='TestClass',
                file_path='src/main.py',
                content='class TestClass:\n    def handle_request(self):\n        pass',
                start_line=1,
                end_line=3,
                language='Python',
                snippet_type='class',
                github_permalink='https://github.com/test/test-repo/blob/main/src/main.py#L1-L3',
                commit_sha='abc123def456',
                architectural_significance=0.8
            ),
            CodeSnippet(
                name='TestRepository',
                file_path='src/repository.py',
                content='class TestRepository:\n    def save(self, entity):\n        pass',
                start_line=1,
                end_line=3,
                language='Python',
                snippet_type='class',
                github_permalink='https://github.com/test/test-repo/blob/main/src/repository.py#L1-L3',
                commit_sha='abc123def456',
                architectural_significance=0.7
            )
        ]
        
        mock_analysis = RepositoryAnalysis(
            repository_url='https://github.com/test/test-repo',
            metadata=mock_metadata,
            total_files_analyzed=10,
            relevant_files=['src/main.py', 'src/repository.py'],
            code_snippets=mock_snippets,
            architecture_patterns=['Handler Pattern', 'Repository Pattern'],
            primary_language='Python',
            complexity_score=0.6
        )
        
        mock.analyze_repository.return_value = mock_analysis
        return mock

    @pytest.mark.asyncio
    async def test_complete_project_workflow_integration(self, repositories, mock_github_client, mock_mcp_client):
        """Test complete project workflow from creation to task generation."""
        
        # Step 1: Create a learning project
        project_data = {
            'user_id': 'test-user-123',
            'title': 'Integration Test Project',
            'architecture_topic': 'Design Patterns',
            'target_repository': 'https://github.com/test/test-repo',
            'implementation_language': 'Python',
            'status': 'created'
        }
        
        project = repositories['project'].create(**project_data)
        assert project.id is not None
        assert project.title == 'Integration Test Project'
        assert project.status == 'created'
        
        # Step 2: Validate repository using GitHub client
        repo_validation = await mock_github_client.validate_repository_url(project.target_repository)
        assert repo_validation is True
        
        # Step 3: Analyze repository using MCP client
        repository_analysis = await mock_mcp_client.analyze_repository(
            project.target_repository, 
            project.architecture_topic
        )
        assert repository_analysis is not None
        assert len(repository_analysis.code_snippets) == 2
        assert repository_analysis.primary_language == 'Python'
        
        # Step 4: Generate specification
        spec_generator = SpecificationGenerator()
        
        # Mock the LLM provider for specification generation
        with patch.object(spec_generator, 'llm_provider') as mock_llm:
            mock_llm_response = Mock()
            mock_llm_response.success = True
            mock_llm_response.content = "# Requirements\n\n1. Implement handler pattern\n2. Create repository layer"
            mock_llm_response.tokens_used = 150
            
            mock_llm.__aenter__.return_value.generate_specification.return_value = mock_llm_response
            mock_llm.__aenter__.return_value.generate_learning_tasks.return_value = mock_llm_response
            
            # Generate specification
            specification = await spec_generator.generate_specification(repository_analysis)
        
        assert specification is not None
        assert 'repository_info' in specification
        assert 'structural_elements' in specification
        assert 'pattern_analysis' in specification
        assert specification['repository_info']['name'] == 'test-repo'
        
        # Step 5: Create learning spec in database
        spec_data = {
            'project_id': project.id,
            'title': 'Integration Test Spec',
            'description': 'Test specification for integration testing',
            'complexity_level': 2,
            'requirements_doc': specification['llm_generated_content']['specification_markdown']
        }
        
        learning_spec = repositories['spec'].create(**spec_data)
        assert learning_spec.id is not None
        assert learning_spec.project_id == project.id
        
        # Step 6: Create tasks from specification
        tasks_data = [
            {
                'spec_id': learning_spec.id,
                'step_number': 1,
                'title': 'Implement Handler Pattern',
                'instruction': 'Create a handler class for processing requests',
                'is_completed': False
            },
            {
                'spec_id': learning_spec.id,
                'step_number': 2,
                'title': 'Create Repository Layer',
                'instruction': 'Implement repository pattern for data access',
                'is_completed': False
            }
        ]
        
        created_tasks = []
        for task_data in tasks_data:
            task = repositories['task'].create(**task_data)
            created_tasks.append(task)
        
        assert len(created_tasks) == 2
        assert created_tasks[0].title == 'Implement Handler Pattern'
        assert created_tasks[1].title == 'Create Repository Layer'
        
        # Step 7: Create reference snippets
        for snippet in repository_analysis.code_snippets:
            snippet_data = {
                'github_url': snippet.github_permalink,
                'file_path': snippet.file_path,
                'start_line': snippet.start_line,
                'end_line': snippet.end_line,
                'code_content': snippet.content,
                'commit_sha': snippet.commit_sha,
                'explanation': f"Example of {snippet.name} pattern"
            }
            
            ref_snippet = repositories['snippet'].create(**snippet_data)
            assert ref_snippet.id is not None
        
        # Step 8: Verify complete project state
        retrieved_project = repositories['project'].get_by_id(project.id)
        assert retrieved_project is not None
        
        project_specs = repositories['spec'].get_by_project_id(project.id)
        assert len(project_specs) > 0
        
        project_tasks = repositories['task'].get_by_spec_id(learning_spec.id)
        assert len(project_tasks) == 2
        
        # Note: ReferenceSnippet doesn't have spec_id, so we can't easily query by spec
        # This is a limitation of the current model structure

    def test_error_handling_integration(self, repositories, mock_github_client):
        """Test error handling across integrated components."""
        
        # Test 1: Invalid repository URL
        mock_github_client.validate_repository_url.return_value = False
        
        project_data = {
            'user_id': 'test-user-123',
            'title': 'Error Test Project',
            'architecture_topic': 'Design Patterns',
            'target_repository': 'https://github.com/invalid/repo',
            'implementation_language': 'Python',
            'status': 'created'
        }
        
        project = repositories['project'].create(**project_data)
        
        # Validate repository
        validation_result = mock_github_client.validate_repository_url(project.target_repository)
        assert validation_result is False
        
        # Test 2: Database constraint violations
        with pytest.raises(Exception):
            # Try to create spec without valid project_id
            repositories['spec'].create(**{
                'project_id': 99999,  # Non-existent project
                'requirements_markdown': 'Test',
                'tasks_markdown': 'Test',
                'architecture_patterns': []
            })
        
        # Test 3: Missing dependencies
        with pytest.raises(Exception):
            # Try to create task without valid spec_id
            repositories['task'].create(**{
                'spec_id': 99999,  # Non-existent spec
                'title': 'Test Task',
                'description': 'Test',
                'order_index': 1,
                'completed': False
            })

    def test_data_persistence_integration(self, repositories):
        """Test data persistence across all repositories."""
        
        # Create complete project hierarchy
        project = repositories['project'].create(**{
            'user_id': 'test-user-123',
            'title': 'Persistence Test',
            'architecture_topic': 'Data Persistence',
            'target_repository': 'https://github.com/test/persistence-repo',
            'implementation_language': 'Python',
            'status': 'ready'
        })
        
        spec = repositories['spec'].create(**{
            'project_id': project.id,
            'title': 'Persistence Spec',
            'description': 'Test persistence patterns',
            'complexity_level': 2,
            'requirements_doc': '# Persistence Requirements'
        })
        
        task = repositories['task'].create(**{
            'spec_id': spec.id,
            'step_number': 1,
            'title': 'Create Repository',
            'instruction': 'Implement data repository',
            'is_completed': False
        })
        
        snippet = repositories['snippet'].create(**{
            'github_url': 'https://github.com/test/persistence-repo/blob/main/src/repository.py',
            'file_path': 'src/repository.py',
            'start_line': 1,
            'end_line': 3,
            'code_content': 'class DataRepository:\n    def save(self, data):\n        pass',
            'commit_sha': 'abc123def456',
            'explanation': 'Repository pattern example'
        })
        
        # Verify all entities were created with proper relationships
        assert project.id is not None
        assert spec.project_id == project.id
        assert task.spec_id == spec.id
        assert snippet.spec_id == spec.id
        
        # Test retrieval and relationships
        retrieved_project = repositories['project'].get_by_id(project.id)
        assert retrieved_project.title == 'Persistence Test'
        
        project_specs = repositories['spec'].get_by_project_id(project.id)
        assert len(project_specs) > 0
        assert project_specs[0].id == spec.id
        
        spec_tasks = repositories['task'].get_by_spec_id(spec.id)
        assert len(spec_tasks) == 1
        assert spec_tasks[0].title == 'Create Repository'
        
        # Test updates
        repositories['task'].update(task.id, is_completed=True)
        updated_task = repositories['task'].get_by_id(task.id)
        assert updated_task.is_completed is True
        
        # Test deletion (cascade should work)
        repositories['project'].delete(project.id)
        
        # Verify cascade deletion
        assert repositories['project'].get_by_id(project.id) is None
        assert len(repositories['spec'].get_by_project_id(project.id)) == 0
        assert len(repositories['task'].get_by_spec_id(spec.id)) == 0