"""
MCP (Model Context Protocol) client for structured repository analysis.
Implements intelligent file filtering, code snippet extraction, and GitHub permalink generation.
"""

import asyncio
import re
from typing import Dict, List, Optional, Tuple, Set, Any, AsyncGenerator
from dataclasses import dataclass
from pathlib import Path
import ast
import logging
from app.github_client import GitHubClient, GitHubRepoMetadata
from app.config import settings

logger = logging.getLogger(__name__)

@dataclass
class CodeSnippet:
    """Represents a code snippet with metadata"""
    file_path: str
    content: str
    start_line: int
    end_line: int
    language: str
    snippet_type: str  # 'interface', 'class', 'struct', 'function', 'type'
    name: str
    github_permalink: str
    commit_sha: str
    architectural_significance: float  # 0.0 to 1.0 score

@dataclass
class RepositoryAnalysis:
    """Results of repository analysis"""
    repository_url: str
    metadata: GitHubRepoMetadata
    total_files_analyzed: int
    relevant_files: List[str]
    code_snippets: List[CodeSnippet]
    architecture_patterns: List[str]
    primary_language: str
    complexity_score: float

class ArchitectureTopicFilter:
    """Filters files and code based on architecture topics"""
    
    # Architecture topic to file pattern mappings
    TOPIC_PATTERNS = {
        'distributed_systems': {
            'keywords': ['cluster', 'node', 'consensus', 'raft', 'gossip', 'partition', 'shard', 'replica'],
            'file_patterns': ['*cluster*', '*node*', '*consensus*', '*raft*', '*gossip*', '*partition*', '*shard*'],
            'directories': ['cluster', 'consensus', 'distributed', 'replication', 'partitioning']
        },
        'microservices': {
            'keywords': ['service', 'gateway', 'discovery', 'registry', 'circuit', 'breaker', 'load', 'balance'],
            'file_patterns': ['*service*', '*gateway*', '*discovery*', '*registry*', '*circuit*', '*balance*'],
            'directories': ['services', 'gateway', 'discovery', 'registry', 'loadbalancer']
        },
        'data_engineering': {
            'keywords': ['pipeline', 'stream', 'batch', 'etl', 'transform', 'ingest', 'queue', 'buffer'],
            'file_patterns': ['*pipeline*', '*stream*', '*batch*', '*etl*', '*transform*', '*queue*'],
            'directories': ['pipeline', 'streaming', 'batch', 'etl', 'ingestion', 'processing']
        },
        'platform_engineering': {
            'keywords': ['deploy', 'orchestrat', 'container', 'kubernetes', 'docker', 'helm', 'terraform'],
            'file_patterns': ['*deploy*', '*orchestrat*', '*container*', '*k8s*', '*helm*', '*terraform*'],
            'directories': ['deploy', 'orchestration', 'containers', 'k8s', 'helm', 'terraform', 'infrastructure']
        },
        'caching': {
            'keywords': ['cache', 'redis', 'memcache', 'lru', 'ttl', 'evict'],
            'file_patterns': ['*cache*', '*redis*', '*memcache*', '*lru*'],
            'directories': ['cache', 'caching', 'redis', 'memory']
        },
        'database': {
            'keywords': ['database', 'sql', 'nosql', 'index', 'query', 'transaction', 'acid'],
            'file_patterns': ['*db*', '*database*', '*sql*', '*index*', '*query*', '*transaction*'],
            'directories': ['database', 'db', 'sql', 'storage', 'persistence']
        }
    }
    
    @classmethod
    def get_relevant_patterns(cls, architecture_topic: str) -> Dict[str, List[str]]:
        """Get file patterns for a specific architecture topic"""
        topic_key = architecture_topic.lower().replace(' ', '_').replace('-', '_')
        return cls.TOPIC_PATTERNS.get(topic_key, {
            'keywords': [],
            'file_patterns': [],
            'directories': []
        })
    
    @classmethod
    def is_file_relevant(cls, file_path: str, architecture_topic: str) -> Tuple[bool, float]:
        """
        Check if a file is relevant to the architecture topic.
        Returns (is_relevant, relevance_score)
        """
        patterns = cls.get_relevant_patterns(architecture_topic)
        file_path_lower = file_path.lower()
        file_name = Path(file_path).name.lower()
        
        relevance_score = 0.0
        
        # Check directory relevance
        for directory in patterns.get('directories', []):
            if directory in file_path_lower:
                relevance_score += 0.4
        
        # Check file pattern relevance
        for pattern in patterns.get('file_patterns', []):
            pattern_clean = pattern.replace('*', '')
            if pattern_clean in file_name:
                relevance_score += 0.3
        
        # Check keyword relevance in file path
        for keyword in patterns.get('keywords', []):
            if keyword in file_path_lower:
                relevance_score += 0.2
        
        # Boost for certain file types that are architecturally significant
        if any(file_path_lower.endswith(ext) for ext in ['.go', '.rs', '.py', '.java', '.ts', '.js']):
            if any(term in file_name for term in ['interface', 'service', 'client', 'server', 'handler', 'controller']):
                relevance_score += 0.3
        
        return relevance_score > 0.3, min(relevance_score, 1.0)

