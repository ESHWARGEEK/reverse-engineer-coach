"""
End-to-end integration tests for the Reverse Engineer Coach platform.

These tests verify complete user workflows from project creation to completion,
testing integration between all system components and error scenarios.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import os
import json

from app.main import app
from app.models import Base, LearningProject, LearningSpec, Task, ReferenceSnippet
from app.database import get_db


class TestE2EIntegration:
    """End-to-end integration tests covering complete user workflows."""
    
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
    
    @pytest.fixture(scope="function")
    def test_client(self, test_db_session):
        """Create a test client with database dependency override."""
        def override_get_db():
            try:
                yield test_db_session
            finally:
                pass
        
        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def mock_github_client(self):
        """Mock GitHub client for testing."""
        with patch('app.github_client.GitHubClient') as mock:
            mock_instance = Mock()
            mock_instance.validate_repository.return_value = {
                'valid': True,
                'name': 'test-repo',
                'description': 'Test repository',
                'language': 'Python',
                'stars': 1000,
                'url': 'https://github.com/test/test-repo'
            }
            mock_instance.get_repository_files.return_value = [
                {'path': 'src/main.py', 'type': 'file'},
                {'path': 'src/models.py', 'type': 'file'},
                {'path': 'tests/test_main.py', 'type': 'file'}
            ]
            mock_instance.get_file_content.return_value = {
                'content': 'class TestClass:\n    def test_method(self):\n        pass',
                'sha': 'abc123',
                'url': 'https://github.com/test/test-repo/blob/main/src/main.py'
            }
            mock.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for testing."""
        with patch('app.mcp_client.MCPClient') as mock:
            mock_instance = Mock()
            mock_instance.analyze_repository.return_value = {
                'relevant_files': ['src/main.py', 'src/models.py'],
                'patterns': ['Factory Pattern', 'Repository Pattern'],
                'complexity_score': 0.7
            }
            mock_instance.extract_code_snippets.return_value = [
                {
                    'file_path': 'src/main.py',
                    'content': 'class Factory:\n    def create(self):\n        pass',
                    'start_line': 1,
                    'end_line': 3,
                    'pattern': 'Factory Pattern'
                }
            ]
            mock.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def mock_llm_provider(self):
        """Mock LLM provider for testing."""
        with patch('app.llm_provider.LLMProvider') as mock:
            mock_instance = Mock()
            mock_instance.generate_specification.return_value = {
                'requirements': '# Requirements\n\n1. Implement factory pattern\n2. Add error handling',
                'tasks': [
                    {'id': 1, 'title': 'Implement Factory Pattern', 'description': 'Create a factory class'},
                    {'id': 2, 'title': 'Add Error Handling', 'description': 'Add try-catch blocks'}
                ]
            }
            mock_instance.generate_coach_response.return_value = {
                'response': 'The factory pattern helps create objects without specifying exact classes.',
                'references': ['src/main.py:1-3']
            }
            mock.return_value = mock_instance
            yield mock_instance

    def test_complete_project_creation_workflow(self, test_client, mock_github_client, mock_mcp_client, mock_llm_provider):
        """Test complete workflow from project creation to task generation."""
        
        # Step 1: Create a new learning project
        project_data = {
            'name': 'Learn Factory Pattern',
            'architecture_topic': 'Design Patterns',
            'target_repository': 'https://github.com/test/test-repo',
            'implementation_language': 'Python'
        }
        
        response = test_client.post('/api/projects', json=project_data)
        assert response.status_code == 201
        project = response.json()
        assert project['name'] == 'Learn Factory Pattern'
        assert project['status'] == 'analyzing'
        project_id = project['id']
        
        # Verify GitHub client was called
        mock_github_client.validate_repository.assert_called_once()
        
        # Step 2: Simulate repository analysis completion
        with patch('app.routers.projects.analyze_repository_background') as mock_analyze:
            mock_analyze.return_value = None
            
            # Check project status
            response = test_client.get(f'/api/projects/{project_id}')
            assert response.status_code == 200
            project = response.json()
            
            # Simulate analysis completion by updating project status
            response = test_client.patch(f'/api/projects/{project_id}', json={'status': 'ready'})
            assert response.status_code == 200
        
        # Step 3: Get generated specification
        response = test_client.get(f'/api/projects/{project_id}/spec')
        assert response.status_code == 200
        spec = response.json()
        assert 'requirements' in spec
        assert 'tasks' in spec
        
        # Step 4: Get project tasks
        response = test_client.get(f'/api/projects/{project_id}/tasks')
        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) > 0
        assert tasks[0]['title'] == 'Implement Factory Pattern'
        
        # Step 5: Get reference snippets
        response = test_client.get(f'/api/projects/{project_id}/snippets')
        assert response.status_code == 200
        snippets = response.json()
        assert len(snippets) > 0
        
        # Verify MCP client was called
        mock_mcp_client.analyze_repository.assert_called_once()
        mock_mcp_client.extract_code_snippets.assert_called_once()
        
        # Verify LLM provider was called
        mock_llm_provider.generate_specification.assert_called_once()

    def test_workspace_file_management_workflow(self, test_client, mock_github_client, mock_mcp_client, mock_llm_provider):
        """Test file creation, editing, and persistence in workspace."""
        
        # Create project first
        project_data = {
            'name': 'File Management Test',
            'architecture_topic': 'File Operations',
            'target_repository': 'https://github.com/test/test-repo',
            'implementation_language': 'Python'
        }
        
        response = test_client.post('/api/projects', json=project_data)
        assert response.status_code == 201
        project_id = response.json()['id']
        
        # Step 1: Create a new file
        file_data = {
            'path': 'src/factory.py',
            'content': 'class Factory:\n    pass'
        }
        
        response = test_client.post(f'/api/projects/{project_id}/files', json=file_data)
        assert response.status_code == 201
        file_info = response.json()
        assert file_info['path'] == 'src/factory.py'
        
        # Step 2: Update file content
        updated_content = {
            'content': 'class Factory:\n    def create_object(self):\n        return Object()'
        }
        
        response = test_client.put(f'/api/projects/{project_id}/files/src/factory.py', json=updated_content)
        assert response.status_code == 200
        
        # Step 3: Retrieve file content
        response = test_client.get(f'/api/projects/{project_id}/files/src/factory.py')
        assert response.status_code == 200
        file_content = response.json()
        assert 'create_object' in file_content['content']
        
        # Step 4: List all project files
        response = test_client.get(f'/api/projects/{project_id}/files')
        assert response.status_code == 200
        files = response.json()
        assert len(files) > 0
        assert any(f['path'] == 'src/factory.py' for f in files)
        
        # Step 5: Delete file
        response = test_client.delete(f'/api/projects/{project_id}/files/src/factory.py')
        assert response.status_code == 204
        
        # Verify file is deleted
        response = test_client.get(f'/api/projects/{project_id}/files/src/factory.py')
        assert response.status_code == 404

    def test_coach_agent_interaction_workflow(self, test_client, mock_github_client, mock_mcp_client, mock_llm_provider):
        """Test AI coach agent interactions and context management."""
        
        # Create project with reference snippets
        project_data = {
            'name': 'Coach Interaction Test',
            'architecture_topic': 'Design Patterns',
            'target_repository': 'https://github.com/test/test-repo',
            'implementation_language': 'Python'
        }
        
        response = test_client.post('/api/projects', json=project_data)
        assert response.status_code == 201
        project_id = response.json()['id']
        
        # Step 1: Ask coach a question
        question_data = {
            'question': 'How does the factory pattern work?',
            'context': {
                'current_file': 'src/factory.py',
                'selected_task': 1
            }
        }
        
        response = test_client.post(f'/api/projects/{project_id}/coach/ask', json=question_data)
        assert response.status_code == 200
        coach_response = response.json()
        assert 'response' in coach_response
        assert 'factory pattern' in coach_response['response'].lower()
        
        # Verify LLM provider was called for coach response
        mock_llm_provider.generate_coach_response.assert_called()
        
        # Step 2: Get chat history
        response = test_client.get(f'/api/projects/{project_id}/coach/history')
        assert response.status_code == 200
        history = response.json()
        assert len(history) > 0
        assert history[0]['question'] == 'How does the factory pattern work?'

    def test_error_scenarios_and_recovery(self, test_client):
        """Test error handling and recovery mechanisms."""
        
        # Test 1: Invalid repository URL
        invalid_project_data = {
            'name': 'Invalid Repo Test',
            'architecture_topic': 'Design Patterns',
            'target_repository': 'invalid-url',
            'implementation_language': 'Python'
        }
        
        with patch('app.github_client.GitHubClient') as mock_github:
            mock_instance = Mock()
            mock_instance.validate_repository.return_value = {'valid': False, 'error': 'Invalid URL format'}
            mock_github.return_value = mock_instance
            
            response = test_client.post('/api/projects', json=invalid_project_data)
            assert response.status_code == 400
            error_response = response.json()
            assert 'Invalid URL format' in error_response['detail']
        
        # Test 2: Non-existent project access
        response = test_client.get('/api/projects/999999')
        assert response.status_code == 404
        
        # Test 3: File operation on non-existent project
        file_data = {'path': 'test.py', 'content': 'test'}
        response = test_client.post('/api/projects/999999/files', json=file_data)
        assert response.status_code == 404
        
        # Test 4: Coach question without project context
        question_data = {'question': 'Test question'}
        response = test_client.post('/api/projects/999999/coach/ask', json=question_data)
        assert response.status_code == 404

    def test_github_api_rate_limiting_scenario(self, test_client):
        """Test GitHub API rate limiting handling."""
        
        with patch('app.github_client.GitHubClient') as mock_github:
            mock_instance = Mock()
            # Simulate rate limit error
            mock_instance.validate_repository.side_effect = Exception("API rate limit exceeded")
            mock_github.return_value = mock_instance
            
            project_data = {
                'name': 'Rate Limit Test',
                'architecture_topic': 'Design Patterns',
                'target_repository': 'https://github.com/test/test-repo',
                'implementation_language': 'Python'
            }
            
            response = test_client.post('/api/projects', json=project_data)
            # Should handle rate limiting gracefully
            assert response.status_code in [429, 503]  # Rate limited or service unavailable

    def test_concurrent_project_operations(self, test_client, mock_github_client, mock_mcp_client, mock_llm_provider):
        """Test concurrent operations on multiple projects."""
        
        # Create multiple projects concurrently
        project_data_1 = {
            'name': 'Concurrent Test 1',
            'architecture_topic': 'Design Patterns',
            'target_repository': 'https://github.com/test/repo1',
            'implementation_language': 'Python'
        }
        
        project_data_2 = {
            'name': 'Concurrent Test 2',
            'architecture_topic': 'Microservices',
            'target_repository': 'https://github.com/test/repo2',
            'implementation_language': 'TypeScript'
        }
        
        # Create projects
        response1 = test_client.post('/api/projects', json=project_data_1)
        response2 = test_client.post('/api/projects', json=project_data_2)
        
        assert response1.status_code == 201
        assert response2.status_code == 201
        
        project1_id = response1.json()['id']
        project2_id = response2.json()['id']
        
        # Perform concurrent file operations
        file_data_1 = {'path': 'src/pattern.py', 'content': 'class Pattern: pass'}
        file_data_2 = {'path': 'src/service.ts', 'content': 'class Service {}'}
        
        response1 = test_client.post(f'/api/projects/{project1_id}/files', json=file_data_1)
        response2 = test_client.post(f'/api/projects/{project2_id}/files', json=file_data_2)
        
        assert response1.status_code == 201
        assert response2.status_code == 201
        
        # Verify projects remain isolated
        files1 = test_client.get(f'/api/projects/{project1_id}/files').json()
        files2 = test_client.get(f'/api/projects/{project2_id}/files').json()
        
        assert any(f['path'] == 'src/pattern.py' for f in files1)
        assert any(f['path'] == 'src/service.ts' for f in files2)
        assert not any(f['path'] == 'src/service.ts' for f in files1)
        assert not any(f['path'] == 'src/pattern.py' for f in files2)

    def test_data_persistence_across_sessions(self, test_client, mock_github_client, mock_mcp_client, mock_llm_provider):
        """Test that data persists correctly across different sessions."""
        
        # Create project and files
        project_data = {
            'name': 'Persistence Test',
            'architecture_topic': 'Data Persistence',
            'target_repository': 'https://github.com/test/test-repo',
            'implementation_language': 'Python'
        }
        
        response = test_client.post('/api/projects', json=project_data)
        assert response.status_code == 201
        project_id = response.json()['id']
        
        # Create multiple files
        files_to_create = [
            {'path': 'src/model.py', 'content': 'class Model: pass'},
            {'path': 'src/repository.py', 'content': 'class Repository: pass'},
            {'path': 'tests/test_model.py', 'content': 'def test_model(): pass'}
        ]
        
        for file_data in files_to_create:
            response = test_client.post(f'/api/projects/{project_id}/files', json=file_data)
            assert response.status_code == 201
        
        # Simulate session restart by creating new client
        new_client = TestClient(app)
        
        # Verify project still exists
        response = new_client.get(f'/api/projects/{project_id}')
        assert response.status_code == 200
        project = response.json()
        assert project['name'] == 'Persistence Test'
        
        # Verify files still exist
        response = new_client.get(f'/api/projects/{project_id}/files')
        assert response.status_code == 200
        files = response.json()
        assert len(files) == 3
        
        created_paths = {f['path'] for f in files}
        expected_paths = {'src/model.py', 'src/repository.py', 'tests/test_model.py'}
        assert created_paths == expected_paths

    def test_system_component_integration(self, test_client, mock_github_client, mock_mcp_client, mock_llm_provider):
        """Test integration between all major system components."""
        
        # This test verifies that all components work together correctly
        project_data = {
            'name': 'Integration Test',
            'architecture_topic': 'System Integration',
            'target_repository': 'https://github.com/test/integration-repo',
            'implementation_language': 'Python'
        }
        
        # Step 1: Project creation (involves GitHub client)
        response = test_client.post('/api/projects', json=project_data)
        assert response.status_code == 201
        project_id = response.json()['id']
        
        # Step 2: Repository analysis (involves MCP client)
        mock_mcp_client.analyze_repository.return_value = {
            'relevant_files': ['src/integration.py', 'src/components.py'],
            'patterns': ['Observer Pattern', 'Command Pattern'],
            'complexity_score': 0.8
        }
        
        # Step 3: Specification generation (involves LLM provider)
        response = test_client.get(f'/api/projects/{project_id}/spec')
        assert response.status_code == 200
        
        # Step 4: File management (involves database)
        file_data = {'path': 'src/integration.py', 'content': 'class Integration: pass'}
        response = test_client.post(f'/api/projects/{project_id}/files', json=file_data)
        assert response.status_code == 201
        
        # Step 5: Coach interaction (involves LLM provider + context)
        question_data = {'question': 'Explain the observer pattern'}
        response = test_client.post(f'/api/projects/{project_id}/coach/ask', json=question_data)
        assert response.status_code == 200
        
        # Verify all components were called
        mock_github_client.validate_repository.assert_called()
        mock_mcp_client.analyze_repository.assert_called()
        mock_llm_provider.generate_specification.assert_called()
        mock_llm_provider.generate_coach_response.assert_called()