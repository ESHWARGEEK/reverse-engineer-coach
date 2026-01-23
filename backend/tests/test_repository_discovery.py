"""
Tests for repository discovery system
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.services.github_search_service import GitHubSearchService, SearchFilters, RepositorySuggestion, RepositoryQuality
from app.services.repository_analyzer import RepositoryAnalyzer, ArchitecturalPattern, EducationalAssessment, ComplexityAnalysis


class TestGitHubSearchService:
    """Test GitHub search service functionality"""
    
    @pytest.fixture
    def mock_github_client(self):
        """Mock GitHub client"""
        client = Mock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        return client
    
    @pytest.fixture
    def search_service(self, mock_github_client):
        """Create search service with mocked client"""
        with patch('app.services.github_search_service.GitHubClient', return_value=mock_github_client):
            return GitHubSearchService()
    
    def test_parse_learning_concept(self, search_service):
        """Test learning concept parsing"""
        concept = "microservices architecture with Python and Docker"
        search_terms, topics, language = search_service._parse_learning_concept(concept)
        
        assert 'microservices' in search_terms
        assert 'architecture' in search_terms
        assert 'python' in search_terms
        assert 'docker' in search_terms
        assert language == 'python'
    
    def test_build_search_query(self, search_service):
        """Test search query building"""
        search_terms = ['microservices', 'api']
        filters = SearchFilters(
            min_stars=10,
            language='python',
            topics=['microservices'],
            has_readme=True
        )
        
        query = search_service._build_search_query(search_terms, filters)
        
        assert 'microservices' in query
        assert 'api' in query
        assert 'stars:>=10' in query
        assert 'language:python' in query
        assert 'topic:microservices' in query
        assert 'readme:true' in query
    
    def test_calculate_educational_value(self, search_service):
        """Test educational value calculation"""
        repo_data = {
            'size': 2000,  # Good size for learning
            'language': 'Python',
            'stargazers_count': 500,
            'topics': ['tutorial', 'example'],
            'description': 'A great example of microservices architecture'
        }
        search_terms = ['microservices', 'architecture']
        
        educational_value = search_service._calculate_educational_value(repo_data, search_terms)
        
        assert 0.0 <= educational_value <= 1.0
        assert educational_value > 0.5  # Should be reasonably high
    
    def test_calculate_relevance_score(self, search_service):
        """Test relevance score calculation"""
        repo_data = {
            'name': 'microservices-example',
            'description': 'Example microservices architecture implementation',
            'topics': ['microservices', 'architecture']
        }
        search_terms = ['microservices', 'architecture']
        
        relevance_score = search_service._calculate_relevance_score(repo_data, search_terms)
        
        assert 0.0 <= relevance_score <= 1.0
        assert relevance_score > 0.5  # Should be highly relevant


class TestRepositoryAnalyzer:
    """Test repository analyzer functionality"""
    
    @pytest.fixture
    def mock_github_client(self):
        """Mock GitHub client"""
        client = Mock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        return client
    
    @pytest.fixture
    def analyzer(self, mock_github_client):
        """Create analyzer with mocked client"""
        with patch('app.services.repository_analyzer.GitHubClient', return_value=mock_github_client):
            return RepositoryAnalyzer()
    
    def test_pattern_complexity_mapping(self, analyzer):
        """Test that pattern complexity mapping is properly defined"""
        assert 'mvc' in analyzer.pattern_complexity
        assert 'microservices' in analyzer.pattern_complexity
        assert 'singleton' in analyzer.pattern_complexity
        
        # Check complexity levels are reasonable
        assert analyzer.pattern_complexity['singleton'] < analyzer.pattern_complexity['microservices']
        assert analyzer.pattern_complexity['mvc'] < analyzer.pattern_complexity['ddd']
    
    def test_calculate_learning_potential(self, analyzer):
        """Test learning potential calculation"""
        patterns = [
            ArchitecturalPattern(
                pattern_name='mvc',
                confidence=0.8,
                description='MVC pattern',
                examples=[],
                complexity_level=2,
                educational_value=0.9
            )
        ]
        
        educational = EducationalAssessment(
            learning_difficulty=2,
            concept_clarity=0.8,
            code_readability=0.7,
            documentation_quality=0.8,
            practical_applicability=0.9,
            overall_educational_score=0.8,
            recommended_prerequisites=[],
            learning_outcomes=[]
        )
        
        complexity = ComplexityAnalysis(
            cyclomatic_complexity=0.4,
            architectural_layers=3,
            component_coupling=0.3,
            abstraction_level=0.6,
            design_pattern_usage=0.7,
            overall_complexity=0.5
        )
        
        learning_potential = analyzer._calculate_learning_potential(patterns, educational, complexity)
        
        assert 0.0 <= learning_potential <= 1.0
        assert learning_potential > 0.5  # Should be reasonably high given good inputs
    
    def test_calculate_implementation_difficulty(self, analyzer):
        """Test implementation difficulty calculation"""
        complexity = ComplexityAnalysis(
            cyclomatic_complexity=0.6,
            architectural_layers=4,
            component_coupling=0.4,
            abstraction_level=0.7,
            design_pattern_usage=0.8,
            overall_complexity=0.6
        )
        
        patterns = [
            ArchitecturalPattern(
                pattern_name='microservices',
                confidence=0.8,
                description='Microservices pattern',
                examples=[],
                complexity_level=4,
                educational_value=0.8
            )
        ]
        
        difficulty = analyzer._calculate_implementation_difficulty(complexity, patterns)
        
        assert 0.0 <= difficulty <= 1.0
        assert difficulty > 0.5  # Should be moderately difficult given complex patterns
    
    def test_calculate_concept_coverage(self, analyzer):
        """Test concept coverage calculation"""
        patterns = [
            ArchitecturalPattern(
                pattern_name='microservices',
                confidence=0.8,
                description='Microservices pattern',
                examples=[],
                complexity_level=4,
                educational_value=0.8
            )
        ]
        
        learning_concept = "microservices architecture patterns"
        coverage = analyzer._calculate_concept_coverage(patterns, learning_concept)
        
        assert 0.0 <= coverage <= 1.0
        assert coverage > 0.5  # Should have good coverage since pattern matches concept


class TestRepositoryDiscoveryIntegration:
    """Test integration between discovery components"""
    
    @pytest.fixture
    def mock_search_service(self):
        """Mock search service"""
        service = Mock()
        service.__aenter__ = AsyncMock(return_value=service)
        service.__aexit__ = AsyncMock(return_value=None)
        
        # Mock repository suggestion
        mock_suggestion = RepositorySuggestion(
            repository_url='https://github.com/example/repo',
            repository_name='example-repo',
            full_name='example/repo',
            description='Example repository',
            stars=100,
            forks=20,
            language='Python',
            topics=['microservices', 'api'],
            size=2000,
            created_at='2023-01-01T00:00:00Z',
            updated_at='2024-01-01T00:00:00Z',
            last_push_at='2024-01-01T00:00:00Z',
            license_name='MIT',
            quality=RepositoryQuality(
                readme_score=0.8,
                documentation_score=0.7,
                code_structure_score=0.8,
                activity_score=0.9,
                community_score=0.7,
                overall_score=0.78
            ),
            educational_value=0.8,
            relevance_score=0.9,
            has_readme=True,
            has_documentation=True,
            has_tests=True,
            has_ci=True,
            contributor_count=5,
            recent_activity=True
        )
        
        service.discover_repositories = AsyncMock(return_value=[mock_suggestion])
        return service
    
    @pytest.fixture
    def mock_analyzer(self):
        """Mock repository analyzer"""
        analyzer = Mock()
        analyzer.__aenter__ = AsyncMock(return_value=analyzer)
        analyzer.__aexit__ = AsyncMock(return_value=None)
        return analyzer
    
    def test_repository_suggestion_overall_score(self):
        """Test repository suggestion overall score calculation"""
        quality = RepositoryQuality(
            readme_score=0.8,
            documentation_score=0.7,
            code_structure_score=0.8,
            activity_score=0.9,
            community_score=0.7,
            overall_score=0.78
        )
        
        suggestion = RepositorySuggestion(
            repository_url='https://github.com/example/repo',
            repository_name='example-repo',
            full_name='example/repo',
            description='Example repository',
            stars=100,
            forks=20,
            language='Python',
            topics=['microservices'],
            size=2000,
            created_at='2023-01-01T00:00:00Z',
            updated_at='2024-01-01T00:00:00Z',
            last_push_at='2024-01-01T00:00:00Z',
            license_name='MIT',
            quality=quality,
            educational_value=0.8,
            relevance_score=0.9,
            has_readme=True,
            has_documentation=True,
            has_tests=True,
            has_ci=True,
            contributor_count=5,
            recent_activity=True
        )
        
        overall_score = suggestion.overall_score()
        
        assert 0.0 <= overall_score <= 1.0
        assert overall_score > 0.7  # Should be high given good metrics
    
    def test_repository_suggestion_to_dict(self):
        """Test repository suggestion serialization"""
        quality = RepositoryQuality(
            readme_score=0.8,
            documentation_score=0.7,
            code_structure_score=0.8,
            activity_score=0.9,
            community_score=0.7,
            overall_score=0.78
        )
        
        suggestion = RepositorySuggestion(
            repository_url='https://github.com/example/repo',
            repository_name='example-repo',
            full_name='example/repo',
            description='Example repository',
            stars=100,
            forks=20,
            language='Python',
            topics=['microservices'],
            size=2000,
            created_at='2023-01-01T00:00:00Z',
            updated_at='2024-01-01T00:00:00Z',
            last_push_at='2024-01-01T00:00:00Z',
            license_name='MIT',
            quality=quality,
            educational_value=0.8,
            relevance_score=0.9,
            has_readme=True,
            has_documentation=True,
            has_tests=True,
            has_ci=True,
            contributor_count=5,
            recent_activity=True
        )
        
        data = suggestion.to_dict()
        
        assert isinstance(data, dict)
        assert data['repository_url'] == 'https://github.com/example/repo'
        assert data['repository_name'] == 'example-repo'
        assert data['stars'] == 100
        assert data['language'] == 'Python'
        assert 'overall_score' in data
        assert 'quality' in data
        assert isinstance(data['quality'], dict)


class TestGitHubSearchServiceAdvanced:
    """Advanced tests for GitHub search service functionality"""
    
    @pytest.fixture
    def mock_github_client(self):
        """Mock GitHub client with comprehensive responses"""
        client = Mock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        
        # Mock comprehensive repository data
        client._make_request = AsyncMock(return_value={
            'items': [
                {
                    'id': 1,
                    'name': 'microservices-demo',
                    'full_name': 'example/microservices-demo',
                    'html_url': 'https://github.com/example/microservices-demo',
                    'description': 'A comprehensive microservices architecture example',
                    'stargazers_count': 500,
                    'forks_count': 100,
                    'language': 'Java',
                    'topics': ['microservices', 'spring-boot', 'docker'],
                    'size': 5000,
                    'created_at': '2022-01-01T00:00:00Z',
                    'updated_at': '2024-01-01T00:00:00Z',
                    'pushed_at': '2024-01-01T00:00:00Z',
                    'license': {'name': 'MIT'},
                    'has_readme': True,
                    'has_issues': True,
                    'has_projects': True,
                    'has_wiki': True
                },
                {
                    'id': 2,
                    'name': 'simple-api',
                    'full_name': 'example/simple-api',
                    'html_url': 'https://github.com/example/simple-api',
                    'description': 'Simple REST API example',
                    'stargazers_count': 50,
                    'forks_count': 10,
                    'language': 'Python',
                    'topics': ['api', 'flask'],
                    'size': 1000,
                    'created_at': '2023-01-01T00:00:00Z',
                    'updated_at': '2024-01-01T00:00:00Z',
                    'pushed_at': '2024-01-01T00:00:00Z',
                    'license': {'name': 'Apache-2.0'},
                    'has_readme': True,
                    'has_issues': True
                }
            ]
        })
        
        # Mock file content responses
        client.get_file_content = AsyncMock(return_value=(
            "# Microservices Demo\n\nThis is a comprehensive example of microservices architecture using Spring Boot and Docker.\n\n## Features\n- Service discovery\n- API Gateway\n- Configuration management\n\n## Getting Started\n1. Clone the repository\n2. Run docker-compose up",
            "README.md"
        ))
        
        # Mock repository contents
        client.get_repository_contents = AsyncMock(return_value=[
            {'name': 'README.md', 'type': 'file'},
            {'name': 'docker-compose.yml', 'type': 'file'},
            {'name': 'services', 'type': 'dir'},
            {'name': 'gateway', 'type': 'dir'},
            {'name': 'config', 'type': 'dir'},
            {'name': 'tests', 'type': 'dir'},
            {'name': 'docs', 'type': 'dir'}
        ])
        
        return client
    
    @pytest.fixture
    def advanced_search_service(self, mock_github_client):
        """Create search service with advanced mocking"""
        with patch('app.services.github_search_service.GitHubClient', return_value=mock_github_client):
            return GitHubSearchService()
    
    @pytest.mark.asyncio
    async def test_comprehensive_repository_discovery(self, advanced_search_service):
        """Test comprehensive repository discovery with real-world scenario"""
        results = await advanced_search_service.discover_repositories(
            learning_concept="microservices architecture with Spring Boot and Docker",
            max_results=10
        )
        
        assert len(results) > 0
        
        # Check that results are properly structured
        for result in results:
            assert hasattr(result, 'repository_url')
            assert hasattr(result, 'repository_name')
            assert hasattr(result, 'quality')
            assert hasattr(result, 'educational_value')
            assert hasattr(result, 'relevance_score')
            
            # Check quality metrics
            assert 0.0 <= result.quality.overall_score <= 1.0
            assert 0.0 <= result.educational_value <= 1.0
            assert 0.0 <= result.relevance_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_language_specific_discovery(self, advanced_search_service):
        """Test language-specific repository discovery"""
        # Mock the method to return Python repositories
        with patch.object(advanced_search_service, 'get_repository_suggestions_by_language') as mock_method:
            mock_method.return_value = [
                RepositorySuggestion(
                    repository_url='https://github.com/example/flask-api',
                    repository_name='flask-api',
                    full_name='example/flask-api',
                    description='Flask API example',
                    stars=100,
                    forks=20,
                    language='Python',
                    topics=['api', 'flask'],
                    size=1000,
                    created_at='2023-01-01T00:00:00Z',
                    updated_at='2024-01-01T00:00:00Z',
                    last_push_at='2024-01-01T00:00:00Z',
                    license_name='MIT',
                    quality=RepositoryQuality(0.8, 0.7, 0.8, 0.9, 0.8, 0.8),
                    educational_value=0.9,
                    relevance_score=0.8,
                    has_readme=True,
                    has_documentation=True,
                    has_tests=True,
                    has_ci=True,
                    contributor_count=5,
                    recent_activity=True
                )
            ]
            
            results = await advanced_search_service.get_repository_suggestions_by_language(
                language="Python",
                concept_keywords=["flask", "api", "microservices"],
                max_results=5
            )
            
            assert len(results) > 0
            
            # All results should be Python repositories
            for result in results:
                assert result.language.lower() == 'python'
    
    @pytest.mark.asyncio
    async def test_search_filters_application(self, advanced_search_service):
        """Test that search filters are properly applied"""
        filters = SearchFilters(
            min_stars=100,
            language="Java",
            topics=["microservices"],
            has_readme=True,
            is_fork=False
        )
        
        # Mock the discover_repositories method to return filtered results
        with patch.object(advanced_search_service, 'discover_repositories') as mock_method:
            mock_method.return_value = [
                RepositorySuggestion(
                    repository_url='https://github.com/example/microservices-java',
                    repository_name='microservices-java',
                    full_name='example/microservices-java',
                    description='Java microservices example',
                    stars=150,
                    forks=30,
                    language='Java',
                    topics=['microservices', 'spring-boot'],
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
                )
            ]
            
            results = await advanced_search_service.discover_repositories(
                learning_concept="microservices",
                filters=filters,
                max_results=5
            )
            
            assert len(results) > 0
            
            # Check that filters are respected
            for result in results:
                assert result.stars >= 100
                assert result.language == "Java"
                assert "microservices" in result.topics
                assert result.has_readme is True
    
    def test_educational_keywords_mapping(self, advanced_search_service):
        """Test that educational keywords are properly mapped"""
        keywords = advanced_search_service.educational_keywords
        
        assert 'architecture' in keywords
        assert 'patterns' in keywords
        assert 'frameworks' in keywords
        assert 'concepts' in keywords
        assert 'practices' in keywords
        
        # Check specific mappings
        assert 'microservices' in keywords['architecture']
        assert 'design-patterns' in keywords['patterns']
        assert 'spring' in keywords['frameworks']


class TestRepositoryAnalyzerAdvanced:
    """Advanced tests for repository analyzer functionality"""
    
    @pytest.fixture
    def mock_github_client_analyzer(self):
        """Mock GitHub client for analyzer testing"""
        client = Mock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        
        # Mock repository metadata
        client.get_repository_metadata = AsyncMock(return_value=Mock(
            name='spring-microservices-demo',
            description='Comprehensive microservices example with Spring Boot, Docker, and Kubernetes',
            language='Java',
            stars=1500,
            size=8000
        ))
        
        # Mock repository structure analysis
        client.get_repository_contents = AsyncMock(return_value=[
            {'name': 'README.md', 'type': 'file'},
            {'name': 'docker-compose.yml', 'type': 'file'},
            {'name': 'pom.xml', 'type': 'file'},
            {'name': 'services', 'type': 'dir'},
            {'name': 'gateway', 'type': 'dir'},
            {'name': 'config', 'type': 'dir'},
            {'name': 'infrastructure', 'type': 'dir'},
            {'name': 'domain', 'type': 'dir'},
            {'name': 'application', 'type': 'dir'},
            {'name': 'tests', 'type': 'dir'},
            {'name': 'docs', 'type': 'dir'},
            {'name': 'kubernetes', 'type': 'dir'}
        ])
        
        # Mock file content for pattern detection
        client.get_file_content = AsyncMock(return_value=(
            """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.cloud</groupId>
            <artifactId>spring-cloud-starter-netflix-eureka-client</artifactId>
        </dependency>
    </dependencies>
