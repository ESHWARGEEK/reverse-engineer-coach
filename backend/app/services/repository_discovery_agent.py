"""
Repository Discovery Agent - AI-powered repository discovery service

Features:
- Intelligent search query generation using LLM
- GitHub API integration with rate limiting
- Repository quality assessment and filtering
- Relevance scoring algorithm
- Repository deduplication and ranking logic
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import hashlib
from dataclasses import dataclass, asdict
from enum import Enum

import httpx
from sqlalchemy.orm import Session

from ..llm_provider import LLMProvider
from ..github_client import GitHubClient
from ..models import User, Project
from ..cache import cache_manager

logger = logging.getLogger(__name__)

class DifficultyLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

@dataclass
class RepositorySearchCriteria:
    """Criteria for repository search"""
    technologies: List[str]
    experience_level: str
    learning_goals: List[str]
    time_commitment: str
    learning_style: str
    current_skills: List[str]
    preferred_languages: List[str]
    project_types: List[str] = None
    exclude_forks: bool = True
    min_stars: int = 10
    max_age_months: int = 24
    require_documentation: bool = True

@dataclass
class RepositoryQualityMetrics:
    """Quality metrics for repository assessment"""
    stars: int
    forks: int
    watchers: int
    open_issues: int
    closed_issues: int
    contributors: int
    commits_last_month: int
    has_readme: bool
    has_documentation: bool
    has_tests: bool
    has_ci: bool
    has_license: bool
    code_quality_score: float
    documentation_quality: float
    activity_score: float
    community_score: float

@dataclass
class RepositoryLearningValue:
    """Learning value assessment for repository"""
    complexity_score: float  # 0-100, how complex the codebase is
    educational_value: float  # 0-100, how much can be learned
    skill_match: float  # 0-100, how well it matches user skills
    goal_alignment: float  # 0-100, how well it aligns with learning goals
    beginner_friendly: float  # 0-100, how beginner-friendly it is
    project_structure_quality: float  # 0-100, quality of project organization
    code_examples_quality: float  # 0-100, quality of code examples
    learning_resources: float  # 0-100, availability of learning resources

@dataclass
class DiscoveredRepository:
    """Discovered repository with metadata and scores"""
    id: str
    name: str
    full_name: str
    description: str
    url: str
    clone_url: str
    language: str
    languages: Dict[str, int]
    topics: List[str]
    created_at: datetime
    updated_at: datetime
    pushed_at: datetime
    size: int
    default_branch: str
    
    # Quality metrics
    quality_metrics: RepositoryQualityMetrics
    
    # Learning value
    learning_value: RepositoryLearningValue
    
    # Scoring
    relevance_score: float  # 0-100, overall relevance to user
    final_score: float  # 0-100, final weighted score
    
    # Reasoning
    selection_reasoning: str
    learning_path_suggestions: List[str]
    
    # Metadata
    discovered_at: datetime
    discovery_method: str

class RepositoryDiscoveryAgent:
    """AI-powered repository discovery service"""
    
    def __init__(self, llm_provider: LLMProvider, github_client: GitHubClient):
        self.llm_provider = llm_provider
        self.github_client = github_client
        self.cache_ttl = 3600  # 1 hour cache
        
    async def discover_repositories(
        self,
        criteria: RepositorySearchCriteria,
        user_id: str,
        max_results: int = 10
    ) -> List[DiscoveredRepository]:
        """
        Discover repositories based on user criteria
        
        Args:
            criteria: Search criteria
            user_id: User ID for personalization
            max_results: Maximum number of results to return
            
        Returns:
            List of discovered repositories with scores and metadata
        """
        try:
            logger.info(f"Starting repository discovery for user {user_id}")
            
            # Generate cache key
            cache_key = self._generate_cache_key(criteria, user_id)
            
            # Check cache first
            cached_results = await self._get_cached_results(cache_key)
            if cached_results:
                logger.info("Returning cached repository discovery results")
                return cached_results[:max_results]
            
            # Generate search queries using LLM
            search_queries = await self._generate_search_queries(criteria)
            logger.info(f"Generated {len(search_queries)} search queries")
            
            # Search repositories using multiple queries
            raw_repositories = []
            for query in search_queries:
                repos = await self._search_repositories(query, criteria)
                raw_repositories.extend(repos)
            
            # Deduplicate repositories
            unique_repositories = self._deduplicate_repositories(raw_repositories)
            logger.info(f"Found {len(unique_repositories)} unique repositories")
            
            # Assess repository quality and learning value
            assessed_repositories = []
            for repo in unique_repositories:
                try:
                    assessed_repo = await self._assess_repository(repo, criteria)
                    if assessed_repo:
                        assessed_repositories.append(assessed_repo)
                except Exception as e:
                    logger.warning(f"Failed to assess repository {repo.get('full_name', 'unknown')}: {e}")
                    continue
            
            # Score and rank repositories
            scored_repositories = await self._score_and_rank_repositories(
                assessed_repositories, criteria
            )
            
            # Generate learning insights
            final_repositories = await self._generate_learning_insights(
                scored_repositories, criteria
            )
            
            # Cache results
            await self._cache_results(cache_key, final_repositories)
            
            logger.info(f"Discovery complete: {len(final_repositories)} repositories found")
            return final_repositories[:max_results]
            
        except Exception as e:
            logger.error(f"Repository discovery failed: {e}")
            raise
    
    async def _generate_search_queries(self, criteria: RepositorySearchCriteria) -> List[str]:
        """Generate intelligent search queries using LLM"""
        
        prompt = f"""
        Generate GitHub search queries to find repositories for learning based on these criteria:
        
        Technologies: {', '.join(criteria.technologies)}
        Experience Level: {criteria.experience_level}
        Learning Goals: {', '.join(criteria.learning_goals)}
        Current Skills: {', '.join(criteria.current_skills)}
        Preferred Languages: {', '.join(criteria.preferred_languages)}
        Learning Style: {criteria.learning_style}
        Time Commitment: {criteria.time_commitment}
        
        Generate 3-5 diverse search queries that will find high-quality repositories for learning.
        Focus on:
        1. Educational repositories with good documentation
        2. Real-world projects using the specified technologies
        3. Projects appropriate for the experience level
        4. Repositories with active communities
        
        Return only the search query strings, one per line.
        """
        
        try:
            response = await self.llm_provider.generate_completion(prompt)
            queries = [q.strip() for q in response.split('\n') if q.strip()]
            
            # Add some default queries based on technologies
            default_queries = []
            for tech in criteria.technologies[:3]:  # Limit to avoid too many queries
                default_queries.append(f"{tech} tutorial example")
                default_queries.append(f"{tech} project learning")
            
            # Combine and deduplicate
            all_queries = list(set(queries + default_queries))
            return all_queries[:8]  # Limit to 8 queries max
            
        except Exception as e:
            logger.warning(f"LLM query generation failed, using fallback: {e}")
            # Fallback to simple queries
            fallback_queries = []
            for tech in criteria.technologies:
                fallback_queries.append(f"{tech} example")
                fallback_queries.append(f"{tech} tutorial")
            return fallback_queries[:5]
    
    async def _search_repositories(
        self, 
        query: str, 
        criteria: RepositorySearchCriteria
    ) -> List[Dict[str, Any]]:
        """Search repositories using GitHub API"""
        
        try:
            # Build search parameters
            search_params = {
                'q': query,
                'sort': 'stars',
                'order': 'desc',
                'per_page': 30
            }
            
            # Add language filter if specified
            if criteria.preferred_languages:
                language_filter = ' OR '.join([f"language:{lang}" for lang in criteria.preferred_languages])
                search_params['q'] += f" ({language_filter})"
            
            # Add quality filters
            if criteria.min_stars > 0:
                search_params['q'] += f" stars:>={criteria.min_stars}"
            
            if criteria.exclude_forks:
                search_params['q'] += " fork:false"
            
            # Add recency filter
            if criteria.max_age_months:
                cutoff_date = datetime.now() - timedelta(days=criteria.max_age_months * 30)
                search_params['q'] += f" pushed:>={cutoff_date.strftime('%Y-%m-%d')}"
            
            # Search repositories
            repositories = await self.github_client.search_repositories(search_params)
            return repositories.get('items', [])
            
        except Exception as e:
            logger.error(f"Repository search failed for query '{query}': {e}")
            return []
    
    def _deduplicate_repositories(self, repositories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate repositories"""
        seen = set()
        unique_repos = []
        
        for repo in repositories:
            repo_id = repo.get('id')
            if repo_id and repo_id not in seen:
                seen.add(repo_id)
                unique_repos.append(repo)
        
        return unique_repos
    
    async def _assess_repository(
        self, 
        repo_data: Dict[str, Any], 
        criteria: RepositorySearchCriteria
    ) -> Optional[DiscoveredRepository]:
        """Assess repository quality and learning value"""
        
        try:
            # Get detailed repository information
            full_name = repo_data.get('full_name')
            if not full_name:
                return None
            
            # Get repository details
            repo_details = await self.github_client.get_repository(full_name)
            if not repo_details:
                return None
            
            # Get additional metrics
            contributors = await self.github_client.get_repository_contributors(full_name)
            languages = await self.github_client.get_repository_languages(full_name)
            readme = await self.github_client.get_repository_readme(full_name)
            
            # Assess quality metrics
            quality_metrics = self._assess_quality_metrics(
                repo_details, contributors, readme
            )
            
            # Assess learning value
            learning_value = await self._assess_learning_value(
                repo_details, criteria, readme, languages
            )
            
            # Create discovered repository object
            discovered_repo = DiscoveredRepository(
                id=str(repo_details['id']),
                name=repo_details['name'],
                full_name=repo_details['full_name'],
                description=repo_details.get('description', ''),
                url=repo_details['html_url'],
                clone_url=repo_details['clone_url'],
                language=repo_details.get('language', ''),
                languages=languages or {},
                topics=repo_details.get('topics', []),
                created_at=datetime.fromisoformat(repo_details['created_at'].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(repo_details['updated_at'].replace('Z', '+00:00')),
                pushed_at=datetime.fromisoformat(repo_details['pushed_at'].replace('Z', '+00:00')),
                size=repo_details.get('size', 0),
                default_branch=repo_details.get('default_branch', 'main'),
                quality_metrics=quality_metrics,
                learning_value=learning_value,
                relevance_score=0.0,  # Will be calculated later
                final_score=0.0,  # Will be calculated later
                selection_reasoning="",  # Will be generated later
                learning_path_suggestions=[],  # Will be generated later
                discovered_at=datetime.now(),
                discovery_method="ai_search"
            )
            
            return discovered_repo
            
        except Exception as e:
            logger.error(f"Repository assessment failed: {e}")
            return None
    
    def _assess_quality_metrics(
        self, 
        repo_details: Dict[str, Any], 
        contributors: List[Dict[str, Any]], 
        readme: Optional[str]
    ) -> RepositoryQualityMetrics:
        """Assess repository quality metrics"""
        
        # Basic metrics from GitHub API
        stars = repo_details.get('stargazers_count', 0)
        forks = repo_details.get('forks_count', 0)
        watchers = repo_details.get('watchers_count', 0)
        open_issues = repo_details.get('open_issues_count', 0)
        
        # Contributor metrics
        contributor_count = len(contributors) if contributors else 0
        
        # Documentation assessment
        has_readme = readme is not None and len(readme) > 100
        has_documentation = (
            has_readme and 
            ('documentation' in repo_details.get('topics', []) or
             'docs' in repo_details.get('topics', []) or
             repo_details.get('has_wiki', False))
        )
        
        # License check
        has_license = repo_details.get('license') is not None
        
        # Calculate derived scores
        activity_score = min(100, (stars + forks * 2 + watchers) / 10)
        community_score = min(100, contributor_count * 10)
        code_quality_score = (
            (50 if has_license else 0) +
            (30 if has_readme else 0) +
            (20 if has_documentation else 0)
        )
        documentation_quality = (
            (40 if has_readme else 0) +
            (40 if has_documentation else 0) +
            (20 if repo_details.get('has_wiki', False) else 0)
        )
        
        return RepositoryQualityMetrics(
            stars=stars,
            forks=forks,
            watchers=watchers,
            open_issues=open_issues,
            closed_issues=0,  # Would need additional API call
            contributors=contributor_count,
            commits_last_month=0,  # Would need additional API call
            has_readme=has_readme,
            has_documentation=has_documentation,
            has_tests=False,  # Would need code analysis
            has_ci=False,  # Would need additional API call
            has_license=has_license,
            code_quality_score=code_quality_score,
            documentation_quality=documentation_quality,
            activity_score=activity_score,
            community_score=community_score
        )
    
    async def _assess_learning_value(
        self,
        repo_details: Dict[str, Any],
        criteria: RepositorySearchCriteria,
        readme: Optional[str],
        languages: Dict[str, int]
    ) -> RepositoryLearningValue:
        """Assess learning value using LLM"""
        
        try:
            # Prepare context for LLM
            context = {
                'name': repo_details['name'],
                'description': repo_details.get('description', ''),
                'language': repo_details.get('language', ''),
                'languages': languages,
                'topics': repo_details.get('topics', []),
                'stars': repo_details.get('stargazers_count', 0),
                'size': repo_details.get('size', 0),
                'has_readme': readme is not None,
                'readme_length': len(readme) if readme else 0
            }
            
            prompt = f"""
            Assess the learning value of this repository for a {criteria.experience_level} developer:
            
            Repository: {context['name']}
            Description: {context['description']}
            Primary Language: {context['language']}
            Topics: {', '.join(context['topics'])}
            Stars: {context['stars']}
            Has README: {context['has_readme']}
            
            User Criteria:
            - Technologies: {', '.join(criteria.technologies)}
            - Learning Goals: {', '.join(criteria.learning_goals)}
            - Current Skills: {', '.join(criteria.current_skills)}
            - Experience Level: {criteria.experience_level}
            
            Rate the following aspects from 0-100:
            1. Complexity Score (code complexity)
            2. Educational Value (how much can be learned)
            3. Skill Match (alignment with user skills)
            4. Goal Alignment (alignment with learning goals)
            5. Beginner Friendly (accessibility for beginners)
            6. Project Structure Quality (organization)
            7. Code Examples Quality (quality of examples)
            8. Learning Resources (availability of resources)
            
            Return only a JSON object with these scores.
            """
            
            response = await self.llm_provider.generate_completion(prompt)
            
            try:
                scores = json.loads(response)
                return RepositoryLearningValue(
                    complexity_score=float(scores.get('complexity_score', 50)),
                    educational_value=float(scores.get('educational_value', 50)),
                    skill_match=float(scores.get('skill_match', 50)),
                    goal_alignment=float(scores.get('goal_alignment', 50)),
                    beginner_friendly=float(scores.get('beginner_friendly', 50)),
                    project_structure_quality=float(scores.get('project_structure_quality', 50)),
                    code_examples_quality=float(scores.get('code_examples_quality', 50)),
                    learning_resources=float(scores.get('learning_resources', 50))
                )
            except (json.JSONDecodeError, ValueError):
                # Fallback to heuristic scoring
                return self._heuristic_learning_value_assessment(context, criteria)
                
        except Exception as e:
            logger.warning(f"LLM learning value assessment failed: {e}")
            return self._heuristic_learning_value_assessment(
                {'name': repo_details['name'], 'language': repo_details.get('language', '')}, 
                criteria
            )
    
    def _heuristic_learning_value_assessment(
        self, 
        context: Dict[str, Any], 
        criteria: RepositorySearchCriteria
    ) -> RepositoryLearningValue:
        """Fallback heuristic assessment of learning value"""
        
        # Simple heuristic scoring
        language_match = 80 if context.get('language', '').lower() in [
            tech.lower() for tech in criteria.technologies
        ] else 30
        
        size_score = min(100, max(20, 100 - (context.get('size', 0) / 1000)))  # Prefer medium-sized repos
        
        return RepositoryLearningValue(
            complexity_score=size_score,
            educational_value=language_match,
            skill_match=language_match,
            goal_alignment=50,
            beginner_friendly=70 if criteria.experience_level == 'beginner' else 50,
            project_structure_quality=60,
            code_examples_quality=50,
            learning_resources=40 if context.get('has_readme') else 20
        )
    
    async def _score_and_rank_repositories(
        self,
        repositories: List[DiscoveredRepository],
        criteria: RepositorySearchCriteria
    ) -> List[DiscoveredRepository]:
        """Score and rank repositories based on relevance"""
        
        for repo in repositories:
            # Calculate relevance score (weighted combination of factors)
            quality_weight = 0.3
            learning_weight = 0.5
            popularity_weight = 0.2
            
            # Quality score (average of quality metrics)
            quality_score = (
                repo.quality_metrics.code_quality_score * 0.4 +
                repo.quality_metrics.documentation_quality * 0.3 +
                repo.quality_metrics.activity_score * 0.2 +
                repo.quality_metrics.community_score * 0.1
            )
            
            # Learning score (weighted average of learning metrics)
            learning_score = (
                repo.learning_value.educational_value * 0.25 +
                repo.learning_value.skill_match * 0.25 +
                repo.learning_value.goal_alignment * 0.25 +
                repo.learning_value.beginner_friendly * 0.15 +
                repo.learning_value.learning_resources * 0.1
            )
            
            # Popularity score (normalized stars)
            max_stars = max([r.quality_metrics.stars for r in repositories] + [1])
            popularity_score = (repo.quality_metrics.stars / max_stars) * 100
            
            # Calculate final scores
            repo.relevance_score = (
                quality_score * quality_weight +
                learning_score * learning_weight +
                popularity_score * popularity_weight
            )
            
            repo.final_score = repo.relevance_score
        
        # Sort by final score
        repositories.sort(key=lambda r: r.final_score, reverse=True)
        
        return repositories
    
    async def _generate_learning_insights(
        self,
        repositories: List[DiscoveredRepository],
        criteria: RepositorySearchCriteria
    ) -> List[DiscoveredRepository]:
        """Generate learning insights and recommendations"""
        
        for repo in repositories:
            try:
                # Generate selection reasoning
                reasoning_prompt = f"""
                Explain why this repository is recommended for learning:
                
                Repository: {repo.name}
                Description: {repo.description}
                Language: {repo.language}
                Topics: {', '.join(repo.topics)}
                
                User Profile:
                - Experience: {criteria.experience_level}
                - Technologies: {', '.join(criteria.technologies)}
                - Goals: {', '.join(criteria.learning_goals)}
                
                Scores:
                - Educational Value: {repo.learning_value.educational_value}/100
                - Skill Match: {repo.learning_value.skill_match}/100
                - Quality: {repo.quality_metrics.code_quality_score}/100
                
                Provide a concise explanation (2-3 sentences) of why this repository is valuable for learning.
                """
                
                reasoning = await self.llm_provider.generate_completion(reasoning_prompt)
                repo.selection_reasoning = reasoning.strip()
                
                # Generate learning path suggestions
                path_prompt = f"""
                Suggest 3-5 specific learning activities for this repository:
                
                Repository: {repo.name} - {repo.description}
                User Level: {criteria.experience_level}
                
                Suggest specific, actionable learning activities like:
                - "Study the authentication system in /auth directory"
                - "Implement a similar feature using the patterns shown"
                - "Analyze the testing strategy in /tests"
                
                Return only the suggestions, one per line.
                """
                
                suggestions_response = await self.llm_provider.generate_completion(path_prompt)
                repo.learning_path_suggestions = [
                    s.strip() for s in suggestions_response.split('\n') 
                    if s.strip() and not s.strip().startswith('-')
                ][:5]
                
            except Exception as e:
                logger.warning(f"Failed to generate insights for {repo.name}: {e}")
                repo.selection_reasoning = f"Recommended based on {repo.language} expertise and learning goals."
                repo.learning_path_suggestions = [
                    "Explore the project structure and architecture",
                    "Study the main implementation files",
                    "Review the documentation and examples",
                    "Analyze the testing approach"
                ]
        
        return repositories
    
    def _generate_cache_key(self, criteria: RepositorySearchCriteria, user_id: str) -> str:
        """Generate cache key for search criteria"""
        criteria_dict = asdict(criteria)
        criteria_str = json.dumps(criteria_dict, sort_keys=True)
        cache_data = f"{user_id}:{criteria_str}"
        return f"repo_discovery:{hashlib.md5(cache_data.encode()).hexdigest()}"
    
    async def _get_cached_results(self, cache_key: str) -> Optional[List[DiscoveredRepository]]:
        """Get cached discovery results"""
        try:
            cached_data = await cache_manager.get(cache_key)
            if cached_data:
                # Deserialize cached repositories
                repo_dicts = json.loads(cached_data)
                repositories = []
                for repo_dict in repo_dicts:
                    # Convert dict back to DiscoveredRepository
                    # This is a simplified version - in production, you'd want proper serialization
                    repositories.append(DiscoveredRepository(**repo_dict))
                return repositories
        except Exception as e:
            logger.warning(f"Failed to get cached results: {e}")
        return None
    
    async def _cache_results(self, cache_key: str, repositories: List[DiscoveredRepository]):
        """Cache discovery results"""
        try:
            # Serialize repositories to dict
            repo_dicts = [asdict(repo) for repo in repositories]
            cached_data = json.dumps(repo_dicts, default=str)  # default=str for datetime serialization
            await cache_manager.set(cache_key, cached_data, ttl=self.cache_ttl)
        except Exception as e:
            logger.warning(f"Failed to cache results: {e}")

# Factory function for dependency injection
def create_repository_discovery_agent(
    llm_provider: LLMProvider, 
    github_client: GitHubClient
) -> RepositoryDiscoveryAgent:
    """Create repository discovery agent instance"""
    return RepositoryDiscoveryAgent(llm_provider, github_client)