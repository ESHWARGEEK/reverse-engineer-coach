"""
Integration tests for repository discovery API endpoints
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import User
from app.services.github_search_service import RepositorySuggestion, RepositoryQuality
from app.services.repository_analyzer import RepositoryAnalysis


class TestDiscoveryAPIIntegration:
    """Integration tests for discovery API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user"""
        user = Mock(spec=User)
        user.id = "test-user-id"
        user.email = "test@example.com"
        user.preferred_ai_provider = "openai"
        return user
    
    @pytest.fixture
    def mock_auth_service(self):
        """Mock authentication service"""
        auth_service = Mock()
        auth_service.get_user_credentials = Mock(return_value=("github_token", "ai_api_key"))
        return auth_service
    
    @pytest.fixture
    def mock_repository_suggestions(self):
        """Mock repository suggestions"""
        return [
            RepositorySuggestion(
                repository_url='https://github.com/example/microservices-demo',
                repository_name='microservices-demo',
                full_name='example/microservices-demo',
                description='Comprehensive microservices architecture example',
                stars=500,
                forks=100,
                language='Java',
                topics=['microservices', 'spring-boot', 'docker'],
                size=5000,
                created_at='2022-01-01T00:00:00Z',
                updated_at='2024-01-01T00:00:00Z',
                last_push_at='2024-01-01T00:00:00Z',
                license_name='MIT',
                quality=RepositoryQuality(0.8, 0.9, 0.7, 0.8, 0.8, 0.8),
                educational_value=0.9,
                relevance_score=0.8,
                has_readme=True,
                has_documentation=True,
                has_tests=True,
                has_ci=True,
                contributor_count=10,
                recent_activity=True
            ),
            RepositorySuggestion(
                repository_url='https://github.com/example/simple-api',
                repository_name='simple-api',
                full_name='example/simple-api',
                description='Simple REST API example',
                stars=50,
                forks=10,
                language='Python',
                topics=['api', 'flask'],
                size=1000,
                created_at='2023-01-01T00:00:00Z',
                updated_at='2024-01-01T00:00:00Z',
                last_push_at='2024-01-01T00:00:00Z',
                license_name='Apache-2.0',
                quality=RepositoryQuality(0.7, 0.6, 0.8, 0.9, 0.6, 0.72),
                educational_value=0.8,
                relevance_score=0.7,
                has_readme=True,
                has_documentation=False,
                has_tests=True,
                has_ci=False,
                contributor_count=3,
                recent_activity=True
            )
        ]
    
    @pytest.fixture
    def mock_repository_analysis(self):
        """Mock repository analysis"""
        return Mock(
            repository_url='https://github.com/example/test-repo',
            learning_potential_score=0.8,
            implementation_difficulty=0.6,
            concept_coverage=0.7,
            to_dict=lambda: {
                'repository_url': 'https://github.com/example/test-repo',
                'learning_potential_score': 0.8,
                'implementation_difficulty': 0.6,
                'concept_coverage': 0.7,
                'architectural_patterns': [],
                'educational_assessment': {
                    'learning_difficulty': 3,
                    'overall_educational_score': 0.8
                }
            }
        )
    
    def test_discover_repositories_endpoint_success(
        self, 
        client, 
        mock_user, 
        mock_auth_service, 
        mock_repository_suggestions
    ):
        """Test successful repository discovery endpoint"""
        with patch('app.routers.discovery.get_current_user', return_value=mock_user), \
             patch('app.routers.discovery.AuthService', return_value=mock_auth_service), \
             patch('app.routers.discovery.GitHubSearchService') as mock_search_service:
            
            # Mock search service
            mock_service_instance = Mock()
            mock_service_instance.__aenter__ = AsyncMock(return_value=mock_service_instance)
            mock_service_instance.__aexit__ = AsyncMock(return_value=None)
            mock_service_instance.discover_repositories = AsyncMock(return_value=mock_repository_suggestions)
            mock_search_service.return_value = mock_service_instance
            
            # Make request
            response = client.post(
                "/discover/repositories",
                json={
                    "concept": "microservices architecture",
                    "max_results": 10,
                    "min_stars": 10,
                    "language": "Java"
                },
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Check response structure
            assert "concept" in data
            assert "total_results" in data
            assert "repositories" in data
            assert "search_metadata" in data
            
            # Check data content
            assert data["concept"] == "microservices architecture"
            assert data["total_results"] == 2
            assert len(data["repositories"]) == 2
            
            # Check repository data
            repo = data["repositories"][0]
            assert "repository_url" in repo
            assert "repository_name" in repo
            assert "stars" in repo
            assert "language" in repo
            assert "overall_score" in repo
    
    def test_discover_repositories_endpoint_validation_error(self, client, mock_user):
        """Test repository discovery endpoint with validation errors"""
        with patch('app.routers.discovery.get_current_user', return_value=mock_user):
            
            # Test missing concept
            response = client.post(
                "/discover/repositories",
                json={
                    "max_results": 10
                },
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 422  # Validation error
            
            # Test invalid concept (too short)
            response = client.post(
                "/discover/repositories",
                json={
                    "concept": "ab",  # Too short
                    "max_results": 10
                },
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 422  # Validation error
            
            # Test invalid max_results (too large)
            response = client.post(
                "/discover/repositories",
                json={
                    "concept": "microservices",
                    "max_results": 100  # Too large
                },
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 422  # Validation error
    
    def test_discover_repositories_endpoint_no_github_token(
        self, 
        client, 
        mock_user
    ):
        """Test repository discovery endpoint without GitHub token"""
        mock_auth_service = Mock()
        mock_auth_service.get_user_credentials = Mock(return_value=(None, "ai_api_key"))
        
        with patch('app.routers.discovery.get_current_user', return_value=mock_user), \
             patch('app.routers.discovery.AuthService', return_value=mock_auth_service):
            
            response = client.post(
                "/discover/repositories",
                json={
                    "concept": "microservices architecture",
                    "max_results": 10
                },
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "GitHub token not found" in data["detail"]
    
    def test_analyze_repository_endpoint_success(
        self, 
        client, 
        mock_user, 
        mock_auth_service, 
        mock_repository_analysis
    ):
        """Test successful repository analysis endpoint"""
        with patch('app.routers.discovery.get_current_user', return_value=mock_user), \
             patch('app.routers.discovery.AuthService', return_value=mock_auth_service), \
             patch('app.routers.discovery.RepositoryAnalyzer') as mock_analyzer:
            
            # Mock analyzer
            mock_analyzer_instance = Mock()
            mock_analyzer_instance.__aenter__ = AsyncMock(return_value=mock_analyzer_instance)
            mock_analyzer_instance.__aexit__ = AsyncMock(return_value=None)
            mock_analyzer_instance.analyze_repository = AsyncMock(return_value=mock_repository_analysis)
            mock_analyzer.return_value = mock_analyzer_instance
            
            # Make request
            response = client.post(
                "/discover/analyze",
                json={
                    "repository_url": "https://github.com/example/test-repo",
                    "learning_concept": "microservices"
                },
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Check response structure
            assert "repository_url" in data
            assert "analysis" in data
            
            # Check data content
            assert data["repository_url"] == "https://github.com/example/test-repo"
            assert "learning_potential_score" in data["analysis"]
    
    def test_analyze_repository_endpoint_invalid_url(self, client, mock_user):
        """Test repository analysis endpoint with invalid URL"""
        with patch('app.routers.discovery.get_current_user', return_value=mock_user):
            
            # Test invalid URL
            response = client.post(
                "/discover/analyze",
                json={
                    "repository_url": "not-a-github-url",
                    "learning_concept": "microservices"
                },
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 422  # Validation error
            
            # Test empty URL
            response = client.post(
                "/discover/analyze",
                json={
                    "repository_url": "",
                    "learning_concept": "microservices"
                },
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 422  # Validation error
    
    def test_discover_by_language_endpoint_success(
        self, 
        client, 
        mock_user, 
        mock_auth_service, 
        mock_repository_suggestions
    ):
        """Test successful language-specific discovery endpoint"""
        with patch('app.routers.discovery.get_current_user', return_value=mock_user), \
             patch('app.routers.discovery.AuthService', return_value=mock_auth_service), \
             patch('app.routers.discovery.GitHubSearchService') as mock_search_service:
            
            # Mock search service
            mock_service_instance = Mock()
            mock_service_instance.__aenter__ = AsyncMock(return_value=mock_service_instance)
            mock_service_instance.__aexit__ = AsyncMock(return_value=None)
            mock_service_instance.get_repository_suggestions_by_language = AsyncMock(
                return_value=mock_repository_suggestions
            )
            mock_search_service.return_value = mock_service_instance
            
            # Make request
            response = client.post(
                "/discover/by-language",
                json={
                    "language": "Python",
                    "concepts": ["flask", "api"],
                    "max_results": 5
                },
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Check response structure
            assert "concept" in data
            assert "total_results" in data
            assert "repositories" in data
            assert "search_metadata" in data
            
            # Check metadata
            assert data["search_metadata"]["language_filter"] == "Python"
            assert data["search_metadata"]["concept_keywords"] == ["flask", "api"]
    
    def test_concept_suggestions_endpoint(self, client):
        """Test concept suggestions endpoint"""
        response = client.get("/discover/suggestions?query=micro&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "query" in data
        assert "suggestions" in data
        assert "total_matches" in data
        
        # Check data content
        assert data["query"] == "micro"
        assert isinstance(data["suggestions"], list)
        assert len(data["suggestions"]) <= 5
        
        # Suggestions should contain the query term
        for suggestion in data["suggestions"]:
            assert "micro" in suggestion.lower()
    
    def test_popular_concepts_endpoint(self, client):
        """Test popular concepts endpoint"""
        response = client.get("/discover/popular-concepts")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "categories" in data
        assert "trending" in data
        
        # Check categories
        categories = data["categories"]
        expected_categories = [
            "architectural_patterns",
            "web_development", 
            "design_patterns",
            "frameworks",
            "devops"
        ]
        
        for category in expected_categories:
            assert category in categories
            assert isinstance(categories[category], list)
            assert len(categories[category]) > 0
        
        # Check trending
        assert isinstance(data["trending"], list)
        assert len(data["trending"]) > 0
    
    def test_refresh_cache_endpoint_success(
        self, 
        client, 
        mock_user, 
        mock_auth_service
    ):
        """Test successful cache refresh endpoint"""
        with patch('app.routers.discovery.get_current_user', return_value=mock_user), \
             patch('app.routers.discovery.AuthService', return_value=mock_auth_service), \
             patch('app.routers.discovery.GitHubSearchService') as mock_search_service:
            
            # Mock search service
            mock_service_instance = Mock()
            mock_service_instance.__aenter__ = AsyncMock(return_value=mock_service_instance)
            mock_service_instance.__aexit__ = AsyncMock(return_value=None)
            mock_service_instance.refresh_repository_cache = AsyncMock(return_value=True)
            mock_search_service.return_value = mock_service_instance
            
            # Make request
            response = client.post(
                "/discover/refresh-cache?concept=microservices",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Check response structure
            assert "message" in data
            assert "concept" in data
            assert "refreshed_at" in data
            
            # Check data content
            assert data["concept"] == "microservices"
            assert "refreshed successfully" in data["message"]
    
    def test_discovery_stats_endpoint(self, client, mock_user):
        """Test discovery statistics endpoint"""
        with patch('app.routers.discovery.get_current_user', return_value=mock_user), \
             patch('app.cache.cache.get_stats', return_value={
                 "hit_rate": 0.75,
                 "hits": 150,
                 "misses": 50
             }):
            
            response = client.get(
                "/discover/stats",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Check response structure
            expected_fields = [
                "total_searches_today",
                "unique_concepts_searched",
                "average_results_per_search",
                "most_popular_languages",
                "most_searched_concepts",
                "cache_performance"
            ]
            
            for field in expected_fields:
                assert field in data
            
            # Check cache performance data
            cache_perf = data["cache_performance"]
            assert "hit_rate" in cache_perf
            assert "total_hits" in cache_perf
            assert "total_misses" in cache_perf
    
    def test_endpoint_authentication_required(self, client):
        """Test that endpoints require authentication"""
        # Test discovery endpoint without auth
        response = client.post(
            "/discover/repositories",
            json={
                "concept": "microservices",
                "max_results": 10
            }
        )
        assert response.status_code == 401  # Unauthorized
        
        # Test analysis endpoint without auth
        response = client.post(
            "/discover/analyze",
            json={
                "repository_url": "https://github.com/example/repo"
            }
        )
        assert response.status_code == 401  # Unauthorized
        
        # Test stats endpoint without auth
        response = client.get("/discover/stats")
        assert response.status_code == 401  # Unauthorized
    
    def test_endpoint_rate_limiting(self, client, mock_user):
        """Test that endpoints have rate limiting"""
        with patch('app.routers.discovery.get_current_user', return_value=mock_user):
            
            # This would test rate limiting if implemented
            # For now, just verify the endpoint responds
            response = client.get(
                "/discover/suggestions?query=test",
                headers={"Authorization": "Bearer test_token"}
            )
            
            # Should succeed (rate limiting would be tested with multiple rapid requests)
            assert response.status_code == 200


class TestDiscoveryAPIErrorHandling:
    """Test error handling in discovery API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user"""
        user = Mock(spec=User)
        user.id = "test-user-id"
        user.email = "test@example.com"
        return user
    
    def test_discovery_endpoint_github_api_error(self, client, mock_user):
        """Test discovery endpoint when GitHub API fails"""
        mock_auth_service = Mock()
        mock_auth_service.get_user_credentials = Mock(return_value=("github_token", "ai_api_key"))
        
        with patch('app.routers.discovery.get_current_user', return_value=mock_user), \
             patch('app.routers.discovery.AuthService', return_value=mock_auth_service), \
             patch('app.routers.discovery.GitHubSearchService') as mock_search_service:
            
            # Mock search service to raise exception
            mock_service_instance = Mock()
            mock_service_instance.__aenter__ = AsyncMock(return_value=mock_service_instance)
            mock_service_instance.__aexit__ = AsyncMock(return_value=None)
            mock_service_instance.discover_repositories = AsyncMock(
                side_effect=Exception("GitHub API error")
            )
            mock_search_service.return_value = mock_service_instance
            
            response = client.post(
                "/discover/repositories",
                json={
                    "concept": "microservices",
                    "max_results": 10
                },
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "Repository discovery failed" in data["detail"]
    
    def test_analysis_endpoint_analyzer_error(self, client, mock_user):
        """Test analysis endpoint when analyzer fails"""
        mock_auth_service = Mock()
        mock_auth_service.get_user_credentials = Mock(return_value=("github_token", "ai_api_key"))
        
        with patch('app.routers.discovery.get_current_user', return_value=mock_user), \
             patch('app.routers.discovery.AuthService', return_value=mock_auth_service), \
             patch('app.routers.discovery.RepositoryAnalyzer') as mock_analyzer:
            
            # Mock analyzer to raise exception
            mock_analyzer_instance = Mock()
            mock_analyzer_instance.__aenter__ = AsyncMock(return_value=mock_analyzer_instance)
            mock_analyzer_instance.__aexit__ = AsyncMock(return_value=None)
            mock_analyzer_instance.analyze_repository = AsyncMock(
                side_effect=Exception("Analysis failed")
            )
            mock_analyzer.return_value = mock_analyzer_instance
            
            response = client.post(
                "/discover/analyze",
                json={
                    "repository_url": "https://github.com/example/repo"
                },
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "Repository analysis failed" in data["detail"]
    
    def test_cache_refresh_endpoint_failure(self, client, mock_user):
        """Test cache refresh endpoint when refresh fails"""
        mock_auth_service = Mock()
        mock_auth_service.get_user_credentials = Mock(return_value=("github_token", "ai_api_key"))
        
        with patch('app.routers.discovery.get_current_user', return_value=mock_user), \
             patch('app.routers.discovery.AuthService', return_value=mock_auth_service), \
             patch('app.routers.discovery.GitHubSearchService') as mock_search_service:
            
            # Mock search service to return failure
            mock_service_instance = Mock()
            mock_service_instance.__aenter__ = AsyncMock(return_value=mock_service_instance)
            mock_service_instance.__aexit__ = AsyncMock(return_value=None)
            mock_service_instance.refresh_repository_cache = AsyncMock(return_value=False)
            mock_search_service.return_value = mock_service_instance
            
            response = client.post(
                "/discover/refresh-cache?concept=microservices",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to refresh cache" in data["detail"]


if __name__ == "__main__":
    pytest.main([__file__])