class CodeAnalyzer:
    """Analyzes code to extract structural elements"""
    
    @staticmethod
    def extract_python_structures(content: str, file_path: str) -> List[Dict]:
        """Extract classes, functions, and interfaces from Python code"""
        structures = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    structures.append({
                        'type': 'class',
                        'name': node.name,
                        'line_start': node.lineno,
                        'line_end': getattr(node, 'end_lineno', node.lineno + 10),
                        'docstring': ast.get_docstring(node),
                        'is_interface': any(base.id in ['ABC', 'Protocol'] for base in node.bases if isinstance(base, ast.Name))
                    })
                
                elif isinstance(node, ast.FunctionDef):
                    # Only include functions that look architecturally significant
                    if any(keyword in node.name.lower() for keyword in ['handle', 'process', 'execute', 'run', 'start', 'stop', 'init']):
                        structures.append({
                            'type': 'function',
                            'name': node.name,
                            'line_start': node.lineno,
                            'line_end': getattr(node, 'end_lineno', node.lineno + 5),
                            'docstring': ast.get_docstring(node),
                            'is_async': isinstance(node, ast.AsyncFunctionDef)
                        })
        
        except SyntaxError:
            logger.warning(f"Failed to parse Python file: {file_path}")
        
        return structures
    
    @staticmethod
    def extract_go_structures(content: str, file_path: str) -> List[Dict]:
        """Extract structs, interfaces, and functions from Go code"""
        structures = []
        lines = content.split('\n')
        
        # Simple regex-based extraction for Go
        struct_pattern = re.compile(r'^type\s+(\w+)\s+struct\s*{', re.MULTILINE)
        interface_pattern = re.compile(r'^type\s+(\w+)\s+interface\s*{', re.MULTILINE)
        func_pattern = re.compile(r'^func\s+(?:\([^)]*\)\s+)?(\w+)\s*\(', re.MULTILINE)
        
        # Find structs
        for match in struct_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            structures.append({
                'type': 'struct',
                'name': match.group(1),
                'line_start': line_num,
                'line_end': line_num + 10,  # Approximate
                'docstring': None
            })
        
        # Find interfaces
        for match in interface_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            structures.append({
                'type': 'interface',
                'name': match.group(1),
                'line_start': line_num,
                'line_end': line_num + 10,  # Approximate
                'docstring': None
            })
        
        # Find significant functions
        for match in func_pattern.finditer(content):
            func_name = match.group(1)
            if any(keyword in func_name.lower() for keyword in ['handle', 'process', 'execute', 'run', 'start', 'stop', 'new']):
                line_num = content[:match.start()].count('\n') + 1
                structures.append({
                    'type': 'function',
                    'name': func_name,
                    'line_start': line_num,
                    'line_end': line_num + 5,  # Approximate
                    'docstring': None
                })
        
        return structures
    
    @staticmethod
    def extract_typescript_structures(content: str, file_path: str) -> List[Dict]:
        """Extract interfaces, classes, and types from TypeScript code"""
        structures = []
        
        # Simple regex-based extraction for TypeScript
        interface_pattern = re.compile(r'^(?:export\s+)?interface\s+(\w+)', re.MULTILINE)
        class_pattern = re.compile(r'^(?:export\s+)?class\s+(\w+)', re.MULTILINE)
        type_pattern = re.compile(r'^(?:export\s+)?type\s+(\w+)', re.MULTILINE)
        
        # Find interfaces
        for match in interface_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            structures.append({
                'type': 'interface',
                'name': match.group(1),
                'line_start': line_num,
                'line_end': line_num + 10,  # Approximate
                'docstring': None
            })
        
        # Find classes
        for match in class_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            structures.append({
                'type': 'class',
                'name': match.group(1),
                'line_start': line_num,
                'line_end': line_num + 15,  # Approximate
                'docstring': None
            })
        
        # Find type definitions
        for match in type_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            structures.append({
                'type': 'type',
                'name': match.group(1),
                'line_start': line_num,
                'line_end': line_num + 5,  # Approximate
                'docstring': None
            })
        
        return structures
    
    @classmethod
    def extract_structures(cls, content: str, file_path: str, language: str) -> List[Dict]:
        """Extract structural elements based on file language"""
        if language.lower() == 'python':
            return cls.extract_python_structures(content, file_path)
        elif language.lower() == 'go':
            return cls.extract_go_structures(content, file_path)
        elif language.lower() in ['typescript', 'javascript']:
            return cls.extract_typescript_structures(content, file_path)
        else:
            # Generic extraction for other languages
            return []

