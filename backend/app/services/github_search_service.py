"""
GitHub Repository Search Service
Implements advanced repository discovery using GitHub Search API with quality analysis and caching.
"""

import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from urllib.parse import quote

import httpx
from app.cache import cache
from app.github_client import GitHubClient, GitHubAPIError

logger = logging.getLogger(__name__)


@dataclass
class SearchFilters:
    """Search filters for repository discovery"""
    min_stars: int = 10
    max_stars: Optional[int] = None
    language: Optional[str] = None
    topics: List[str] = None
    min_size: Optional[int] = None  # KB
    max_size: Optional[int] = None  # KB
    created_after: Optional[str] = None  # ISO date
    updated_after: Optional[str] = None  # ISO date
    has_readme: bool = True
    has_license: bool = True
    is_fork: bool = False
    is_archived: bool = False


@dataclass
class RepositoryQuality:
    """Repository quality metrics"""
    readme_score: float  # 0-1
    documentation_score: float  # 0-1
    code_structure_score: float  # 0-1
    activity_score: float  # 0-1
    community_score: float  # 0-1
    overall_score: float  # 0-1
    
    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class RepositorySuggestion:
    """Repository suggestion with metadata and quality scores"""
    repository_url: str
    repository_name: str
    full_name: str
    description: Optional[str]
    stars: int
    forks: int
    language: str
    topics: List[str]
    size: int  # KB
    created_at: str
    updated_at: str
    last_push_at: Optional[str]
    license_name: Optional[str]
    
    # Quality metrics
    quality: RepositoryQuality
    educational_value: float  # 0-1
    relevance_score: float  # 0-1
    
    # Additional metadata
    has_readme: bool
    has_documentation: bool
    has_tests: bool
    has_ci: bool
    contributor_count: int
    recent_activity: bool
    
    def overall_score(self) -> float:
        """Calculate overall repository score"""
        return (
            self.quality.overall_score * 0.4 +
            self.educational_value * 0.3 +
            self.relevance_score * 0.3
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['overall_score'] = self.overall_score()
        return result


class GitHubSearchService:
    """
    Advanced GitHub repository search service with quality analysis and caching.
    
    Features:
    - Concept-based repository discovery
    - Advanced search filters (stars, activity, language, topics)
    - Repository quality analysis (README, documentation, structure)
    - Intelligent caching to reduce API usage
    - Educational value assessment
    """
    
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize GitHub search service.
        
        Args:
            github_token: GitHub API token for authenticated requests
        """
        self.github_client = GitHubClient(github_token)
        self.cache_ttl = 3600  # 1 hour cache for search results
        self.quality_cache_ttl = 7200  # 2 hours cache for quality analysis
        
        # Educational keywords for relevance scoring
        self.educational_keywords = {
            'architecture': ['microservices', 'mvc', 'mvp', 'clean', 'hexagonal', 'onion', 'ddd'],
            'patterns': ['design-patterns', 'observer', 'factory', 'singleton', 'strategy', 'adapter'],
            'frameworks': ['spring', 'django', 'flask', 'express', 'react', 'vue', 'angular'],
            'concepts': ['api', 'rest', 'graphql', 'websocket', 'auth', 'security', 'testing'],
            'practices': ['tdd', 'bdd', 'ci-cd', 'docker', 'kubernetes', 'monitoring']
        }
    
    async def __aenter__(self):
        await self.github_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.github_client.__aexit__(exc_type, exc_val, exc_tb)
    
    def _parse_learning_concept(self, concept: str) -> Tuple[List[str], List[str], Optional[str]]:
        """
        Parse learning concept into search terms, topics, and language.
        
        Args:
            concept: User's learning concept description
            
        Returns:
            Tuple of (search_terms, topics, language)
        """
        concept_lower = concept.lower()
        
        # Extract programming language
        language = None
        language_patterns = {
            'python': r'\b(python|django|flask|fastapi)\b',
            'javascript': r'\b(javascript|js|node|react|vue|angular|express)\b',
            'java': r'\b(java|spring|maven|gradle)\b',
            'go': r'\b(go|golang|gin|echo)\b',
            'rust': r'\b(rust|cargo|actix|rocket)\b',
            'typescript': r'\b(typescript|ts)\b',
            'csharp': r'\b(c#|csharp|dotnet|asp\.net)\b',
            'php': r'\b(php|laravel|symfony)\b',
            'ruby': r'\b(ruby|rails)\b',
            'kotlin': r'\b(kotlin)\b',
            'swift': r'\b(swift|ios)\b'
        }
        
        for lang, pattern in language_patterns.items():
            if re.search(pattern, concept_lower):
                language = lang
                break
        
        # Extract topics and search terms
        search_terms = []
        topics = []
        
        # Check for architectural patterns
        for category, keywords in self.educational_keywords.items():
            for keyword in keywords:
                if keyword in concept_lower:
                    search_terms.append(keyword)
                    topics.append(keyword)
        
        # Add the original concept as search terms
        concept_words = re.findall(r'\b\w+\b', concept_lower)
        search_terms.extend([word for word in concept_words if len(word) > 2])
        
        # Remove duplicates while preserving order
        search_terms = list(dict.fromkeys(search_terms))
        topics = list(dict.fromkeys(topics))
        
        return search_terms, topics, language
    
    def _build_search_query(self, search_terms: List[str], filters: SearchFilters) -> str:
        """
        Build GitHub search query string.
        
        Args:
            search_terms: List of search terms
            filters: Search filters
            
        Returns:
            GitHub search query string
        """
        query_parts = []
        
        # Add search terms
        if search_terms:
            # Use OR for multiple terms to get broader results
            terms_query = ' OR '.join(f'"{term}"' for term in search_terms[:5])  # Limit to 5 terms
            query_parts.append(f'({terms_query})')
        
        # Add filters
        if filters.min_stars:
            if filters.max_stars:
                query_parts.append(f'stars:{filters.min_stars}..{filters.max_stars}')
            else:
                query_parts.append(f'stars:>={filters.min_stars}')
        
        if filters.language:
            query_parts.append(f'language:{filters.language}')
        
        if filters.topics:
            for topic in filters.topics[:3]:  # Limit to 3 topics
                query_parts.append(f'topic:{topic}')
        
        if filters.min_size:
            if filters.max_size:
                query_parts.append(f'size:{filters.min_size}..{filters.max_size}')
            else:
                query_parts.append(f'size:>={filters.min_size}')
        
        if filters.created_after:
            query_parts.append(f'created:>={filters.created_after}')
        
        if filters.updated_after:
            query_parts.append(f'pushed:>={filters.updated_after}')
        
        if not filters.is_fork:
            query_parts.append('fork:false')
        
        if not filters.is_archived:
            query_parts.append('archived:false')
        
        if filters.has_readme:
            query_parts.append('readme:true')
        
        if filters.has_license:
            query_parts.append('license:true')
        
        return ' '.join(query_parts)
    
    async def _search_repositories(self, query: str, per_page: int = 30) -> List[Dict[str, Any]]:
        """
        Search repositories using GitHub Search API.
        
        Args:
            query: GitHub search query
            per_page: Number of results per page
            
        Returns:
            List of repository data from GitHub API
        """
        try:
            search_endpoint = f"search/repositories"
            params = {
                'q': query,
                'sort': 'stars',
                'order': 'desc',
                'per_page': min(per_page, 100)  # GitHub API limit
            }
            
            response = await self.github_client._make_request(search_endpoint, params)
            return response.get('items', [])
            
        except GitHubAPIError as e:
            logger.error(f"GitHub search failed: {e}")
            return []
    
    async def _analyze_repository_quality(self, repo_data: Dict[str, Any]) -> RepositoryQuality:
        """
        Analyze repository quality based on various metrics.
        
        Args:
            repo_data: Repository data from GitHub API
            
        Returns:
            RepositoryQuality object with scores
        """
        cache_key = f"repo_quality:{repo_data['full_name']}"
        cached_quality = await cache.get(cache_key, namespace="github_quality")
        
        if cached_quality:
            return RepositoryQuality(**cached_quality)
        
        try:
            # Initialize scores
            readme_score = 0.0
            documentation_score = 0.0
            code_structure_score = 0.0
            activity_score = 0.0
            community_score = 0.0
            
            # README analysis
            readme_score = await self._analyze_readme_quality(repo_data)
            
            # Documentation analysis
            documentation_score = await self._analyze_documentation_quality(repo_data)
            
            # Code structure analysis
            code_structure_score = await self._analyze_code_structure(repo_data)
            
            # Activity analysis
            activity_score = self._analyze_activity_score(repo_data)
            
            # Community analysis
            community_score = self._analyze_community_score(repo_data)
            
            # Calculate overall score
            overall_score = (
                readme_score * 0.25 +
                documentation_score * 0.20 +
                code_structure_score * 0.25 +
                activity_score * 0.15 +
                community_score * 0.15
            )
            
            quality = RepositoryQuality(
                readme_score=readme_score,
                documentation_score=documentation_score,
                code_structure_score=code_structure_score,
                activity_score=activity_score,
                community_score=community_score,
                overall_score=overall_score
            )
            
            # Cache the quality analysis
            await cache.set(cache_key, quality.to_dict(), expire=self.quality_cache_ttl, namespace="github_quality")
            
            return quality
            
        except Exception as e:
            logger.error(f"Quality analysis failed for {repo_data['full_name']}: {e}")
            # Return default quality scores
            return RepositoryQuality(
                readme_score=0.5,
                documentation_score=0.5,
                code_structure_score=0.5,
                activity_score=0.5,
                community_score=0.5,
                overall_score=0.5
            )
    
    async def _analyze_readme_quality(self, repo_data: Dict[str, Any]) -> float:
        """Analyze README quality."""
        try:
            # Get README content
            readme_content, _ = await self.github_client.get_file_content(
                repo_data['html_url'], 'README.md'
            )
            
            score = 0.0
            
            # Length check (reasonable documentation)
            if len(readme_content) > 500:
                score += 0.3
            if len(readme_content) > 2000:
                score += 0.2
            
            # Structure checks
            if '# ' in readme_content or '## ' in readme_content:
                score += 0.2  # Has headers
            
            if any(word in readme_content.lower() for word in ['installation', 'setup', 'getting started']):
                score += 0.2  # Has setup instructions
            
            if any(word in readme_content.lower() for word in ['example', 'usage', 'demo']):
                score += 0.1  # Has examples
            
            return min(score, 1.0)
            
        except Exception:
            return 0.0
    
    async def _analyze_documentation_quality(self, repo_data: Dict[str, Any]) -> float:
        """Analyze documentation quality."""
        try:
            # Check for documentation directories/files
            contents = await self.github_client.get_repository_contents(repo_data['html_url'])
            
            score = 0.0
            doc_indicators = ['docs', 'documentation', 'wiki', 'examples', 'tutorials']
            
            for item in contents:
                if item['type'] == 'dir' and any(indicator in item['name'].lower() for indicator in doc_indicators):
                    score += 0.4
                    break
            
            # Check for common documentation files
            doc_files = ['CONTRIBUTING.md', 'CHANGELOG.md', 'API.md', 'GUIDE.md']
            for item in contents:
                if item['name'] in doc_files:
                    score += 0.15
            
            return min(score, 1.0)
            
        except Exception:
            return 0.0
    
    async def _analyze_code_structure(self, repo_data: Dict[str, Any]) -> float:
        """Analyze code structure quality."""
        try:
            contents = await self.github_client.get_repository_contents(repo_data['html_url'])
            
            score = 0.0
            
            # Check for good project structure
            structure_indicators = {
                'src': 0.2, 'lib': 0.2, 'app': 0.2,
                'tests': 0.2, 'test': 0.2, '__tests__': 0.2,
                'config': 0.1, 'scripts': 0.1,
                'package.json': 0.1, 'requirements.txt': 0.1, 'Cargo.toml': 0.1,
                'Dockerfile': 0.1, 'docker-compose.yml': 0.1,
                '.github': 0.1, '.gitignore': 0.1
            }
            
            for item in contents:
                if item['name'] in structure_indicators:
                    score += structure_indicators[item['name']]
            
            return min(score, 1.0)
            
        except Exception:
            return 0.0
    
    def _analyze_activity_score(self, repo_data: Dict[str, Any]) -> float:
        """Analyze repository activity score."""
        try:
            # Check last update
            last_push = datetime.fromisoformat(repo_data['pushed_at'].replace('Z', '+00:00'))
            days_since_update = (datetime.now().astimezone() - last_push).days
            
            score = 0.0
            
            # Recent activity bonus
            if days_since_update <= 30:
                score += 0.4
            elif days_since_update <= 90:
                score += 0.3
            elif days_since_update <= 365:
                score += 0.2
            else:
                score += 0.1
            
            # Repository age (mature but not too old)
            created_at = datetime.fromisoformat(repo_data['created_at'].replace('Z', '+00:00'))
            age_days = (datetime.now().astimezone() - created_at).days
            
            if 90 <= age_days <= 1095:  # 3 months to 3 years
                score += 0.3
            elif age_days > 1095:
                score += 0.2
            else:
                score += 0.1
            
            # Size indicates active development
            if 100 <= repo_data['size'] <= 10000:  # KB
                score += 0.3
            
            return min(score, 1.0)
            
        except Exception:
            return 0.5
    
    def _analyze_community_score(self, repo_data: Dict[str, Any]) -> float:
        """Analyze community engagement score."""
        try:
            score = 0.0
            
            # Stars indicate community interest
            stars = repo_data['stargazers_count']
            if stars >= 1000:
                score += 0.4
            elif stars >= 100:
                score += 0.3
            elif stars >= 10:
                score += 0.2
            else:
                score += 0.1
            
            # Forks indicate community contribution
            forks = repo_data['forks_count']
            if forks >= 100:
                score += 0.3
            elif forks >= 10:
                score += 0.2
            elif forks >= 1:
                score += 0.1
            
            # Issues indicate active community
            if repo_data.get('has_issues', False):
                score += 0.1
            
            # License indicates professional project
            if repo_data.get('license'):
                score += 0.2
            
            return min(score, 1.0)
            
        except Exception:
            return 0.5
    
    def _calculate_educational_value(self, repo_data: Dict[str, Any], search_terms: List[str]) -> float:
        """Calculate educational value of repository."""
        try:
            score = 0.0
            
            # Size sweet spot for learning (not too small, not too large)
            size = repo_data['size']
            if 500 <= size <= 5000:  # KB
                score += 0.3
            elif 100 <= size <= 10000:
                score += 0.2
            else:
                score += 0.1
            
            # Language popularity for learning
            language = repo_data.get('language', '').lower()
            popular_languages = ['python', 'javascript', 'java', 'typescript', 'go', 'rust']
            if language in popular_languages:
                score += 0.2
            
            # Topics relevance
            topics = repo_data.get('topics', [])
            educational_topics = ['tutorial', 'example', 'demo', 'learning', 'education', 'sample']
            for topic in topics:
                if topic in educational_topics:
                    score += 0.1
                if topic in search_terms:
                    score += 0.1
            
            # Description quality
            description = repo_data.get('description', '').lower()
            if description and len(description) > 20:
                score += 0.1
                # Bonus for educational keywords in description
                educational_keywords = ['example', 'tutorial', 'demo', 'sample', 'learning']
                for keyword in educational_keywords:
                    if keyword in description:
                        score += 0.1
                        break
            
            # Star count indicates quality but not too popular (overwhelming)
            stars = repo_data['stargazers_count']
            if 50 <= stars <= 5000:
                score += 0.2
            elif 10 <= stars <= 10000:
                score += 0.1
            
            return min(score, 1.0)
            
        except Exception:
            return 0.5
    
    def _calculate_relevance_score(self, repo_data: Dict[str, Any], search_terms: List[str]) -> float:
        """Calculate relevance score based on search terms."""
        try:
            score = 0.0
            
            # Check name relevance
            name = repo_data['name'].lower()
            for term in search_terms:
                if term in name:
                    score += 0.3
                    break
            
            # Check description relevance
            description = repo_data.get('description', '').lower()
            if description:
                term_matches = sum(1 for term in search_terms if term in description)
                score += min(term_matches * 0.1, 0.4)
            
            # Check topics relevance
            topics = repo_data.get('topics', [])
            topic_matches = sum(1 for term in search_terms if term in topics)
            score += min(topic_matches * 0.1, 0.3)
            
            return min(score, 1.0)
            
        except Exception:
            return 0.5
    
    async def discover_repositories(
        self,
        learning_concept: str,
        filters: Optional[SearchFilters] = None,
        max_results: int = 10
    ) -> List[RepositorySuggestion]:
        """
        Discover repositories based on learning concept.
        
        Args:
            learning_concept: User's learning concept description
            filters: Optional search filters
            max_results: Maximum number of results to return
            
        Returns:
            List of repository suggestions sorted by overall score
        """
        # Generate cache key
        cache_key = hashlib.md5(
            f"{learning_concept}:{filters}:{max_results}".encode()
        ).hexdigest()
        
        # Try cache first
        cached_results = await cache.get(cache_key, namespace="github_discovery")
        if cached_results:
            return [RepositorySuggestion(**item) for item in cached_results]
        
        try:
            # Parse learning concept
            search_terms, topics, language = self._parse_learning_concept(learning_concept)
            
            # Apply default filters if none provided
            if filters is None:
                filters = SearchFilters()
            
            # Override language if detected from concept
            if language and not filters.language:
                filters.language = language
            
            # Add detected topics to filters
            if topics and not filters.topics:
                filters.topics = topics[:3]  # Limit to 3 topics
            
            # Build search query
            query = self._build_search_query(search_terms, filters)
            
            logger.info(f"Searching repositories with query: {query}")
            
            # Search repositories
            repo_results = await self._search_repositories(query, max_results * 2)  # Get more for filtering
            
            # Analyze and score repositories
            suggestions = []
            
            for repo_data in repo_results[:max_results * 2]:  # Process more than needed for better filtering
                try:
                    # Analyze quality
                    quality = await self._analyze_repository_quality(repo_data)
                    
                    # Calculate scores
                    educational_value = self._calculate_educational_value(repo_data, search_terms)
                    relevance_score = self._calculate_relevance_score(repo_data, search_terms)
                    
                    # Check for additional metadata
                    has_readme = bool(repo_data.get('has_readme', False))
                    has_documentation = quality.documentation_score > 0.3
                    has_tests = quality.code_structure_score > 0.5
                    has_ci = '.github' in str(repo_data.get('topics', []))
                    
                    # Create suggestion
                    suggestion = RepositorySuggestion(
                        repository_url=repo_data['html_url'],
                        repository_name=repo_data['name'],
                        full_name=repo_data['full_name'],
                        description=repo_data.get('description'),
                        stars=repo_data['stargazers_count'],
                        forks=repo_data['forks_count'],
                        language=repo_data.get('language', 'Unknown'),
                        topics=repo_data.get('topics', []),
                        size=repo_data['size'],
                        created_at=repo_data['created_at'],
                        updated_at=repo_data['updated_at'],
                        last_push_at=repo_data.get('pushed_at'),
                        license_name=repo_data.get('license', {}).get('name') if repo_data.get('license') else None,
                        quality=quality,
                        educational_value=educational_value,
                        relevance_score=relevance_score,
                        has_readme=has_readme,
                        has_documentation=has_documentation,
                        has_tests=has_tests,
                        has_ci=has_ci,
                        contributor_count=0,  # Would need additional API call
                        recent_activity=quality.activity_score > 0.5
                    )
                    
                    suggestions.append(suggestion)
                    
                except Exception as e:
                    logger.error(f"Failed to process repository {repo_data.get('full_name', 'unknown')}: {e}")
                    continue
            
            # Sort by overall score and limit results
            suggestions.sort(key=lambda x: x.overall_score(), reverse=True)
            final_suggestions = suggestions[:max_results]
            
            # Cache results
            cache_data = [suggestion.to_dict() for suggestion in final_suggestions]
            await cache.set(cache_key, cache_data, expire=self.cache_ttl, namespace="github_discovery")
            
            logger.info(f"Found {len(final_suggestions)} repository suggestions for concept: {learning_concept}")
            
            return final_suggestions
            
        except Exception as e:
            logger.error(f"Repository discovery failed: {e}")
            return []
    
    async def get_repository_suggestions_by_language(
        self,
        language: str,
        concept_keywords: List[str],
        max_results: int = 5
    ) -> List[RepositorySuggestion]:
        """
        Get repository suggestions filtered by programming language.
        
        Args:
            language: Programming language
            concept_keywords: List of concept keywords
            max_results: Maximum number of results
            
        Returns:
            List of repository suggestions
        """
        filters = SearchFilters(
            language=language,
            min_stars=10,
            has_readme=True,
            is_fork=False
        )
        
        concept = ' '.join(concept_keywords)
        return await self.discover_repositories(concept, filters, max_results)
    
    async def refresh_repository_cache(self, learning_concept: str) -> bool:
        """
        Refresh cached repository suggestions for a learning concept.
        
        Args:
            learning_concept: Learning concept to refresh
            
        Returns:
            True if refresh was successful
        """
        try:
            # Invalidate existing cache
            cache_pattern = f"*{hashlib.md5(learning_concept.encode()).hexdigest()[:8]}*"
            await cache.invalidate_pattern(cache_pattern, namespace="github_discovery")
            
            # Fetch fresh results
            await self.discover_repositories(learning_concept)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh repository cache: {e}")
            return False