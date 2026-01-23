"""
GitHub API client for repository validation and metadata fetching.
Implements rate limiting, caching, and authentication handling.
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from urllib.parse import urlparse
import re
import httpx
from app.config import settings
from app.cache import get_redis_client
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class GitHubRepoMetadata:
    """Metadata for a GitHub repository"""
    owner: str
    name: str
    full_name: str
    description: Optional[str]
    language: Optional[str]
    languages: Dict[str, int]
    stars: int
    forks: int
    size: int  # in KB
    default_branch: str
    is_private: bool
    is_fork: bool
    created_at: str
    updated_at: str
    clone_url: str
    html_url: str
    latest_commit_sha: Optional[str] = None
    last_push_at: Optional[str] = None


@dataclass
class RepositoryChange:
    """Represents a change in repository state"""
    change_type: str  # 'commit', 'branch', 'tag', 'metadata'
    old_value: Optional[str]
    new_value: Optional[str]
    detected_at: str
    description: str


@dataclass
class CommitInfo:
    """Information about a Git commit"""
    sha: str
    message: str
    author: str
    author_email: str
    date: str
    url: str

@dataclass
class RateLimitInfo:
    """GitHub API rate limit information"""
    limit: int
    remaining: int
    reset_time: int
    used: int

class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)

class GitHubClient:
    """
    GitHub API client with authentication, rate limiting, and caching.
    
    Features:
    - Repository validation and metadata fetching
    - Rate limit handling with exponential backoff
    - Redis caching for API responses
    - Support for both public and private repositories
    """
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.github_token
        self.base_url = "https://api.github.com"
        self.cache_ttl = 3600  # 1 hour cache TTL
        self.metadata_cache_ttl = 1800  # 30 minutes for metadata
        self.rate_limit_info: Optional[RateLimitInfo] = None
        
        # HTTP client configuration
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ReverseEngineerCoach/1.0"
        }
        
        if self.token:
            headers["Authorization"] = f"token {self.token}"
            
        self.client = httpx.AsyncClient(
            headers=headers,
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def _parse_github_url(self, url: str) -> Tuple[str, str]:
        """
        Parse GitHub URL to extract owner and repository name.
        
        Supports formats:
        - https://github.com/owner/repo
        - https://github.com/owner/repo.git
        - git@github.com:owner/repo.git
        - owner/repo
        """
        # Remove .git suffix if present
        url = url.rstrip('.git')
        
        # Handle SSH format
        if url.startswith('git@github.com:'):
            path = url.replace('git@github.com:', '')
            parts = path.split('/')
            if len(parts) == 2:
                return parts[0], parts[1]
        
        # Handle HTTPS format
        if url.startswith('https://github.com/'):
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 2:
                return path_parts[0], path_parts[1]
        
        # Handle owner/repo format
        if '/' in url and not url.startswith('http'):
            parts = url.split('/')
            if len(parts) == 2:
                return parts[0], parts[1]
        
        raise ValueError(f"Invalid GitHub URL format: {url}")
    
    def _get_cache_key(self, endpoint: str, params: Dict = None) -> str:
        """Generate cache key for API endpoint"""
        key = f"github_api:{endpoint}"
        if params:
            param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            key += f":{param_str}"
        return key
    
    async def _get_cached_response(self, cache_key: str) -> Optional[Dict]:
        """Get cached API response"""
        try:
            from app.cache import cache
            return await cache.get(cache_key, namespace="github_api")
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
        return None
    
    async def _cache_response(self, cache_key: str, data: Dict) -> None:
        """Cache API response"""
        try:
            from app.cache import cache
            await cache.set(cache_key, data, expire=self.cache_ttl, namespace="github_api")
        except Exception as e:
            logger.warning(f"Cache storage failed: {e}")
    
    async def _invalidate_cache_pattern(self, pattern: str) -> None:
        """Invalidate cache entries matching pattern"""
        try:
            from app.cache import cache
            await cache.invalidate_pattern(pattern, namespace="github_api")
        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")
    
    def _update_rate_limit_info(self, headers: Dict[str, str]) -> None:
        """Update rate limit information from response headers"""
        try:
            self.rate_limit_info = RateLimitInfo(
                limit=int(headers.get('x-ratelimit-limit', 0)),
                remaining=int(headers.get('x-ratelimit-remaining', 0)),
                reset_time=int(headers.get('x-ratelimit-reset', 0)),
                used=int(headers.get('x-ratelimit-used', 0))
            )
        except (ValueError, TypeError):
            logger.warning("Failed to parse rate limit headers")
    
    async def _wait_for_rate_limit_reset(self) -> None:
        """Wait for rate limit reset if necessary"""
        if not self.rate_limit_info or self.rate_limit_info.remaining > 0:
            return
        
        current_time = int(time.time())
        wait_time = max(0, self.rate_limit_info.reset_time - current_time + 1)
        
        if wait_time > 0:
            logger.info(f"Rate limit exceeded. Waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time)
    
    async def _make_request(self, endpoint: str, params: Dict = None, use_cache: bool = True) -> Dict:
        """
        Make authenticated request to GitHub API with rate limiting and caching.
        """
        from app.cache import cache
        
        cache_key = self._get_cache_key(endpoint, params)
        
        # Try cache first
        if use_cache:
            cached_response = await self._get_cached_response(cache_key)
            if cached_response:
                return cached_response
        
        # Use debounced request to prevent duplicate API calls
        request_key = f"github_request:{cache_key}"
        
        async def make_api_call():
            # Check rate limit before making request
            await self._wait_for_rate_limit_reset()
            
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            
            try:
                response = await self.client.get(url, params=params or {})
                
                # Update rate limit info
                self._update_rate_limit_info(dict(response.headers))
                
                if response.status_code == 200:
                    data = response.json()
                    # Cache successful responses
                    if use_cache:
                        await self._cache_response(cache_key, data)
                    return data
                
                elif response.status_code == 404:
                    raise GitHubAPIError(
                        "Repository not found or not accessible",
                        status_code=404,
                        response_data=response.json() if response.content else None
                    )
                
                elif response.status_code == 403:
                    error_data = response.json() if response.content else {}
                    if 'rate limit' in error_data.get('message', '').lower():
                        # Handle rate limit exceeded with exponential backoff
                        await self._handle_rate_limit_with_backoff()
                        return await make_api_call()  # Retry after backoff
                    else:
                        raise GitHubAPIError(
                            "Access forbidden - check authentication token",
                            status_code=403,
                            response_data=error_data
                        )
                
                elif response.status_code == 401:
                    raise GitHubAPIError(
                        "Authentication failed - invalid or missing token",
                        status_code=401,
                        response_data=response.json() if response.content else None
                    )
                
                else:
                    raise GitHubAPIError(
                        f"GitHub API error: {response.status_code}",
                        status_code=response.status_code,
                        response_data=response.json() if response.content else None
                    )
                    
            except httpx.RequestError as e:
                raise GitHubAPIError(f"Network error: {str(e)}")
        
        return await cache.debounced_request(request_key, make_api_call)
    
    async def _handle_rate_limit_with_backoff(self, max_retries: int = 3) -> None:
        """Handle rate limiting with exponential backoff"""
        for attempt in range(max_retries):
            if not self.rate_limit_info or self.rate_limit_info.remaining > 0:
                return
            
            # Calculate backoff time (exponential with jitter)
            base_wait = 2 ** attempt
            jitter = 0.1 * base_wait * (0.5 - asyncio.get_event_loop().time() % 1)
            wait_time = base_wait + jitter
            
            logger.warning(f"Rate limit hit, backing off for {wait_time:.2f} seconds (attempt {attempt + 1})")
            await asyncio.sleep(wait_time)
            
            # Check if rate limit has reset
            try:
                await self.get_rate_limit_status()
            except:
                pass  # Continue with backoff if we can't check status
    
    async def validate_repository_url(self, url: str) -> bool:
        """
        Validate if a GitHub repository URL is accessible.
        
        Args:
            url: GitHub repository URL in various formats
            
        Returns:
            bool: True if repository is accessible, False otherwise
            
        Raises:
            GitHubAPIError: For authentication or network errors
            ValueError: For invalid URL formats
        """
        try:
            owner, repo = self._parse_github_url(url)
            await self._make_request(f"repos/{owner}/{repo}")
            return True
        except GitHubAPIError as e:
            if e.status_code == 404:
                return False
            raise
    
    async def get_repository_metadata(self, url: str) -> GitHubRepoMetadata:
        """
        Fetch comprehensive metadata for a GitHub repository.
        
        Args:
            url: GitHub repository URL
            
        Returns:
            GitHubRepoMetadata: Repository metadata
            
        Raises:
            GitHubAPIError: For API errors
            ValueError: For invalid URL formats
        """
        owner, repo = self._parse_github_url(url)
        
        # Fetch repository data
        repo_data = await self._make_request(f"repos/{owner}/{repo}")
        
        # Fetch languages data
        languages_data = await self._make_request(f"repos/{owner}/{repo}/languages")
        
        # Fetch latest commit information
        latest_commit = None
        try:
            commits_data = await self._make_request(f"repos/{owner}/{repo}/commits", {"per_page": 1})
            if commits_data:
                latest_commit = commits_data[0]['sha']
        except GitHubAPIError:
            logger.warning(f"Could not fetch latest commit for {owner}/{repo}")
        
        return GitHubRepoMetadata(
            owner=repo_data['owner']['login'],
            name=repo_data['name'],
            full_name=repo_data['full_name'],
            description=repo_data.get('description'),
            language=repo_data.get('language'),
            languages=languages_data,
            stars=repo_data['stargazers_count'],
            forks=repo_data['forks_count'],
            size=repo_data['size'],
            default_branch=repo_data['default_branch'],
            is_private=repo_data['private'],
            is_fork=repo_data['fork'],
            created_at=repo_data['created_at'],
            updated_at=repo_data['updated_at'],
            clone_url=repo_data['clone_url'],
            html_url=repo_data['html_url'],
            latest_commit_sha=latest_commit,
            last_push_at=repo_data.get('pushed_at')
        )
    
    async def get_repository_contents(self, url: str, path: str = "", ref: Optional[str] = None) -> List[Dict]:
        """
        Get contents of a repository directory.
        
        Args:
            url: GitHub repository URL
            path: Directory path (empty for root)
            ref: Git reference (branch, tag, or commit SHA)
            
        Returns:
            List[Dict]: List of file/directory information
        """
        owner, repo = self._parse_github_url(url)
        
        params = {}
        if ref:
            params['ref'] = ref
        if path:
            params['path'] = path
            
        endpoint = f"repos/{owner}/{repo}/contents"
        if path:
            endpoint += f"/{path}"
            
        return await self._make_request(endpoint, params)
    
    async def get_file_content(self, url: str, file_path: str, ref: Optional[str] = None) -> Tuple[str, str]:
        """
        Get content of a specific file.
        
        Args:
            url: GitHub repository URL
            file_path: Path to the file
            ref: Git reference (branch, tag, or commit SHA)
            
        Returns:
            Tuple[str, str]: (file_content, commit_sha)
        """
        owner, repo = self._parse_github_url(url)
        
        params = {}
        if ref:
            params['ref'] = ref
            
        file_data = await self._make_request(f"repos/{owner}/{repo}/contents/{file_path}", params)
        
        if file_data.get('type') != 'file':
            raise GitHubAPIError(f"Path {file_path} is not a file")
        
        # Decode base64 content
        import base64
        content = base64.b64decode(file_data['content']).decode('utf-8')
        
        return content, file_data['sha']
    
    async def get_rate_limit_status(self) -> RateLimitInfo:
        """Get current rate limit status"""
        data = await self._make_request("rate_limit", use_cache=False)
        
        core_info = data['resources']['core']
        return RateLimitInfo(
            limit=core_info['limit'],
            remaining=core_info['remaining'],
            reset_time=core_info['reset'],
            used=core_info['used']
        )
    
    def get_permalink_url(self, url: str, file_path: str, line_number: Optional[int] = None, 
                         commit_sha: Optional[str] = None) -> str:
        """
        Generate a stable GitHub permalink for a file or specific line.
        
        Args:
            url: GitHub repository URL
            file_path: Path to the file
            line_number: Optional line number
            commit_sha: Optional commit SHA for stable linking
            
        Returns:
            str: GitHub permalink URL
        """
        owner, repo = self._parse_github_url(url)
        
        if commit_sha:
            base_url = f"https://github.com/{owner}/{repo}/blob/{commit_sha}/{file_path}"
        else:
            base_url = f"https://github.com/{owner}/{repo}/blob/main/{file_path}"
        
        if line_number:
            base_url += f"#L{line_number}"
            
        return base_url
    
    async def detect_repository_changes(self, url: str, last_known_commit: Optional[str] = None) -> List[RepositoryChange]:
        """
        Detect changes in repository since last known state.
        
        Args:
            url: GitHub repository URL
            last_known_commit: Last known commit SHA
            
        Returns:
            List[RepositoryChange]: List of detected changes
        """
        owner, repo = self._parse_github_url(url)
        changes = []
        current_time = time.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        try:
            # Get current repository metadata
            current_metadata = await self.get_repository_metadata(url)
            
            # Check for new commits
            if last_known_commit and current_metadata.latest_commit_sha != last_known_commit:
                # Get commits since last known commit
                try:
                    commits_data = await self._make_request(
                        f"repos/{owner}/{repo}/commits",
                        {"since": last_known_commit, "per_page": 10}
                    )
                    
                    for commit_data in commits_data:
                        if commit_data['sha'] != last_known_commit:
                            changes.append(RepositoryChange(
                                change_type='commit',
                                old_value=last_known_commit,
                                new_value=commit_data['sha'],
                                detected_at=current_time,
                                description=f"New commit: {commit_data['commit']['message'][:100]}"
                            ))
                            
                except GitHubAPIError as e:
                    logger.warning(f"Could not fetch commits since {last_known_commit}: {e}")
            
            # Check for metadata changes (cached comparison)
            from app.cache import cache
            cached_metadata = await cache.get(f"github_metadata:{owner}/{repo}", namespace="github_metadata")
            
            if cached_metadata:
                # Compare key metadata fields
                if cached_metadata.get('stargazers_count') != current_metadata.stars:
                    changes.append(RepositoryChange(
                        change_type='metadata',
                        old_value=str(cached_metadata.get('stargazers_count', 0)),
                        new_value=str(current_metadata.stars),
                        detected_at=current_time,
                        description=f"Stars changed from {cached_metadata.get('stargazers_count', 0)} to {current_metadata.stars}"
                    ))
                
                if cached_metadata.get('description') != current_metadata.description:
                    changes.append(RepositoryChange(
                        change_type='metadata',
                        old_value=cached_metadata.get('description', ''),
                        new_value=current_metadata.description or '',
                        detected_at=current_time,
                        description="Repository description updated"
                    ))
            
            # Cache current metadata for future comparisons
            from app.cache import cache
            await cache.set(f"github_metadata:{owner}/{repo}", {
                'stargazers_count': current_metadata.stars,
                'description': current_metadata.description,
                'updated_at': current_metadata.updated_at,
                'latest_commit_sha': current_metadata.latest_commit_sha
            }, expire=self.metadata_cache_ttl, namespace="github_metadata")
            
        except GitHubAPIError as e:
            logger.error(f"Failed to detect repository changes: {e}")
            
        return changes
    
    async def refresh_repository_cache(self, url: str) -> bool:
        """
        Refresh cached repository data by invalidating cache and fetching fresh data.
        
        Args:
            url: GitHub repository URL
            
        Returns:
            bool: True if refresh was successful
        """
        try:
            owner, repo = self._parse_github_url(url)
            
            # Invalidate relevant cache entries using pattern matching
            cache_patterns = [
                f"repos/{owner}/{repo}*",
                f"github_metadata:{owner}/{repo}*"
            ]
            
            for pattern in cache_patterns:
                await self._invalidate_cache_pattern(pattern)
            
            # Fetch fresh metadata to repopulate cache
            await self.get_repository_metadata(url)
            
            logger.info(f"Successfully refreshed cache for repository {owner}/{repo}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh repository cache: {e}")
            return False
    
    async def get_stable_file_link(self, url: str, file_path: str, line_number: Optional[int] = None) -> str:
        """
        Generate a stable link to a file using the latest commit SHA.
        
        Args:
            url: GitHub repository URL
            file_path: Path to the file
            line_number: Optional line number
            
        Returns:
            str: Stable GitHub permalink with commit SHA
        """
        try:
            # Get latest commit SHA for stable linking
            owner, repo = self._parse_github_url(url)
            commits_data = await self._make_request(f"repos/{owner}/{repo}/commits", {"per_page": 1})
            
            if commits_data:
                latest_commit_sha = commits_data[0]['sha']
                return self.get_permalink_url(url, file_path, line_number, latest_commit_sha)
            else:
                # Fallback to branch-based link
                return self.get_permalink_url(url, file_path, line_number)
                
        except GitHubAPIError as e:
            logger.warning(f"Could not get stable link, using branch-based link: {e}")
            return self.get_permalink_url(url, file_path, line_number)
    
    async def get_commit_info(self, url: str, commit_sha: str) -> CommitInfo:
        """
        Get detailed information about a specific commit.
        
        Args:
            url: GitHub repository URL
            commit_sha: Commit SHA
            
        Returns:
            CommitInfo: Commit information
        """
        owner, repo = self._parse_github_url(url)
        commit_data = await self._make_request(f"repos/{owner}/{repo}/commits/{commit_sha}")
        
        return CommitInfo(
            sha=commit_data['sha'],
            message=commit_data['commit']['message'],
            author=commit_data['commit']['author']['name'],
            author_email=commit_data['commit']['author']['email'],
            date=commit_data['commit']['author']['date'],
            url=commit_data['html_url']
        )
    
    async def get_repository_activity_summary(self, url: str, days: int = 30) -> Dict[str, Any]:
        """
        Get a summary of repository activity over the specified period.
        
        Args:
            url: GitHub repository URL
            days: Number of days to look back
            
        Returns:
            Dict containing activity summary
        """
        owner, repo = self._parse_github_url(url)
        
        # Calculate date range
        from datetime import datetime, timedelta
        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        try:
            # Get recent commits
            commits_data = await self._make_request(
                f"repos/{owner}/{repo}/commits",
                {"since": since_date, "per_page": 100}
            )
            
            # Get recent issues (if accessible)
            issues_data = []
            try:
                issues_data = await self._make_request(
                    f"repos/{owner}/{repo}/issues",
                    {"since": since_date, "state": "all", "per_page": 100}
                )
            except GitHubAPIError:
                # Issues might not be accessible for private repos
                pass
            
            # Analyze activity
            commit_count = len(commits_data)
            unique_authors = len(set(commit['commit']['author']['name'] for commit in commits_data))
            
            # Count issues vs pull requests
            issues_count = len([issue for issue in issues_data if 'pull_request' not in issue])
            prs_count = len([issue for issue in issues_data if 'pull_request' in issue])
            
            return {
                'period_days': days,
                'commit_count': commit_count,
                'unique_contributors': unique_authors,
                'issues_count': issues_count,
                'pull_requests_count': prs_count,
                'total_activity_items': commit_count + issues_count + prs_count,
                'most_recent_commit': commits_data[0] if commits_data else None,
                'activity_level': self._calculate_activity_level(commit_count, days)
            }
            
        except GitHubAPIError as e:
            logger.error(f"Failed to get repository activity summary: {e}")
            return {
                'period_days': days,
                'error': str(e),
                'activity_level': 'unknown'
            }
    
    def _calculate_activity_level(self, commit_count: int, days: int) -> str:
        """Calculate activity level based on commit frequency"""
        commits_per_day = commit_count / days
        
        if commits_per_day >= 2:
            return 'very_high'
        elif commits_per_day >= 1:
            return 'high'
        elif commits_per_day >= 0.5:
            return 'moderate'
        elif commits_per_day >= 0.1:
            return 'low'
        else:
            return 'very_low'
    
    async def validate_file_exists(self, url: str, file_path: str, ref: Optional[str] = None) -> bool:
        """
        Validate that a specific file exists in the repository.
        
        Args:
            url: GitHub repository URL
            file_path: Path to the file
            ref: Git reference (branch, tag, or commit SHA)
            
        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            await self.get_file_content(url, file_path, ref)
            return True
        except GitHubAPIError as e:
            if e.status_code == 404:
                return False
            raise

# Convenience function for creating GitHub client
async def create_github_client(token: Optional[str] = None) -> GitHubClient:
    """Create and return a GitHub client instance"""
    return GitHubClient(token)