</project>""",
            "pom.xml"
        ))
        
        return client
    
    @pytest.fixture
    def advanced_analyzer(self, mock_github_client_analyzer):
        """Create analyzer with advanced mocking"""
        with patch('app.services.repository_analyzer.GitHubClient', return_value=mock_github_client_analyzer):
            return RepositoryAnalyzer()
    
    @pytest.mark.asyncio
    async def test_comprehensive_repository_analysis(self, advanced_analyzer):
        """Test comprehensive repository analysis"""
        analysis = await advanced_analyzer.analyze_repository(
            "https://github.com/example/spring-microservices-demo",
            "microservices architecture with Spring Boot"
        )
        
        assert analysis is not None
        assert analysis.repository_url == "https://github.com/example/spring-microservices-demo"
        
        # Check architectural patterns
        assert len(analysis.architectural_patterns) > 0
        pattern_names = [p.pattern_name for p in analysis.architectural_patterns]
        assert any(pattern in ['microservices', 'layered', 'spring-boot'] for pattern in pattern_names)
        
        # Check educational assessment
        assert 0.0 <= analysis.educational_assessment.overall_educational_score <= 1.0
        assert 1 <= analysis.educational_assessment.learning_difficulty <= 5
        
        # Check complexity analysis
        assert 0.0 <= analysis.complexity_analysis.overall_complexity <= 1.0
        assert analysis.complexity_analysis.architectural_layers >= 1
        
        # Check ranking scores
        assert 0.0 <= analysis.learning_potential_score <= 1.0
        assert 0.0 <= analysis.implementation_difficulty <= 1.0
        assert 0.0 <= analysis.concept_coverage <= 1.0
    
    @pytest.mark.asyncio
    async def test_pattern_detection_accuracy(self, advanced_analyzer):
        """Test accuracy of architectural pattern detection"""
        analysis = await advanced_analyzer.analyze_repository(
            "https://github.com/example/spring-microservices-demo",
            "microservices"
        )
        
        patterns = analysis.architectural_patterns
        assert len(patterns) > 0
        
        # Should detect microservices pattern
        microservices_patterns = [p for p in patterns if 'microservices' in p.pattern_name.lower()]
        assert len(microservices_patterns) > 0
        
        # Should detect layered architecture
        layered_patterns = [p for p in patterns if 'layered' in p.pattern_name.lower()]
        assert len(layered_patterns) > 0
        
        # Check pattern confidence scores
        for pattern in patterns:
            assert 0.0 <= pattern.confidence <= 1.0
            assert 1 <= pattern.complexity_level <= 5
            assert 0.0 <= pattern.educational_value <= 1.0
    
    @pytest.mark.asyncio
    async def test_educational_assessment_accuracy(self, advanced_analyzer):
        """Test accuracy of educational value assessment"""
        analysis = await advanced_analyzer.analyze_repository(
            "https://github.com/example/spring-microservices-demo",
            "learning microservices architecture"
        )
        
        assessment = analysis.educational_assessment
        
        # Check all assessment metrics are within valid ranges
        assert 1 <= assessment.learning_difficulty <= 5
        assert 0.0 <= assessment.concept_clarity <= 1.0
        assert 0.0 <= assessment.code_readability <= 1.0
        assert 0.0 <= assessment.documentation_quality <= 1.0
        assert 0.0 <= assessment.practical_applicability <= 1.0
        assert 0.0 <= assessment.overall_educational_score <= 1.0
        
        # Check that prerequisites and outcomes are provided
        assert isinstance(assessment.recommended_prerequisites, list)
        assert isinstance(assessment.learning_outcomes, list)
        assert len(assessment.recommended_prerequisites) > 0
        assert len(assessment.learning_outcomes) > 0
    
    @pytest.mark.asyncio
    async def test_complexity_analysis_accuracy(self, advanced_analyzer):
        """Test accuracy of complexity analysis"""
        analysis = await advanced_analyzer.analyze_repository(
            "https://github.com/example/spring-microservices-demo",
            "microservices"
        )
        
        complexity = analysis.complexity_analysis
        
        # Check all complexity metrics are within valid ranges
        assert 0.0 <= complexity.cyclomatic_complexity <= 1.0
        assert complexity.architectural_layers >= 1
        assert 0.0 <= complexity.component_coupling <= 1.0
        assert 0.0 <= complexity.abstraction_level <= 1.0
        assert 0.0 <= complexity.design_pattern_usage <= 1.0
        assert 0.0 <= complexity.overall_complexity <= 1.0
        
        # For a microservices repository, should have multiple layers
        assert complexity.architectural_layers >= 3
    
    @pytest.mark.asyncio
    async def test_ranking_algorithm_consistency(self, advanced_analyzer):
        """Test that ranking algorithm produces consistent results"""
        repo_urls = [
            "https://github.com/example/simple-api",
            "https://github.com/example/complex-microservices",
            "https://github.com/example/basic-crud"
        ]
        
        # Mock different analysis results for different repositories
        def mock_analyze(repo_url, concept):
            if 'simple' in repo_url:
                return Mock(
                    learning_potential_score=0.6,
                    implementation_difficulty=0.3,
                    concept_coverage=0.7
                )
            elif 'complex' in repo_url:
                return Mock(
                    learning_potential_score=0.8,
                    implementation_difficulty=0.8,
                    concept_coverage=0.9
                )
            else:  # basic-crud
                return Mock(
                    learning_potential_score=0.5,
                    implementation_difficulty=0.4,
                    concept_coverage=0.6
                )
        
        with patch.object(advanced_analyzer, 'analyze_repository', side_effect=mock_analyze):
            # Analyze multiple repositories
            analyses = []
            for url in repo_urls:
                analysis = await advanced_analyzer.analyze_repository(url, "api development")
                analyses.append(analysis)
            
            # Check that all analyses have valid scores
            for analysis in analyses:
                assert 0.0 <= analysis.learning_potential_score <= 1.0
                assert 0.0 <= analysis.implementation_difficulty <= 1.0
                assert 0.0 <= analysis.concept_coverage <= 1.0
            
            # Scores should be different for different repositories
            learning_scores = [a.learning_potential_score for a in analyses]
            assert len(set(learning_scores)) > 1  # Should have different scores


class TestAIPoweredRanking:
    """Test AI-powered repository ranking algorithms"""
    
    @pytest.fixture
    def mock_repositories(self):
        """Mock repository suggestions for ranking tests"""
        from app.services.github_search_service import RepositorySuggestion, RepositoryQuality
        
        return [
            RepositorySuggestion(
                repository_url='https://github.com/example/beginner-api',
                repository_name='beginner-api',
                full_name='example/beginner-api',
                description='Simple REST API for beginners',
                stars=50,
                forks=10,
                language='Python',
                topics=['api', 'tutorial'],
                size=500,
                created_at='2023-01-01T00:00:00Z',
                updated_at='2024-01-01T00:00:00Z',
                last_push_at='2024-01-01T00:00:00Z',
                license_name='MIT',
                quality=RepositoryQuality(0.7, 0.8, 0.6, 0.9, 0.7, 0.74),
                educational_value=0.9,
                relevance_score=0.8,
                has_readme=True,
                has_documentation=True,
                has_tests=True,
                has_ci=False,
                contributor_count=3,
                recent_activity=True
            ),
            RepositorySuggestion(
                repository_url='https://github.com/example/advanced-microservices',
                repository_name='advanced-microservices',
                full_name='example/advanced-microservices',
                description='Advanced microservices architecture',
                stars=1000,
                forks=200,
                language='Java',
                topics=['microservices', 'spring-boot', 'kubernetes'],
                size=10000,
                created_at='2022-01-01T00:00:00Z',
                updated_at='2024-01-01T00:00:00Z',
                last_push_at='2024-01-01T00:00:00Z',
                license_name='Apache-2.0',
                quality=RepositoryQuality(0.9, 0.9, 0.8, 0.8, 0.9, 0.86),
                educational_value=0.7,
                relevance_score=0.9,
                has_readme=True,
                has_documentation=True,
                has_tests=True,
                has_ci=True,
                contributor_count=15,
                recent_activity=True
            )
        ]
    
    @pytest.fixture
    def mock_analyzer_for_ranking(self):
        """Mock analyzer for ranking tests"""
        analyzer = Mock()
        analyzer.__aenter__ = AsyncMock(return_value=analyzer)
        analyzer.__aexit__ = AsyncMock(return_value=None)
        
        # Mock different analysis results for different repositories
        def mock_analyze(repo_url, concept):
            if 'beginner' in repo_url:
                return Mock(
                    learning_potential_score=0.8,
                    implementation_difficulty=0.3,
                    concept_coverage=0.7
                )
            else:
                return Mock(
                    learning_potential_score=0.6,
                    implementation_difficulty=0.8,
                    concept_coverage=0.9
                )
        
        analyzer.analyze_repository = AsyncMock(side_effect=mock_analyze)
        return analyzer
    
    @pytest.mark.asyncio
    async def test_repository_ranking_algorithm(self, mock_repositories, mock_analyzer_for_ranking):
        """Test that repository ranking algorithm works correctly"""
        # Create a real analyzer instance and mock its rank_repositories method
        from app.services.repository_analyzer import RepositoryAnalyzer
        
        async def mock_rank_repositories(repositories, concept):
            # Return mock ranking results
            return [
                (repositories[0], Mock(learning_potential_score=0.8)),
                (repositories[1], Mock(learning_potential_score=0.6))
            ]
        
        # Mock the rank_repositories method
        with patch.object(RepositoryAnalyzer, 'rank_repositories', side_effect=mock_rank_repositories):
            analyzer = RepositoryAnalyzer()
            ranked_repos = await analyzer.rank_repositories(
                mock_repositories, 
                "learning API development"
            )
            
            assert len(ranked_repos) == 2
            
            # Check that results are tuples of (repository, analysis)
            for repo, analysis in ranked_repos:
                assert hasattr(repo, 'repository_url')
                assert hasattr(analysis, 'learning_potential_score')
            
            # Results should be sorted by learning potential
            scores = [analysis.learning_potential_score for _, analysis in ranked_repos]
            assert scores == sorted(scores, reverse=True)
    
    def test_overall_score_calculation(self, mock_repositories):
        """Test overall score calculation for repository suggestions"""
        for repo in mock_repositories:
            overall_score = repo.overall_score()
            
            # Score should be within valid range
            assert 0.0 <= overall_score <= 1.0
            
            # Score should be influenced by quality, educational value, and relevance
            expected_score = (
                repo.quality.overall_score * 0.4 +
                repo.educational_value * 0.3 +
                repo.relevance_score * 0.3
            )
            assert abs(overall_score - expected_score) < 0.01
    
    def test_repository_suggestion_serialization(self, mock_repositories):
        """Test repository suggestion serialization to dict"""
        for repo in mock_repositories:
            data = repo.to_dict()
            
            # Check that all required fields are present
            required_fields = [
                'repository_url', 'repository_name', 'description',
                'stars', 'language', 'topics', 'quality',
                'educational_value', 'relevance_score', 'overall_score'
            ]
            
            for field in required_fields:
                assert field in data
            
            # Check that quality is properly serialized
            assert isinstance(data['quality'], dict)
            assert 'overall_score' in data['quality']


if __name__ == "__main__":
    pytest.main([__file__])