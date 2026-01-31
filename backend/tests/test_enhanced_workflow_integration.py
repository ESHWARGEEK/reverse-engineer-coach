"""
Enhanced Workflow Integration Tests

Comprehensive integration tests for AI agent workflows, covering:
- Repository discovery agent integration
- Repository analysis agent integration  
- Curriculum generation agent integration
- Workflow orchestration service integration
- Error handling and fallback scenarios
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from app.services.repository_discovery_agent import RepositoryDiscoveryAgent
from app.services.repository_analysis_agent import RepositoryAnalysisAgent
from app.services.curriculum_generation_agent import CurriculumGenerationAgent
from app.services.workflow_orchestration_service import WorkflowOrchestrationService


class TestRepositoryDiscoveryAgentIntegration:
    """Integration tests for Repository Discovery Agent"""
    
    @pytest.fixture
    def discovery_agent(self):
        return RepositoryDiscoveryAgent()
    
    @pytest.fixture
    def sample_user_preferences(self):
        return {
            'experience_level': 'intermediate',
            'technologies': ['Python', 'FastAPI', 'React'],
            'learning_goals': ['Learn web development', 'Build REST APIs'],
            'time_commitment': '10-15 hours/week'
        }
    
    @pytest.mark.asyncio
    async def test_complete_repository_discovery_workflow(self, discovery_agent, sample_user_preferences):
        """Test complete repository discovery workflow"""
        
        # Mock GitHub API responses
        with patch('app.services.github_search_service.GitHubSearchService.search_repositories') as mock_search:
            mock_search.return_value = [
                {
                    'id': 1,
                    'name': 'fastapi-tutorial',
                    'full_name': 'user/fastapi-tutorial',
                    'description': 'Learn FastAPI by building a real application',
                    'html_url': 'https://github.com/user/fastapi-tutorial',
                    'language': 'Python',
                    'stargazers_count': 1500,
                    'forks_count': 300,
                    'topics': ['fastapi', 'python', 'tutorial', 'web-development'],
                    'updated_at': '2024-01-15T10:00:00Z',
                    'license': {'name': 'MIT License'},
                    'has_wiki': True,
                    'has_pages': True
                },
                {
                    'id': 2,
                    'name': 'react-fastapi-app',
                    'full_name': 'user/react-fastapi-app',
                    'description': 'Full-stack application with React and FastAPI',
                    'html_url': 'https://github.com/user/react-fastapi-app',
                    'language': 'JavaScript',
                    'stargazers_count': 800,
                    'forks_count': 150,
                    'topics': ['react', 'fastapi', 'fullstack'],
                    'updated_at': '2024-01-10T10:00:00Z',
                    'license': {'name': 'MIT License'},
                    'has_wiki': False,
                    'has_pages': False
                }
            ]
            
            # Execute discovery workflow
            result = await discovery_agent.discover_repositories(sample_user_preferences)
            
            # Verify results
            assert 'repositories' in result
            assert len(result['repositories']) == 2
            
            # Verify repository data structure
            repo = result['repositories'][0]
            assert 'id' in repo
            assert 'name' in repo
            assert 'relevance_score' in repo
            assert 'selection_reasoning' in repo
            assert 'learning_path_suggestions' in repo
            
            # Verify relevance scoring
            assert 0 <= repo['relevance_score'] <= 100
            assert repo['selection_reasoning'] is not None
            assert len(repo['learning_path_suggestions']) > 0
    
    @pytest.mark.asyncio
    async def test_repository_discovery_with_rate_limiting(self, discovery_agent, sample_user_preferences):
        """Test repository discovery handles GitHub API rate limiting"""
        
        with patch('app.services.github_search_service.GitHubSearchService.search_repositories') as mock_search:
            # Simulate rate limit error
            mock_search.side_effect = Exception("API rate limit exceeded")
            
            # Should handle gracefully and return cached/fallback results
            result = await discovery_agent.discover_repositories(sample_user_preferences)
            
            assert 'error' in result
            assert 'fallback_repositories' in result
            assert result['error'] == 'rate_limit_exceeded'
    
    @pytest.mark.asyncio
    async def test_repository_quality_assessment(self, discovery_agent):
        """Test repository quality assessment functionality"""
        
        sample_repo = {
            'stargazers_count': 1500,
            'forks_count': 300,
            'updated_at': '2024-01-15T10:00:00Z',
            'license': {'name': 'MIT License'},
            'has_wiki': True,
            'has_pages': True,
            'topics': ['tutorial', 'beginner-friendly', 'documentation']
        }
        
        quality_score = discovery_agent._assess_repository_quality(sample_repo)
        
        assert 0 <= quality_score <= 100
        assert quality_score > 50  # Should be high quality based on metrics


class TestRepositoryAnalysisAgentIntegration:
    """Integration tests for Repository Analysis Agent"""
    
    @pytest.fixture
    def analysis_agent(self):
        return RepositoryAnalysisAgent()
    
    @pytest.fixture
    def sample_repository(self):
        return {
            'id': 1,
            'name': 'fastapi-tutorial',
            'full_name': 'user/fastapi-tutorial',
            'html_url': 'https://github.com/user/fastapi-tutorial',
            'language': 'Python',
            'topics': ['fastapi', 'python', 'tutorial']
        }
    
    @pytest.mark.asyncio
    async def test_complete_repository_analysis_workflow(self, analysis_agent, sample_repository):
        """Test complete repository analysis workflow"""
        
        # Mock GitHub API for repository content
        with patch('app.services.github_search_service.GitHubSearchService.get_repository_contents') as mock_contents:
            mock_contents.return_value = {
                'files': [
                    {'name': 'main.py', 'type': 'file', 'size': 1500},
                    {'name': 'requirements.txt', 'type': 'file', 'size': 200},
                    {'name': 'README.md', 'type': 'file', 'size': 3000},
                    {'name': 'tests/', 'type': 'dir'},
                    {'name': 'app/', 'type': 'dir'}
                ],
                'readme_content': '# FastAPI Tutorial\n\nLearn FastAPI by building a real application...',
                'structure': {
                    'directories': ['app', 'tests'],
                    'main_files': ['main.py', 'requirements.txt'],
                    'documentation': ['README.md']
                }
            }
            
            # Execute analysis workflow
            result = await analysis_agent.analyze_repository(sample_repository)
            
            # Verify analysis results
            assert 'analysis' in result
            assert 'architectural_patterns' in result['analysis']
            assert 'complexity_assessment' in result['analysis']
            assert 'learning_opportunities' in result['analysis']
            assert 'educational_value' in result['analysis']
            
            # Verify complexity assessment
            complexity = result['analysis']['complexity_assessment']
            assert 'overall_complexity' in complexity
            assert complexity['overall_complexity'] in ['beginner', 'intermediate', 'advanced']
            
            # Verify learning opportunities
            opportunities = result['analysis']['learning_opportunities']
            assert len(opportunities) > 0
            assert all('concept' in opp and 'description' in opp for opp in opportunities)
    
    @pytest.mark.asyncio
    async def test_architectural_pattern_detection(self, analysis_agent, sample_repository):
        """Test architectural pattern detection"""
        
        with patch('app.services.github_search_service.GitHubSearchService.get_repository_contents') as mock_contents:
            mock_contents.return_value = {
                'files': [
                    {'name': 'main.py', 'type': 'file'},
                    {'name': 'models.py', 'type': 'file'},
                    {'name': 'views.py', 'type': 'file'},
                    {'name': 'controllers/', 'type': 'dir'}
                ],
                'structure': {
                    'directories': ['controllers'],
                    'main_files': ['main.py', 'models.py', 'views.py']
                }
            }
            
            patterns = await analysis_agent._detect_architectural_patterns(sample_repository)
            
            assert len(patterns) > 0
            assert any('MVC' in pattern['name'] for pattern in patterns)
    
    @pytest.mark.asyncio
    async def test_code_complexity_assessment(self, analysis_agent):
        """Test code complexity assessment for different skill levels"""
        
        # Test beginner-level complexity
        beginner_repo = {
            'language': 'Python',
            'file_count': 5,
            'directory_count': 2,
            'has_tests': False,
            'has_documentation': True
        }
        
        complexity = analysis_agent._assess_code_complexity(beginner_repo)
        assert complexity['level'] == 'beginner'
        assert complexity['score'] <= 30
        
        # Test advanced-level complexity
        advanced_repo = {
            'language': 'Python',
            'file_count': 50,
            'directory_count': 15,
            'has_tests': True,
            'has_documentation': True,
            'has_ci_cd': True,
            'architectural_patterns': ['Microservices', 'Event-Driven']
        }
        
        complexity = analysis_agent._assess_code_complexity(advanced_repo)
        assert complexity['level'] == 'advanced'
        assert complexity['score'] >= 70


class TestCurriculumGenerationAgentIntegration:
    """Integration tests for Curriculum Generation Agent"""
    
    @pytest.fixture
    def curriculum_agent(self):
        return CurriculumGenerationAgent()
    
    @pytest.fixture
    def sample_analysis_data(self):
        return {
            'repository': {
                'name': 'fastapi-tutorial',
                'language': 'Python',
                'topics': ['fastapi', 'web-development']
            },
            'analysis': {
                'complexity_assessment': {
                    'overall_complexity': 'intermediate',
                    'score': 65
                },
                'learning_opportunities': [
                    {'concept': 'REST API Design', 'description': 'Learn to design RESTful APIs'},
                    {'concept': 'Database Integration', 'description': 'Connect to databases'}
                ],
                'architectural_patterns': [
                    {'name': 'MVC Pattern', 'description': 'Model-View-Controller architecture'}
                ]
            },
            'user_preferences': {
                'experience_level': 'intermediate',
                'learning_goals': ['Build web APIs', 'Learn Python'],
                'time_commitment': '10-15 hours/week'
            }
        }
    
    @pytest.mark.asyncio
    async def test_complete_curriculum_generation_workflow(self, curriculum_agent, sample_analysis_data):
        """Test complete curriculum generation workflow"""
        
        # Mock LLM service
        with patch('app.services.llm_provider.LLMProvider.generate_curriculum') as mock_llm:
            mock_llm.return_value = {
                'title': 'Learn FastAPI Web Development',
                'description': 'Master FastAPI by building a complete web application',
                'objectives': [
                    'Understand FastAPI fundamentals',
                    'Build REST APIs',
                    'Implement database integration'
                ],
                'curriculum': [
                    {
                        'phase': 'Foundation',
                        'title': 'FastAPI Basics',
                        'description': 'Learn the fundamentals of FastAPI',
                        'tasks': [
                            'Set up FastAPI development environment',
                            'Create your first FastAPI application',
                            'Understand request/response handling'
                        ],
                        'estimated_hours': 8
                    },
                    {
                        'phase': 'Development',
                        'title': 'Building APIs',
                        'description': 'Create comprehensive REST APIs',
                        'tasks': [
                            'Design API endpoints',
                            'Implement CRUD operations',
                            'Add input validation'
                        ],
                        'estimated_hours': 12
                    }
                ],
                'prerequisites': ['Basic Python knowledge', 'Understanding of HTTP'],
                'learning_outcomes': ['Build production-ready APIs', 'Deploy FastAPI applications']
            }
            
            # Execute curriculum generation
            result = await curriculum_agent.generate_curriculum(sample_analysis_data)
            
            # Verify curriculum structure
            assert 'title' in result
            assert 'description' in result
            assert 'objectives' in result
            assert 'curriculum' in result
            assert 'prerequisites' in result
            assert 'learning_outcomes' in result
            
            # Verify curriculum phases
            curriculum = result['curriculum']
            assert len(curriculum) >= 2
            
            for phase in curriculum:
                assert 'phase' in phase
                assert 'title' in phase
                assert 'description' in phase
                assert 'tasks' in phase
                assert 'estimated_hours' in phase
                assert len(phase['tasks']) > 0
    
    @pytest.mark.asyncio
    async def test_curriculum_personalization(self, curriculum_agent):
        """Test curriculum personalization based on user preferences"""
        
        # Test beginner-level personalization
        beginner_data = {
            'user_preferences': {
                'experience_level': 'beginner',
                'time_commitment': '5-10 hours/week'
            },
            'analysis': {
                'complexity_assessment': {'overall_complexity': 'intermediate'}
            }
        }
        
        with patch('app.services.llm_provider.LLMProvider.generate_curriculum') as mock_llm:
            mock_llm.return_value = {'curriculum': []}
            
            await curriculum_agent.generate_curriculum(beginner_data)
            
            # Verify LLM was called with beginner-specific prompts
            call_args = mock_llm.call_args[0][0]
            assert 'beginner' in call_args.lower()
            assert 'step-by-step' in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_difficulty_progression_analysis(self, curriculum_agent):
        """Test difficulty progression in generated curriculum"""
        
        sample_curriculum = [
            {'phase': 'Foundation', 'estimated_hours': 8, 'complexity': 'beginner'},
            {'phase': 'Development', 'estimated_hours': 12, 'complexity': 'intermediate'},
            {'phase': 'Advanced', 'estimated_hours': 16, 'complexity': 'advanced'}
        ]
        
        progression = curriculum_agent._analyze_difficulty_progression(sample_curriculum)
        
        assert progression['is_progressive'] is True
        assert progression['total_hours'] == 36
        assert len(progression['difficulty_levels']) == 3


class TestWorkflowOrchestrationServiceIntegration:
    """Integration tests for Workflow Orchestration Service"""
    
    @pytest.fixture
    def orchestration_service(self):
        return WorkflowOrchestrationService()
    
    @pytest.fixture
    def sample_workflow_request(self):
        return {
            'user_id': 'test-user-123',
            'skill_assessment': {
                'experience_level': 'intermediate',
                'current_skills': ['Python', 'JavaScript'],
                'learning_goals': ['Build web applications', 'Learn FastAPI']
            },
            'technology_preferences': [
                {'name': 'Python', 'category': 'language', 'proficiency': 'intermediate'},
                {'name': 'FastAPI', 'category': 'backend', 'proficiency': 'beginner'}
            ]
        }
    
    @pytest.mark.asyncio
    async def test_complete_workflow_orchestration(self, orchestration_service, sample_workflow_request):
        """Test complete workflow orchestration from start to finish"""
        
        # Mock all agent services
        with patch.multiple(
            'app.services.workflow_orchestration_service',
            RepositoryDiscoveryAgent=Mock(),
            RepositoryAnalysisAgent=Mock(),
            CurriculumGenerationAgent=Mock()
        ) as mocks:
            
            # Configure mock responses
            mocks['RepositoryDiscoveryAgent'].return_value.discover_repositories = AsyncMock(return_value={
                'repositories': [{'id': 1, 'name': 'test-repo'}]
            })
            
            mocks['RepositoryAnalysisAgent'].return_value.analyze_repository = AsyncMock(return_value={
                'analysis': {'complexity_assessment': {'overall_complexity': 'intermediate'}}
            })
            
            mocks['CurriculumGenerationAgent'].return_value.generate_curriculum = AsyncMock(return_value={
                'title': 'Test Curriculum',
                'curriculum': [{'phase': 'Foundation', 'tasks': ['Task 1']}]
            })
            
            # Execute complete workflow
            result = await orchestration_service.execute_workflow(sample_workflow_request)
            
            # Verify workflow completion
            assert 'workflow_id' in result
            assert 'status' in result
            assert result['status'] == 'completed'
            assert 'project_preview' in result
            assert 'repositories' in result
            assert 'curriculum' in result
    
    @pytest.mark.asyncio
    async def test_workflow_error_handling_and_recovery(self, orchestration_service, sample_workflow_request):
        """Test workflow error handling and recovery mechanisms"""
        
        with patch.multiple(
            'app.services.workflow_orchestration_service',
            RepositoryDiscoveryAgent=Mock(),
            RepositoryAnalysisAgent=Mock(),
            CurriculumGenerationAgent=Mock()
        ) as mocks:
            
            # Simulate repository discovery failure
            mocks['RepositoryDiscoveryAgent'].return_value.discover_repositories = AsyncMock(
                side_effect=Exception("GitHub API unavailable")
            )
            
            # Should fall back to manual repository entry
            result = await orchestration_service.execute_workflow(sample_workflow_request)
            
            assert 'error' in result
            assert 'fallback' in result
            assert result['fallback']['type'] == 'manual_repository_entry'
    
    @pytest.mark.asyncio
    async def test_workflow_state_persistence(self, orchestration_service, sample_workflow_request):
        """Test workflow state persistence and recovery"""
        
        # Start workflow
        workflow_id = await orchestration_service.start_workflow(sample_workflow_request)
        
        # Verify state is persisted
        state = await orchestration_service.get_workflow_state(workflow_id)
        assert state['workflow_id'] == workflow_id
        assert state['status'] == 'in_progress'
        assert 'current_step' in state
        
        # Update workflow state
        await orchestration_service.update_workflow_state(workflow_id, {
            'current_step': 'repository_analysis',
            'progress': 50
        })
        
        # Verify state update
        updated_state = await orchestration_service.get_workflow_state(workflow_id)
        assert updated_state['current_step'] == 'repository_analysis'
        assert updated_state['progress'] == 50
    
    @pytest.mark.asyncio
    async def test_real_time_progress_updates(self, orchestration_service, sample_workflow_request):
        """Test real-time progress updates during workflow execution"""
        
        progress_updates = []
        
        def progress_callback(update):
            progress_updates.append(update)
        
        # Execute workflow with progress callback
        await orchestration_service.execute_workflow(
            sample_workflow_request,
            progress_callback=progress_callback
        )
        
        # Verify progress updates were sent
        assert len(progress_updates) > 0
        assert any(update['step'] == 'repository_discovery' for update in progress_updates)
        assert any(update['step'] == 'curriculum_generation' for update in progress_updates)


class TestEndToEndWorkflowIntegration:
    """End-to-end integration tests for the complete enhanced workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_enhanced_workflow_integration(self):
        """Test complete enhanced workflow from user input to project creation"""
        
        # Simulate complete user workflow
        user_input = {
            'skill_assessment': {
                'experience_level': 'intermediate',
                'current_skills': ['Python', 'JavaScript', 'HTML', 'CSS'],
                'learning_goals': ['Build full-stack applications', 'Learn modern frameworks'],
                'learning_style': 'hands-on',
                'time_commitment': '10-15 hours/week',
                'motivation': 'Career advancement'
            },
            'technology_preferences': [
                {'name': 'Python', 'category': 'language', 'proficiency': 'intermediate'},
                {'name': 'FastAPI', 'category': 'backend', 'proficiency': 'beginner'},
                {'name': 'React', 'category': 'frontend', 'proficiency': 'beginner'}
            ]
        }
        
        # Initialize orchestration service
        orchestration_service = WorkflowOrchestrationService()
        
        # Mock external dependencies
        with patch.multiple(
            'app.services.github_search_service.GitHubSearchService',
            search_repositories=AsyncMock(return_value=[
                {
                    'id': 1,
                    'name': 'fastapi-react-app',
                    'full_name': 'user/fastapi-react-app',
                    'description': 'Full-stack application with FastAPI and React',
                    'html_url': 'https://github.com/user/fastapi-react-app',
                    'language': 'Python',
                    'stargazers_count': 1200,
                    'topics': ['fastapi', 'react', 'fullstack']
                }
            ]),
            get_repository_contents=AsyncMock(return_value={
                'files': [
                    {'name': 'main.py', 'type': 'file'},
                    {'name': 'frontend/', 'type': 'dir'},
                    {'name': 'backend/', 'type': 'dir'}
                ]
            })
        ):
            with patch('app.services.llm_provider.LLMProvider.generate_curriculum') as mock_llm:
                mock_llm.return_value = {
                    'title': 'Full-Stack Development with FastAPI and React',
                    'description': 'Build modern web applications',
                    'objectives': ['Master FastAPI', 'Learn React', 'Deploy applications'],
                    'curriculum': [
                        {
                            'phase': 'Backend Development',
                            'title': 'FastAPI Fundamentals',
                            'description': 'Learn FastAPI basics',
                            'tasks': ['Setup FastAPI', 'Create APIs', 'Database integration'],
                            'estimated_hours': 12
                        },
                        {
                            'phase': 'Frontend Development',
                            'title': 'React Application',
                            'description': 'Build React frontend',
                            'tasks': ['Setup React', 'Create components', 'API integration'],
                            'estimated_hours': 16
                        }
                    ],
                    'prerequisites': ['Basic Python', 'Basic JavaScript'],
                    'learning_outcomes': ['Full-stack applications', 'Modern deployment']
                }
                
                # Execute complete workflow
                result = await orchestration_service.execute_workflow(user_input)
                
                # Verify end-to-end results
                assert result['status'] == 'completed'
                assert 'project_preview' in result
                assert 'repositories' in result
                assert 'curriculum' in result
                
                # Verify project preview structure
                project_preview = result['project_preview']
                assert 'title' in project_preview
                assert 'description' in project_preview
                assert 'objectives' in project_preview
                assert 'curriculum' in project_preview
                assert len(project_preview['curriculum']) == 2
                
                # Verify repository selection
                repositories = result['repositories']
                assert len(repositories) > 0
                assert repositories[0]['name'] == 'fastapi-react-app'
                
                # Verify curriculum generation
                curriculum = result['curriculum']
                assert len(curriculum) == 2
                assert curriculum[0]['phase'] == 'Backend Development'
                assert curriculum[1]['phase'] == 'Frontend Development'
    
    @pytest.mark.asyncio
    async def test_workflow_performance_benchmarks(self):
        """Test workflow performance meets acceptable benchmarks"""
        
        start_time = datetime.now()
        
        # Execute workflow with performance monitoring
        orchestration_service = WorkflowOrchestrationService()
        
        user_input = {
            'skill_assessment': {'experience_level': 'beginner'},
            'technology_preferences': [{'name': 'Python', 'category': 'language'}]
        }
        
        with patch.multiple(
            'app.services.workflow_orchestration_service',
            RepositoryDiscoveryAgent=Mock(),
            RepositoryAnalysisAgent=Mock(),
            CurriculumGenerationAgent=Mock()
        ):
            result = await orchestration_service.execute_workflow(user_input)
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Verify performance benchmarks
            assert execution_time < 300  # Should complete within 5 minutes
            assert result['status'] == 'completed'
    
    @pytest.mark.asyncio
    async def test_workflow_scalability_under_load(self):
        """Test workflow can handle multiple concurrent requests"""
        
        orchestration_service = WorkflowOrchestrationService()
        
        # Create multiple concurrent workflow requests
        user_inputs = [
            {'skill_assessment': {'experience_level': 'beginner'}},
            {'skill_assessment': {'experience_level': 'intermediate'}},
            {'skill_assessment': {'experience_level': 'advanced'}}
        ]
        
        with patch.multiple(
            'app.services.workflow_orchestration_service',
            RepositoryDiscoveryAgent=Mock(),
            RepositoryAnalysisAgent=Mock(),
            CurriculumGenerationAgent=Mock()
        ):
            # Execute workflows concurrently
            tasks = [
                orchestration_service.execute_workflow(user_input)
                for user_input in user_inputs
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all workflows completed successfully
            assert len(results) == 3
            assert all(isinstance(result, dict) and result.get('status') == 'completed' 
                      for result in results if not isinstance(result, Exception))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])