class MCPClient:
    """
    MCP Client for structured repository analysis and code fetching.
    
    Features:
    - Intelligent file filtering based on architecture topics
    - Code snippet extraction with GitHub permalink generation
    - Architectural pattern recognition
    - Complexity analysis and scoring
    - Lazy loading for large datasets
    - Performance optimizations with caching
    """
    
    def __init__(self, github_client: Optional[GitHubClient] = None, github_token: Optional[str] = None):
        if github_token:
            self.github_client = GitHubClient(github_token)
        else:
            self.github_client = github_client or GitHubClient()
        self.max_files_limit = 50  # Maximum files to analyze per repository
        self.max_file_size = 100 * 1024  # 100KB max file size
        self.batch_size = 10  # Files to process in each batch for lazy loading
        
        # Performance tracking
        self.analysis_stats = {
            'files_analyzed': 0,
            'snippets_extracted': 0,
            'cache_hits': 0,
            'api_calls': 0
        }
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self.github_client, '__aexit__'):
            await self.github_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def _analyze_file_cached(self, repo_url: str, file_path: str, architecture_topic: str, 
                                 commit_sha: str) -> List[CodeSnippet]:
        """Analyze a single file with caching support"""
        from app.cache import cache, cache_result
        
        # Generate cache key for file analysis
        cache_key = f"file_analysis:{self._hash_file_key(repo_url, file_path, commit_sha, architecture_topic)}"
        
        # Try to get from cache first
        cached_result = await cache.get(cache_key, namespace="mcp_analysis")
        if cached_result:
            self.analysis_stats['cache_hits'] += 1
            # Convert dict back to CodeSnippet objects
            return [CodeSnippet(**snippet_data) for snippet_data in cached_result]
        
        # Analyze file if not cached
        snippets = await self._analyze_file(repo_url, file_path, architecture_topic, commit_sha)
        
        # Cache the results (convert CodeSnippet objects to dicts)
        if snippets:
            snippet_dicts = [snippet.__dict__ for snippet in snippets]
            await cache.set(cache_key, snippet_dicts, expire=7200, namespace="mcp_analysis")  # 2 hour cache
        
        self.analysis_stats['api_calls'] += 1
        return snippets
    
    def _hash_file_key(self, repo_url: str, file_path: str, commit_sha: str, architecture_topic: str) -> str:
        """Generate hash key for file analysis caching"""
        import hashlib
        key_data = f"{repo_url}:{file_path}:{commit_sha}:{architecture_topic}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def _analyze_files_lazy(self, repo_url: str, relevant_files: List[Tuple[str, float]], 
                                architecture_topic: str, commit_sha: str) -> AsyncGenerator[List[CodeSnippet], None]:
        """Lazy loading generator for file analysis"""
        
        for i in range(0, len(relevant_files), self.batch_size):
            batch = relevant_files[i:i + self.batch_size]
            batch_snippets = []
            
            # Process batch concurrently
            tasks = []
            for file_path, relevance_score in batch:
                task = self._analyze_file_cached(repo_url, file_path, architecture_topic, commit_sha)
                tasks.append(task)
            
            # Wait for batch completion
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.warning(f"File analysis failed: {result}")
                    continue
                
                if isinstance(result, list):
                    batch_snippets.extend(result)
                    self.analysis_stats['files_analyzed'] += 1
            
            self.analysis_stats['snippets_extracted'] += len(batch_snippets)
            
            # Yield batch results
            if batch_snippets:
                yield batch_snippets
            
            # Small delay between batches to prevent overwhelming the API
            await asyncio.sleep(0.2)
    
    async def analyze_repository_lazy(self, repo_url: str, architecture_topic: str, 
                                    max_snippets: Optional[int] = None) -> AsyncGenerator[RepositoryAnalysis, None]:
        """
        Perform repository analysis with lazy loading for better performance.
        
        Args:
            repo_url: GitHub repository URL
            architecture_topic: Architecture specialization
            max_snippets: Maximum number of snippets to extract (None for no limit)
            
        Yields:
            RepositoryAnalysis: Partial analysis results as they become available
        """
        logger.info(f"Starting lazy repository analysis: {repo_url} for topic: {architecture_topic}")
        
        # Get repository metadata (cached)
        from app.cache import cache_result
        
        @cache_result(expire=1800, namespace="github_metadata")  # 30 min cache
        async def get_cached_metadata():
            return await self.github_client.get_repository_metadata(repo_url)
        
        metadata = await get_cached_metadata()
        
        # Get the latest commit SHA for stable linking
        contents = await self.github_client.get_repository_contents(repo_url)
        commit_sha = contents[0]['sha'] if contents else metadata.default_branch
        
        # Get relevant files
        relevant_files = await self._get_relevant_files(repo_url, architecture_topic)
        logger.info(f"Found {len(relevant_files)} relevant files for lazy analysis")
        
        # Initialize analysis state
        all_snippets = []
        analyzed_files = []
        
        # Process files in batches using lazy loading
        async for batch_snippets in self._analyze_files_lazy(repo_url, relevant_files, architecture_topic, commit_sha):
            all_snippets.extend(batch_snippets)
            
            # Check if we've reached the snippet limit
            if max_snippets and len(all_snippets) >= max_snippets:
                all_snippets = all_snippets[:max_snippets]
                break
            
            # Sort snippets by architectural significance
            all_snippets.sort(key=lambda x: x.architectural_significance, reverse=True)
            
            # Yield partial results
            partial_analysis = RepositoryAnalysis(
                repository_url=repo_url,
                metadata=metadata,
                total_files_analyzed=self.analysis_stats['files_analyzed'],
                relevant_files=[f[0] for f in relevant_files[:self.analysis_stats['files_analyzed']]],
                code_snippets=all_snippets,
                architecture_patterns=self._detect_architecture_patterns(all_snippets, architecture_topic),
                primary_language=metadata.language or 'unknown',
                complexity_score=self._calculate_complexity_score(metadata, all_snippets)
            )
            
            yield partial_analysis
        
        # Final analysis with complete results
        final_analysis = RepositoryAnalysis(
            repository_url=repo_url,
            metadata=metadata,
            total_files_analyzed=self.analysis_stats['files_analyzed'],
            relevant_files=[f[0] for f in relevant_files],
            code_snippets=all_snippets,
            architecture_patterns=self._detect_architecture_patterns(all_snippets, architecture_topic),
            primary_language=metadata.language or 'unknown',
            complexity_score=self._calculate_complexity_score(metadata, all_snippets)
        )
        
        logger.info(f"Lazy analysis complete: {len(all_snippets)} snippets extracted, "
                   f"complexity score: {final_analysis.complexity_score:.2f}")
        
        yield final_analysis
    
    async def get_analysis_stats(self) -> Dict[str, Any]:
        """Get performance statistics for the analysis"""
        return {
            **self.analysis_stats,
            'cache_hit_rate': self.analysis_stats['cache_hits'] / max(self.analysis_stats['api_calls'], 1),
            'avg_snippets_per_file': self.analysis_stats['snippets_extracted'] / max(self.analysis_stats['files_analyzed'], 1)
        }
    
    def _calculate_architectural_significance(self, structure: Dict, file_path: str, 
                                           architecture_topic: str) -> float:
        """Calculate architectural significance score for a code structure"""
        score = 0.0
        
        # Base score for structure type
        type_scores = {
            'interface': 0.8,
            'class': 0.6,
            'struct': 0.7,
            'type': 0.5,
            'function': 0.3
        }
        score += type_scores.get(structure.get('type', ''), 0.2)
        
        # Boost for architecture-relevant names
        name = structure.get('name', '').lower()
        patterns = ArchitectureTopicFilter.get_relevant_patterns(architecture_topic)
        
        for keyword in patterns.get('keywords', []):
            if keyword in name:
                score += 0.2
        
        # Boost for common architectural patterns
        architectural_terms = ['handler', 'service', 'client', 'server', 'manager', 'controller', 'processor']
        for term in architectural_terms:
            if term in name:
                score += 0.15
        
        # Boost for interfaces and abstract classes
        if structure.get('is_interface') or structure.get('type') == 'interface':
            score += 0.3
        
        return min(score, 1.0)
    
    def _detect_language(self, file_path: str, content: str) -> str:
        """Detect programming language from file extension and content"""
        extension = Path(file_path).suffix.lower()
        
        extension_map = {
            '.py': 'python',
            '.go': 'go',
            '.ts': 'typescript',
            '.js': 'javascript',
            '.java': 'java',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp'
        }
        
        return extension_map.get(extension, 'unknown')
    
    async def _analyze_file(self, repo_url: str, file_path: str, architecture_topic: str, 
                          commit_sha: str) -> List[CodeSnippet]:
        """Analyze a single file and extract relevant code snippets"""
        try:
            content, file_sha = await self.github_client.get_file_content(repo_url, file_path, commit_sha)
            
            # Skip files that are too large
            if len(content) > self.max_file_size:
                logger.info(f"Skipping large file: {file_path} ({len(content)} bytes)")
                return []
            
            language = self._detect_language(file_path, content)
            structures = CodeAnalyzer.extract_structures(content, file_path, language)
            
            snippets = []
            for structure in structures:
                # Calculate architectural significance
                significance = self._calculate_architectural_significance(
                    structure, file_path, architecture_topic
                )
                
                # Only include architecturally significant structures
                if significance > 0.4:
                    # Extract the actual code snippet
                    lines = content.split('\n')
                    start_line = max(0, structure['line_start'] - 1)
                    end_line = min(len(lines), structure['line_end'])
                    snippet_content = '\n'.join(lines[start_line:end_line])
                    
                    # Generate GitHub permalink
                    permalink = self.github_client.get_permalink_url(
                        repo_url, file_path, structure['line_start'], commit_sha
                    )
                    
                    snippet = CodeSnippet(
                        file_path=file_path,
                        content=snippet_content,
                        start_line=structure['line_start'],
                        end_line=structure['line_end'],
                        language=language,
                        snippet_type=structure['type'],
                        name=structure['name'],
                        github_permalink=permalink,
                        commit_sha=commit_sha,
                        architectural_significance=significance
                    )
                    snippets.append(snippet)
            
            return snippets
            
        except Exception as e:
            logger.warning(f"Failed to analyze file {file_path}: {e}")
            return []
    
    async def _get_relevant_files(self, repo_url: str, architecture_topic: str, 
                                max_files: int = None) -> List[Tuple[str, float]]:
        """Get list of files relevant to the architecture topic"""
        max_files = max_files or self.max_files_limit
        
        try:
            # Get repository contents recursively
            all_files = []
            
            async def collect_files(path: str = ""):
                contents = await self.github_client.get_repository_contents(repo_url, path)
                
                for item in contents:
                    if item['type'] == 'file':
                        # Check if file is relevant to architecture topic
                        is_relevant, relevance_score = ArchitectureTopicFilter.is_file_relevant(
                            item['path'], architecture_topic
                        )
                        
                        if is_relevant:
                            all_files.append((item['path'], relevance_score))
                    
                    elif item['type'] == 'dir' and len(all_files) < max_files * 2:
                        # Recursively explore relevant directories
                        dir_relevant, _ = ArchitectureTopicFilter.is_file_relevant(
                            item['path'], architecture_topic
                        )
                        if dir_relevant or item['name'] in ['src', 'lib', 'pkg', 'internal']:
                            await collect_files(item['path'])
            
            await collect_files()
            
            # Sort by relevance score and limit results
            all_files.sort(key=lambda x: x[1], reverse=True)
            return all_files[:max_files]
            
        except Exception as e:
            logger.error(f"Failed to get repository files: {e}")
            return []
    
    async def analyze_repository(self, repo_url: str, architecture_topic: str) -> RepositoryAnalysis:
        """
        Perform comprehensive repository analysis for the given architecture topic.
        
        Args:
            repo_url: GitHub repository URL
            architecture_topic: Architecture specialization (e.g., 'distributed_systems')
            
        Returns:
            RepositoryAnalysis: Complete analysis results
        """
        logger.info(f"Starting repository analysis: {repo_url} for topic: {architecture_topic}")
        
        # Get repository metadata
        metadata = await self.github_client.get_repository_metadata(repo_url)
        
        # Get the latest commit SHA for stable linking
        contents = await self.github_client.get_repository_contents(repo_url)
        commit_sha = contents[0]['sha'] if contents else metadata.default_branch
        
        # Get relevant files with the configured limit
        relevant_files = await self._get_relevant_files(repo_url, architecture_topic, self.max_files_limit)
        
        logger.info(f"Found {len(relevant_files)} relevant files for analysis")
        
        # Analyze files and extract code snippets, respecting the file limit
        all_snippets = []
        analyzed_files = []
        
        # Ensure we don't exceed the max_files_limit
        files_to_analyze = relevant_files[:self.max_files_limit]
        
        for file_path, relevance_score in files_to_analyze:
            snippets = await self._analyze_file(repo_url, file_path, architecture_topic, commit_sha)
            all_snippets.extend(snippets)
            analyzed_files.append(file_path)
            
            # Add small delay to avoid overwhelming the API
            await asyncio.sleep(0.1)
        
        # Sort snippets by architectural significance
        all_snippets.sort(key=lambda x: x.architectural_significance, reverse=True)
        
        # Detect architecture patterns
        architecture_patterns = self._detect_architecture_patterns(all_snippets, architecture_topic)
        
        # Calculate complexity score
        complexity_score = self._calculate_complexity_score(metadata, all_snippets)
        
        analysis = RepositoryAnalysis(
            repository_url=repo_url,
            metadata=metadata,
            total_files_analyzed=len(analyzed_files),
            relevant_files=analyzed_files,
            code_snippets=all_snippets,
            architecture_patterns=architecture_patterns,
            primary_language=metadata.language or 'unknown',
            complexity_score=complexity_score
        )
        
        logger.info(f"Analysis complete: {len(all_snippets)} snippets extracted, "
                   f"complexity score: {complexity_score:.2f}")
        
        return analysis
    
    def _detect_architecture_patterns(self, snippets: List[CodeSnippet], 
                                    architecture_topic: str) -> List[str]:
        """Detect common architecture patterns in the code snippets"""
        patterns = set()
        
        # Pattern detection based on snippet names and types
        for snippet in snippets:
            name_lower = snippet.name.lower()
            
            # Common patterns
            if 'handler' in name_lower:
                patterns.add('Handler Pattern')
            if 'service' in name_lower:
                patterns.add('Service Layer Pattern')
            if 'factory' in name_lower:
                patterns.add('Factory Pattern')
            if 'builder' in name_lower:
                patterns.add('Builder Pattern')
            if 'observer' in name_lower:
                patterns.add('Observer Pattern')
            if 'strategy' in name_lower:
                patterns.add('Strategy Pattern')
            if snippet.snippet_type == 'interface':
                patterns.add('Interface Segregation')
            if 'client' in name_lower and 'server' in [s.name.lower() for s in snippets]:
                patterns.add('Client-Server Pattern')
        
        # Topic-specific patterns
        topic_patterns = ArchitectureTopicFilter.get_relevant_patterns(architecture_topic)
        for keyword in topic_patterns.get('keywords', []):
            if any(keyword in snippet.name.lower() for snippet in snippets):
                patterns.add(f"{keyword.title()} Pattern")
        
        return list(patterns)
    
    def _calculate_complexity_score(self, metadata: GitHubRepoMetadata, 
                                  snippets: List[CodeSnippet]) -> float:
        """Calculate repository complexity score (0.0 to 1.0)"""
        score = 0.0
        
        # Base score from repository size and activity
        size_score = min(metadata.size / 10000, 0.3)  # Normalize by 10MB
        activity_score = min(metadata.stars / 1000, 0.2)  # Normalize by 1k stars
        
        # Score from code analysis
        snippet_score = min(len(snippets) / 50, 0.3)  # Normalize by 50 snippets
        
        # Language diversity score
        languages = set(snippet.language for snippet in snippets)
        language_score = min(len(languages) / 5, 0.2)  # Normalize by 5 languages
        
        score = size_score + activity_score + snippet_score + language_score
        return min(score, 1.0)

# Convenience function for creating MCP client
async def create_mcp_client(github_token: Optional[str] = None) -> MCPClient:
    """Create and return an MCP client instance"""
    github_client = GitHubClient(github_token)
    return MCPClient(github_client)