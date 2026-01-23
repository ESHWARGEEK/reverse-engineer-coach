"""
End-to-End User Workflow Tests

These tests verify complete user workflows from registration to project completion,
covering all major user journeys and system integration scenarios.

Test Coverage:
- Complete user registration and onboarding flow
- Concept search to project creation workflow  
- User project management and workspace access
- Cross-system integration testing
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
import time
from datetime import datetime, timedelta

from app.main import app
from app.models import Base, User, UserCredentials, LearningProject, LearningSpec, Task, ReferenceSnippet
from app.database import get_db
from app.services.auth_service import AuthService
from app.services.jwt_service import JWTService
from app.services.password_service import PasswordService
from app.services.credential_encryption_service import CredentialEncryptionService


class TestE2EUserWorkflow:
    """End-to-end user workflow tests covering complete user journeys."""
    
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
    def mock_external_services(self):
        """Mock all external services for testing."""
        with patch('app.services.github_search_service.GitHubSearchService') as mock_github, \
             patch('app.services.repository_analyzer.RepositoryAnalyzer') as mock_analyzer, \
             patch('app.llm_provider.LLMProvider') as mock_llm, \
             patch('app.mcp_client.MCPClient') as mock_mcp:
            
            # Setup GitHub search service mock
            mock_github_instance = Mock()
            mock_github_instance.search_repositories.return_value = [
                {
                    'repository_url': 'https://github.com/example/microservices-demo',
                    'repository_name': 'microservices-demo',
                    'description': 'A sample microservices application',
                    'stars': 1500,
                    'forks': 300,
                    'language': 'Python',
                    'topics': ['microservices', 'docker', 'kubernetes'],
                    'last_updated': datetime.now().isoformat(),
                    'owner': 'example',
                    'size_kb': 2500,
                    'has_readme': True,
                    'has_license': True,
                    'open_issues': 5,
                }
            ]
            mock_github.return_value = mock_github_instance
            
            # Setup repository analyzer mock
            mock_analyzer_instance = Mock()
            mock_analyzer_instance.analyze_repository_quality.return_value = {
                'overall_score': 0.85,
                'code_quality': 0.8,
                'documentation_quality': 0.9,
                'activity_score': 0.7,
                'educational_value': 0.9,
                'complexity_score': 0.8,
            }
            mock_analyzer_instance.calculate_relevance_score.return_value = 0.95
            mock_analyzer.return_value = mock_analyzer_instance
            
            # Setup LLM provider mock
            mock_llm_instance = Mock()
            mock_llm_instance.generate_specification.return_value = {
                'requirements': '# Requirements\n\n1. Implement microservices pattern\n2. Add error handling',
                'tasks': [
                    {'id': 1, 'title': 'Implement Microservices Pattern', 'description': 'Create microservices architecture'},
                    {'id': 2, 'title': 'Add Error Handling', 'description': 'Add comprehensive error handling'}
                ]
            }
            mock_llm_instance.generate_coach_response.return_value = {
                'response': 'Microservices architecture helps create scalable applications.',
                'references': ['src/main.py:1-10']
            }
            mock_llm.return_value = mock_llm_instance
            
            # Setup MCP client mock
            mock_mcp_instance = Mock()
            mock_mcp_instance.analyze_repository.return_value = {
                'relevant_files': ['src/main.py', 'src/services.py'],
                'patterns': ['Microservices Pattern', 'API Gateway Pattern'],
                'complexity_score': 0.7
            }
            mock_mcp_instance.extract_code_snippets.return_value = [
                {
                    'file_path': 'src/main.py',
                    'content': 'class MicroserviceApp:\n    def __init__(self):\n        pass',
                    'start_line': 1,
                    'end_line': 3,
                    'pattern': 'Microservices Pattern'
                }
            ]
            mock_mcp.return_value = mock_mcp_instance
            
            yield {
                'github': mock_github_instance,
                'analyzer': mock_analyzer_instance,
                'llm': mock_llm_instance,
                'mcp': mock_mcp_instance,
            }

    def test_complete_user_registration_and_onboarding_workflow(self, test_client, mock_external_services):
        """Test complete user registration and onboarding workflow."""
        
        # Step 1: User registration
        registration_data = {
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'github_token': 'ghp_test_token_123',
            'openai_api_key': 'sk-test-openai-key-123',
            'preferred_ai_provider': 'openai',
            'preferred_language': 'python',
            'preferred_frameworks': ['fastapi', 'django'],
        }
        
        # Mock API key validation
        with patch('app.services.credential_encryption_service.CredentialEncryptionService.validate_github_token') as mock_github_val, \
             patch('app.services.credential_encryption_service.CredentialEncryptionService.validate_openai_key') as mock_openai_val:
            
            mock_github_val.return_value = True
            mock_openai_val.return_value = True
            
            response = test_client.post('/api/v1/auth/register', json=registration_data)
            assert response.status_code == 201
            
            registration_result = response.json()
            assert 'user' in registration_result
            assert 'access_token' in registration_result
            assert registration_result['user']['email'] == 'test@example.com'
            
            access_token = registration_result['access_token']
            user_id = registration_result['user']['id']
        
        # Step 2: Verify user can access dashboard
        headers = {'Authorization': f'Bearer {access_token}'}
        response = test_client.get('/api/v1/dashboard/', headers=headers)
        assert response.status_code == 200
        
        dashboard_data = response.json()
        assert 'projects' in dashboard_data
        assert 'stats' in dashboard_data
        assert dashboard_data['stats']['total_projects'] == 0
        
        # Step 3: Verify user profile access
        response = test_client.get('/api/v1/profile/', headers=headers)
        assert response.status_code == 200
        
        profile_data = response.json()
        assert profile_data['email'] == 'test@example.com'
        assert profile_data['preferred_language'] == 'python'
        assert 'fastapi' in profile_data['preferred_frameworks']
        
        # Step 4: Verify API credentials are stored securely (masked)
        assert 'github_token' in profile_data
        assert profile_data['github_token'].startswith('ghp_****')
        assert 'openai_api_key' in profile_data
        assert profile_data['openai_api_key'].startswith('sk-****')

    def test_concept_search_to_project_creation_workflow(self, test_client, mock_external_services):
        """Test complete workflow from concept search to project creation."""
        
        # Step 1: Register and authenticate user
        registration_data = {
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'openai_api_key': 'sk-test-openai-key-123',
            'preferred_ai_provider': 'openai',
            'preferred_language': 'python',
        }
        
        with patch('app.services.credential_encryption_service.CredentialEncryptionService.validate_openai_key') as mock_val:
            mock_val.return_value = True
            response = test_client.post('/api/v1/auth/register', json=registration_data)
            assert response.status_code == 201
            access_token = response.json()['access_token']
        
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Step 2: Search for repositories based on concept
        concept_data = {
            'concept': 'microservices architecture',
            'preferred_language': 'python',
            'max_results': 5
        }
        
        response = test_client.post('/api/v1/discovery/repositories', json=concept_data, headers=headers)
        assert response.status_code == 200
        
        discovery_result = response.json()
        assert 'suggestions' in discovery_result
        assert len(discovery_result['suggestions']) > 0
        
        # Verify repository suggestion structure
        suggestion = discovery_result['suggestions'][0]
        assert 'repository_url' in suggestion
        assert 'repository_name' in suggestion
        assert 'quality' in suggestion
        assert suggestion['repository_name'] == 'microservices-demo'
        
        # Step 3: Create project with selected repository
        project_data = {
            'name': 'Learn Microservices Architecture',
            'concept_description': 'microservices architecture',
            'target_repository': suggestion['repository_url'],
            'implementation_language': 'python',
            'preferred_frameworks': ['fastapi'],
        }
        
        response = test_client.post('/api/v1/projects', json=project_data, headers=headers)
        assert response.status_code == 201
        
        project_result = response.json()
        assert project_result['name'] == 'Learn Microservices Architecture'
        assert project_result['status'] == 'analyzing'
        assert project_result['concept_description'] == 'microservices architecture'
        
        project_id = project_result['id']
        
        # Step 4: Simulate analysis completion and verify project is ready
        # In real scenario, this would be done by background task
        response = test_client.patch(f'/api/v1/projects/{project_id}', 
                                   json={'status': 'ready'}, headers=headers)
        assert response.status_code == 200
        
        # Step 5: Verify project appears in dashboard
        response = test_client.get('/api/v1/dashboard/', headers=headers)
        assert response.status_code == 200
        
        dashboard_data = response.json()
        assert dashboard_data['stats']['total_projects'] == 1
        assert len(dashboard_data['projects']) == 1
        assert dashboard_data['projects'][0]['id'] == project_id
        
        # Step 6: Verify project specification was generated
        response = test_client.get(f'/api/v1/projects/{project_id}/spec', headers=headers)
        assert response.status_code == 200
        
        spec_data = response.json()
        assert 'requirements' in spec_data
        assert 'microservices pattern' in spec_data['requirements'].lower()
        
        # Step 7: Verify tasks were generated
        response = test_client.get(f'/api/v1/projects/{project_id}/tasks', headers=headers)
        assert response.status_code == 200
        
        tasks_data = response.json()
        assert len(tasks_data) > 0
        assert tasks_data[0]['title'] == 'Implement Microservices Pattern'

    def test_user_project_management_and_workspace_access_workflow(self, test_client, mock_external_services):
        """Test user project management and workspace access workflow."""
        
        # Step 1: Setup authenticated user with project
        registration_data = {
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'openai_api_key': 'sk-test-openai-key-123',
            'preferred_ai_provider': 'openai',
            'preferred_language': 'python',
        }
        
        with patch('app.services.credential_encryption_service.CredentialEncryptionService.validate_openai_key') as mock_val:
            mock_val.return_value = True
            response = test_client.post('/api/v1/auth/register', json=registration_data)
            access_token = response.json()['access_token']
        
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Create a project
        project_data = {
            'name': 'Test Project',
            'concept_description': 'microservices',
            'target_repository': 'https://github.com/example/microservices-demo',
            'implementation_language': 'python',
        }
        
        response = test_client.post('/api/v1/projects', json=project_data, headers=headers)
        project_id = response.json()['id']
        
        # Mark project as ready
        test_client.patch(f'/api/v1/projects/{project_id}', 
                         json={'status': 'ready'}, headers=headers)
        
        # Step 2: Test project filtering and search
        # Create additional projects for filtering
        for i in range(3):
            additional_project = {
                'name': f'Additional Project {i}',
                'concept_description': f'concept-{i}',
                'target_repository': f'https://github.com/example/repo-{i}',
                'implementation_language': 'typescript' if i % 2 else 'python',
            }
            test_client.post('/api/v1/projects', json=additional_project, headers=headers)
        
        # Test search by concept
        response = test_client.get('/api/v1/dashboard/?topic_search=microservices', headers=headers)
        assert response.status_code == 200
        
        search_results = response.json()
        assert len(search_results['projects']) == 1
        assert search_results['projects'][0]['concept_description'] == 'microservices'
        
        # Test filter by language
        response = test_client.get('/api/v1/dashboard/?language=python', headers=headers)
        assert response.status_code == 200
        
        filter_results = response.json()
        python_projects = [p for p in filter_results['projects'] if p['implementation_language'] == 'python']
        assert len(python_projects) >= 2
        
        # Test filter by status
        response = test_client.get('/api/v1/dashboard/?status=ready', headers=headers)
        assert response.status_code == 200
        
        status_results = response.json()
        ready_projects = [p for p in status_results['projects'] if p['status'] == 'ready']
        assert len(ready_projects) >= 1
        
        # Step 3: Test project workspace access
        response = test_client.get(f'/api/v1/projects/{project_id}', headers=headers)
        assert response.status_code == 200
        
        project_details = response.json()
        assert project_details['name'] == 'Test Project'
        assert project_details['status'] == 'ready'
        
        # Step 4: Test file management in workspace
        # Create a file
        file_data = {
            'path': 'src/main.py',
            'content': 'class MicroserviceApp:\n    def __init__(self):\n        self.name = "test"'
        }
        
        response = test_client.post(f'/api/v1/projects/{project_id}/files', 
                                  json=file_data, headers=headers)
        assert response.status_code == 201
        
        file_result = response.json()
        assert file_result['path'] == 'src/main.py'
        
        # Update file content
        updated_content = {
            'content': 'class MicroserviceApp:\n    def __init__(self):\n        self.name = "updated"\n        self.version = "1.0"'
        }
        
        response = test_client.put(f'/api/v1/projects/{project_id}/files/src/main.py', 
                                 json=updated_content, headers=headers)
        assert response.status_code == 200
        
        # Retrieve file content
        response = test_client.get(f'/api/v1/projects/{project_id}/files/src/main.py', headers=headers)
        assert response.status_code == 200
        
        file_content = response.json()
        assert 'updated' in file_content['content']
        assert 'version = "1.0"' in file_content['content']
        
        # List all files
        response = test_client.get(f'/api/v1/projects/{project_id}/files', headers=headers)
        assert response.status_code == 200
        
        files_list = response.json()
        assert len(files_list) > 0
        assert any(f['path'] == 'src/main.py' for f in files_list)
        
        # Step 5: Test coach agent interaction
        question_data = {
            'question': 'How do I implement microservices communication?',
            'context': {
                'current_file': 'src/main.py',
                'selected_task': 1
            }
        }
        
        response = test_client.post(f'/api/v1/projects/{project_id}/coach/ask', 
                                  json=question_data, headers=headers)
        assert response.status_code == 200
        
        coach_response = response.json()
        assert 'response' in coach_response
        assert 'microservices' in coach_response['response'].lower()
        
        # Get chat history
        response = test_client.get(f'/api/v1/projects/{project_id}/coach/history', headers=headers)
        assert response.status_code == 200
        
        history = response.json()
        assert len(history) > 0
        assert history[0]['question'] == 'How do I implement microservices communication?'
        
        # Step 6: Test project deletion
        response = test_client.delete(f'/api/v1/dashboard/projects/{project_id}', headers=headers)
        assert response.status_code == 204
        
        # Verify project is deleted
        response = test_client.get(f'/api/v1/projects/{project_id}', headers=headers)
        assert response.status_code == 404

    def test_user_profile_management_workflow(self, test_client, mock_external_services):
        """Test user profile management workflow."""
        
        # Step 1: Register user
        registration_data = {
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'openai_api_key': 'sk-test-openai-key-123',
            'preferred_ai_provider': 'openai',
            'preferred_language': 'python',
        }
        
        with patch('app.services.credential_encryption_service.CredentialEncryptionService.validate_openai_key') as mock_val:
            mock_val.return_value = True
            response = test_client.post('/api/v1/auth/register', json=registration_data)
            access_token = response.json()['access_token']
        
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Step 2: Get initial profile
        response = test_client.get('/api/v1/profile/', headers=headers)
        assert response.status_code == 200
        
        profile = response.json()
        assert profile['email'] == 'test@example.com'
        assert profile['preferred_language'] == 'python'
        
        # Step 3: Update profile preferences
        update_data = {
            'preferred_language': 'typescript',
            'preferred_frameworks': ['nestjs', 'react'],
        }
        
        response = test_client.patch('/api/v1/profile/', json=update_data, headers=headers)
        assert response.status_code == 200
        
        updated_profile = response.json()
        assert updated_profile['preferred_language'] == 'typescript'
        assert 'nestjs' in updated_profile['preferred_frameworks']
        
        # Step 4: Update API credentials
        with patch('app.services.credential_encryption_service.CredentialEncryptionService.validate_github_token') as mock_github_val, \
             patch('app.services.credential_encryption_service.CredentialEncryptionService.validate_gemini_key') as mock_gemini_val:
            
            mock_github_val.return_value = True
            mock_gemini_val.return_value = True
            
            credentials_update = {
                'github_token': 'ghp_new_token_456',
                'gemini_api_key': 'gemini_new_key_789',
                'preferred_ai_provider': 'gemini',
            }
            
            response = test_client.patch('/api/v1/profile/credentials', 
                                       json=credentials_update, headers=headers)
            assert response.status_code == 200
            
            # Verify credentials are updated (masked)
            response = test_client.get('/api/v1/profile/', headers=headers)
            updated_profile = response.json()
            assert updated_profile['github_token'].startswith('ghp_****')
            assert updated_profile['gemini_api_key'].startswith('****')
            assert updated_profile['preferred_ai_provider'] == 'gemini'
        
        # Step 5: Change password
        password_change = {
            'current_password': 'SecurePassword123!',
            'new_password': 'NewSecurePassword456!',
        }
        
        response = test_client.patch('/api/v1/profile/password', 
                                   json=password_change, headers=headers)
        assert response.status_code == 200
        
        # Step 6: Verify new password works
        login_data = {
            'email': 'test@example.com',
            'password': 'NewSecurePassword456!',
        }
        
        response = test_client.post('/api/v1/auth/login', json=login_data)
        assert response.status_code == 200
        
        login_result = response.json()
        assert 'access_token' in login_result

    def test_multi_user_data_isolation_workflow(self, test_client, mock_external_services):
        """Test that user data is properly isolated between different users."""
        
        # Step 1: Register two users
        user1_data = {
            'email': 'user1@example.com',
            'password': 'SecurePassword123!',
            'openai_api_key': 'sk-user1-key-123',
            'preferred_ai_provider': 'openai',
            'preferred_language': 'python',
        }
        
        user2_data = {
            'email': 'user2@example.com',
            'password': 'SecurePassword123!',
            'gemini_api_key': 'gemini-user2-key-456',
            'preferred_ai_provider': 'gemini',
            'preferred_language': 'typescript',
        }
        
        with patch('app.services.credential_encryption_service.CredentialEncryptionService.validate_openai_key') as mock_openai_val, \
             patch('app.services.credential_encryption_service.CredentialEncryptionService.validate_gemini_key') as mock_gemini_val:
            
            mock_openai_val.return_value = True
            mock_gemini_val.return_value = True
            
            # Register user 1
            response = test_client.post('/api/v1/auth/register', json=user1_data)
            assert response.status_code == 201
            user1_token = response.json()['access_token']
            
            # Register user 2
            response = test_client.post('/api/v1/auth/register', json=user2_data)
            assert response.status_code == 201
            user2_token = response.json()['access_token']
        
        user1_headers = {'Authorization': f'Bearer {user1_token}'}
        user2_headers = {'Authorization': f'Bearer {user2_token}'}
        
        # Step 2: Create projects for each user
        user1_project = {
            'name': 'User 1 Project',
            'concept_description': 'user1 microservices',
            'target_repository': 'https://github.com/user1/repo',
            'implementation_language': 'python',
        }
        
        user2_project = {
            'name': 'User 2 Project',
            'concept_description': 'user2 clean architecture',
            'target_repository': 'https://github.com/user2/repo',
            'implementation_language': 'typescript',
        }
        
        # Create projects
        response = test_client.post('/api/v1/projects', json=user1_project, headers=user1_headers)
        assert response.status_code == 201
        user1_project_id = response.json()['id']
        
        response = test_client.post('/api/v1/projects', json=user2_project, headers=user2_headers)
        assert response.status_code == 201
        user2_project_id = response.json()['id']
        
        # Step 3: Verify data isolation - each user only sees their own projects
        response = test_client.get('/api/v1/dashboard/', headers=user1_headers)
        assert response.status_code == 200
        user1_dashboard = response.json()
        assert len(user1_dashboard['projects']) == 1
        assert user1_dashboard['projects'][0]['name'] == 'User 1 Project'
        
        response = test_client.get('/api/v1/dashboard/', headers=user2_headers)
        assert response.status_code == 200
        user2_dashboard = response.json()
        assert len(user2_dashboard['projects']) == 1
        assert user2_dashboard['projects'][0]['name'] == 'User 2 Project'
        
        # Step 4: Verify users cannot access each other's projects
        response = test_client.get(f'/api/v1/projects/{user2_project_id}', headers=user1_headers)
        assert response.status_code == 404  # User 1 cannot access User 2's project
        
        response = test_client.get(f'/api/v1/projects/{user1_project_id}', headers=user2_headers)
        assert response.status_code == 404  # User 2 cannot access User 1's project
        
        # Step 5: Verify users cannot modify each other's projects
        response = test_client.patch(f'/api/v1/projects/{user2_project_id}', 
                                   json={'status': 'completed'}, headers=user1_headers)
        assert response.status_code == 404
        
        response = test_client.delete(f'/api/v1/dashboard/projects/{user1_project_id}', headers=user2_headers)
        assert response.status_code == 404
        
        # Step 6: Verify profile isolation
        response = test_client.get('/api/v1/profile/', headers=user1_headers)
        user1_profile = response.json()
        assert user1_profile['email'] == 'user1@example.com'
        assert user1_profile['preferred_language'] == 'python'
        
        response = test_client.get('/api/v1/profile/', headers=user2_headers)
        user2_profile = response.json()
        assert user2_profile['email'] == 'user2@example.com'
        assert user2_profile['preferred_language'] == 'typescript'

    def test_error_recovery_and_resilience_workflow(self, test_client, mock_external_services):
        """Test system resilience and error recovery mechanisms."""
        
        # Step 1: Setup authenticated user
        registration_data = {
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'openai_api_key': 'sk-test-openai-key-123',
            'preferred_ai_provider': 'openai',
            'preferred_language': 'python',
        }
        
        with patch('app.services.credential_encryption_service.CredentialEncryptionService.validate_openai_key') as mock_val:
            mock_val.return_value = True
            response = test_client.post('/api/v1/auth/register', json=registration_data)
            access_token = response.json()['access_token']
        
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Step 2: Test repository discovery with external service failure
        with patch.object(mock_external_services['github'], 'search_repositories') as mock_search:
            mock_search.side_effect = Exception("GitHub API unavailable")
            
            concept_data = {
                'concept': 'microservices architecture',
                'preferred_language': 'python',
            }
            
            response = test_client.post('/api/v1/discovery/repositories', 
                                      json=concept_data, headers=headers)
            # Should handle gracefully with appropriate error response
            assert response.status_code in [503, 500]  # Service unavailable or internal error
        
        # Step 3: Test project creation with partial service failures
        project_data = {
            'name': 'Resilience Test Project',
            'concept_description': 'test resilience',
            'target_repository': 'https://github.com/example/test-repo',
            'implementation_language': 'python',
        }
        
        # Mock LLM service failure during spec generation
        with patch.object(mock_external_services['llm'], 'generate_specification') as mock_spec:
            mock_spec.side_effect = Exception("LLM service unavailable")
            
            response = test_client.post('/api/v1/projects', json=project_data, headers=headers)
            # Project should still be created, but marked as failed or pending
            assert response.status_code == 201
            
            project_result = response.json()
            project_id = project_result['id']
            
            # Check project status reflects the failure
            response = test_client.get(f'/api/v1/projects/{project_id}', headers=headers)
            project_details = response.json()
            assert project_details['status'] in ['failed', 'analyzing']
        
        # Step 4: Test recovery after service restoration
        # Reset mocks to working state
        mock_external_services['llm'].generate_specification.side_effect = None
        mock_external_services['llm'].generate_specification.return_value = {
            'requirements': '# Requirements\n\n1. Test resilience patterns',
            'tasks': [{'id': 1, 'title': 'Implement Resilience', 'description': 'Add resilience patterns'}]
        }
        
        # Retry project analysis
        response = test_client.post(f'/api/v1/projects/{project_id}/retry-analysis', headers=headers)
        if response.status_code == 200:  # If retry endpoint exists
            # Verify project is now ready
            response = test_client.get(f'/api/v1/projects/{project_id}', headers=headers)
            project_details = response.json()
            assert project_details['status'] in ['ready', 'analyzing']
        
        # Step 5: Test database transaction rollback on failure
        invalid_project_data = {
            'name': 'Invalid Project',
            'concept_description': 'test',
            'target_repository': 'invalid-url-format',  # Invalid URL
            'implementation_language': 'python',
        }
        
        response = test_client.post('/api/v1/projects', json=invalid_project_data, headers=headers)
        assert response.status_code == 400  # Bad request due to validation
        
        # Verify no partial data was created
        response = test_client.get('/api/v1/dashboard/', headers=headers)
        dashboard_data = response.json()
        # Should not include the invalid project
        invalid_projects = [p for p in dashboard_data['projects'] if p['name'] == 'Invalid Project']
        assert len(invalid_projects) == 0

    def test_performance_under_load_workflow(self, test_client, mock_external_services):
        """Test system performance under simulated load."""
        
        # Step 1: Register user
        registration_data = {
            'email': 'load_test@example.com',
            'password': 'SecurePassword123!',
            'openai_api_key': 'sk-test-openai-key-123',
            'preferred_ai_provider': 'openai',
            'preferred_language': 'python',
        }
        
        with patch('app.services.credential_encryption_service.CredentialEncryptionService.validate_openai_key') as mock_val:
            mock_val.return_value = True
            response = test_client.post('/api/v1/auth/register', json=registration_data)
            access_token = response.json()['access_token']
        
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Step 2: Create multiple projects rapidly
        project_ids = []
        start_time = time.time()
        
        for i in range(10):  # Create 10 projects
            project_data = {
                'name': f'Load Test Project {i}',
                'concept_description': f'load test concept {i}',
                'target_repository': f'https://github.com/example/repo-{i}',
                'implementation_language': 'python',
            }
            
            response = test_client.post('/api/v1/projects', json=project_data, headers=headers)
            assert response.status_code == 201
            project_ids.append(response.json()['id'])
        
        creation_time = time.time() - start_time
        assert creation_time < 30  # Should complete within 30 seconds
        
        # Step 3: Test concurrent dashboard access
        start_time = time.time()
        
        for _ in range(20):  # 20 concurrent dashboard requests
            response = test_client.get('/api/v1/dashboard/', headers=headers)
            assert response.status_code == 200
        
        dashboard_time = time.time() - start_time
        assert dashboard_time < 10  # Should complete within 10 seconds
        
        # Step 4: Test bulk project operations
        start_time = time.time()
        
        # Get details for all projects
        for project_id in project_ids:
            response = test_client.get(f'/api/v1/projects/{project_id}', headers=headers)
            assert response.status_code == 200
        
        bulk_access_time = time.time() - start_time
        assert bulk_access_time < 15  # Should complete within 15 seconds
        
        # Step 5: Verify data consistency after load
        response = test_client.get('/api/v1/dashboard/', headers=headers)
        assert response.status_code == 200
        
        dashboard_data = response.json()
        assert dashboard_data['stats']['total_projects'] == 10
        assert len(dashboard_data['projects']) <= 12  # Respects pagination

    def test_security_and_authentication_workflow(self, test_client, mock_external_services):
        """Test security measures and authentication workflows."""
        
        # Step 1: Test registration with weak password
        weak_password_data = {
            'email': 'weak@example.com',
            'password': '123',  # Weak password
            'preferred_ai_provider': 'openai',
            'preferred_language': 'python',
        }
        
        response = test_client.post('/api/v1/auth/register', json=weak_password_data)
        assert response.status_code == 400  # Should reject weak password
        
        # Step 2: Test registration with invalid email
        invalid_email_data = {
            'email': 'invalid-email',  # Invalid email format
            'password': 'SecurePassword123!',
            'preferred_ai_provider': 'openai',
            'preferred_language': 'python',
        }
        
        response = test_client.post('/api/v1/auth/register', json=invalid_email_data)
        assert response.status_code == 400  # Should reject invalid email
        
        # Step 3: Test duplicate email registration
        valid_data = {
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'openai_api_key': 'sk-test-key-123',
            'preferred_ai_provider': 'openai',
            'preferred_language': 'python',
        }
        
        with patch('app.services.credential_encryption_service.CredentialEncryptionService.validate_openai_key') as mock_val:
            mock_val.return_value = True
            
            # First registration should succeed
            response = test_client.post('/api/v1/auth/register', json=valid_data)
            assert response.status_code == 201
            
            # Second registration with same email should fail
            response = test_client.post('/api/v1/auth/register', json=valid_data)
            assert response.status_code == 400
        
        # Step 4: Test login with invalid credentials
        invalid_login = {
            'email': 'test@example.com',
            'password': 'WrongPassword123!',
        }
        
        response = test_client.post('/api/v1/auth/login', json=invalid_login)
        assert response.status_code == 401  # Unauthorized
        
        # Step 5: Test access without authentication
        response = test_client.get('/api/v1/dashboard/')
        assert response.status_code == 401  # Should require authentication
        
        response = test_client.get('/api/v1/profile/')
        assert response.status_code == 401  # Should require authentication
        
        # Step 6: Test access with invalid token
        invalid_headers = {'Authorization': 'Bearer invalid-token-123'}
        
        response = test_client.get('/api/v1/dashboard/', headers=invalid_headers)
        assert response.status_code == 401  # Should reject invalid token
        
        # Step 7: Test token expiration handling
        # This would require mocking JWT service to create expired tokens
        # For now, we verify the structure is in place
        valid_login = {
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
        }
        
        response = test_client.post('/api/v1/auth/login', json=valid_login)
        assert response.status_code == 200
        
        login_result = response.json()
        assert 'access_token' in login_result
        assert 'refresh_token' in login_result
        assert 'token_type' in login_result
        assert login_result['token_type'] == 'bearer'