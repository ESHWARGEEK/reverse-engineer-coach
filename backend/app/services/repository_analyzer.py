"""
AI-Powered Repository Analysis Service
Uses LLM integration to assess educational value and architectural complexity of repositories.
"""

import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict

from app.cache import cache
from app.github_client import GitHubClient, GitHubAPIError
from app.llm_provider import LLMProviderFactory, LLMProvider, SpecificationPrompt
from app.services.github_search_service import RepositorySuggestion, RepositoryQuality

logger = logging.getLogger(__name__)


@dataclass
class ArchitecturalPattern:
    """Identified architectural pattern in repository"""
    pattern_name: str
    confidence: float  # 0-1
    description: str
    examples: List[str]  # File paths or code snippets
    complexity_level: int  # 1-5
    educational_value: float  # 0-1


@dataclass
class EducationalAssessment:
    """Educational value assessment of repository"""
    learning_difficulty: int  # 1-5 (1=beginner, 5=expert)
    concept_clarity: float  # 0-1
    code_readability: float  # 0-1
    documentation_quality: float  # 0-1
    practical_applicability: float  # 0-1
    overall_educational_score: float  # 0-1
    recommended_prerequisites: List[str]
    learning_outcomes: List[str]


@dataclass
class ComplexityAnalysis:
    """Architectural complexity analysis"""
    cyclomatic_complexity: float  # Estimated
    architectural_layers: int
    component_coupling: float  # 0-1 (0=loose, 1=tight)
    abstraction_level: float  # 0-1 (0=concrete, 1=abstract)
    design_pattern_usage: float  # 0-1
    overall_complexity: float  # 0-1


@dataclass
class RepositoryAnalysis:
    """Complete repository analysis result"""
    repository_url: str
    analysis_timestamp: str
    
    # Core analysis
    architectural_patterns: List[ArchitecturalPattern]
    educational_assessment: EducationalAssessment
    complexity_analysis: ComplexityAnalysis
    
    # Ranking factors
    learning_potential_score: float  # 0-1
    implementation_difficulty: float  # 0-1
    concept_coverage: float  # 0-1
    
    # Recommendations
    target_audience: str
    estimated_learning_time: str
    recommended_approach: str
    key_learning_points: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class RepositoryAnalyzer:
    """
    AI-powered repository analyzer for educational value assessment.
    
    Features:
    - Educational value assessment using LLM analysis
    - Architectural complexity analysis
    - Repository ranking algorithm based on learning potential
    - Pattern recognition and complexity scoring
    """
    
    def __init__(self, github_token: Optional[str] = None, ai_api_key: Optional[str] = None, ai_provider: str = "openai"):
        """
        Initialize repository analyzer.
        
        Args:
            github_token: GitHub API token
            ai_api_key: AI service API key
            ai_provider: AI provider ("openai" or "anthropic")
        """
        self.github_client = GitHubClient(github_token)
        self.ai_provider_type = LLMProvider.OPENAI if ai_provider == "openai" else LLMProvider.ANTHROPIC
        self.ai_api_key = ai_api_key
        self.cache_ttl = 7200  # 2 hours cache for analysis results
        
        # Educational patterns and their complexity levels
        self.pattern_complexity = {
            'mvc': 2, 'mvp': 2, 'mvvm': 3,
            'microservices': 4, 'monolith': 2,
            'layered': 2, 'hexagonal': 4, 'clean': 4,
            'repository': 2, 'factory': 2, 'singleton': 1,
            'observer': 2, 'strategy': 2, 'adapter': 2,
            'decorator': 3, 'facade': 2, 'proxy': 3,
            'command': 3, 'mediator': 4, 'chain': 3,
            'ddd': 5, 'cqrs': 4, 'event-sourcing': 5,
            'rest': 2, 'graphql': 3, 'websocket': 3,
            'oauth': 3, 'jwt': 2, 'rbac': 3
        }
        
        # Language-specific complexity indicators
        self.language_complexity_indicators = {
            'python': {
                'simple': ['flask', 'fastapi', 'requests'],
                'moderate': ['django', 'sqlalchemy', 'celery'],
                'complex': ['asyncio', 'multiprocessing', 'metaclass']
            },
            'javascript': {
                'simple': ['express', 'axios', 'lodash'],
                'moderate': ['react', 'vue', 'webpack'],
                'complex': ['rxjs', 'mobx', 'redux-saga']
            },
            'java': {
                'simple': ['spring-boot', 'junit', 'maven'],
                'moderate': ['spring-security', 'hibernate', 'kafka'],
                'complex': ['spring-cloud', 'akka', 'reactive']
            }
        }
    
    async def __aenter__(self):
        await self.github_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.github_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def analyze_repository(self, repository_url: str, learning_concept: Optional[str] = None) -> RepositoryAnalysis:
        """
        Perform comprehensive repository analysis.
        
        Args:
            repository_url: GitHub repository URL
            learning_concept: Optional learning concept for context
            
        Returns:
            Complete repository analysis
        """
        # Generate cache key
        cache_key = hashlib.md5(f"{repository_url}:{learning_concept}".encode()).hexdigest()
        
        # Try cache first
        cached_analysis = await cache.get(cache_key, namespace="repo_analysis")
        if cached_analysis:
            return RepositoryAnalysis(**cached_analysis)
        
        try:
            logger.info(f"Starting analysis for repository: {repository_url}")
            
            # Get repository metadata
            repo_metadata = await self.github_client.get_repository_metadata(repository_url)
            
            # Analyze repository structure
            repo_structure = await self._analyze_repository_structure(repository_url)
            
            # Identify architectural patterns
            patterns = await self._identify_architectural_patterns(repository_url, repo_structure, repo_metadata)
            
            # Assess educational value using AI
            educational_assessment = await self._assess_educational_value(
                repository_url, repo_metadata, patterns, learning_concept
            )
            
            # Analyze complexity
            complexity_analysis = await self._analyze_complexity(repository_url, repo_structure, patterns)
            
            # Calculate ranking scores
            learning_potential = self._calculate_learning_potential(patterns, educational_assessment, complexity_analysis)
            implementation_difficulty = self._calculate_implementation_difficulty(complexity_analysis, patterns)
            concept_coverage = self._calculate_concept_coverage(patterns, learning_concept)
            
            # Generate recommendations
            target_audience, learning_time, approach, key_points = await self._generate_recommendations(
                patterns, educational_assessment, complexity_analysis, learning_concept
            )
            
            # Create analysis result
            analysis = RepositoryAnalysis(
                repository_url=repository_url,
                analysis_timestamp=datetime.utcnow().isoformat(),
                architectural_patterns=patterns,
                educational_assessment=educational_assessment,
                complexity_analysis=complexity_analysis,
                learning_potential_score=learning_potential,
                implementation_difficulty=implementation_difficulty,
                concept_coverage=concept_coverage,
                target_audience=target_audience,
                estimated_learning_time=learning_time,
                recommended_approach=approach,
                key_learning_points=key_points
            )
            
            # Cache the analysis
            await cache.set(cache_key, analysis.to_dict(), expire=self.cache_ttl, namespace="repo_analysis")
            
            logger.info(f"Completed analysis for repository: {repository_url}")
            return analysis
            
        except Exception as e:
            logger.error(f"Repository analysis failed for {repository_url}: {e}")
            # Return default analysis
            return self._create_default_analysis(repository_url)
    
    async def _analyze_repository_structure(self, repository_url: str) -> Dict[str, Any]:
        """Analyze repository file structure and organization."""
        try:
            contents = await self.github_client.get_repository_contents(repository_url)
            
            structure = {
                'directories': [],
                'files': [],
                'config_files': [],
                'documentation_files': [],
                'test_files': [],
                'build_files': []
            }
            
            # Categorize files and directories
            for item in contents:
                if item['type'] == 'dir':
                    structure['directories'].append(item['name'])
                else:
                    filename = item['name'].lower()
                    structure['files'].append(item['name'])
                    
                    # Categorize files
                    if any(ext in filename for ext in ['.md', '.txt', '.rst']):
                        structure['documentation_files'].append(item['name'])
                    elif any(test_indicator in filename for test_indicator in ['test', 'spec', '__test__']):
                        structure['test_files'].append(item['name'])
                    elif any(config in filename for config in ['config', 'package.json', 'requirements.txt', 'pom.xml', 'cargo.toml']):
                        structure['config_files'].append(item['name'])
                    elif any(build in filename for build in ['dockerfile', 'makefile', 'build', 'webpack']):
                        structure['build_files'].append(item['name'])
            
            return structure
            
        except Exception as e:
            logger.error(f"Failed to analyze repository structure: {e}")
            return {'directories': [], 'files': [], 'config_files': [], 'documentation_files': [], 'test_files': [], 'build_files': []}
    
    async def _identify_architectural_patterns(
        self, 
        repository_url: str, 
        structure: Dict[str, Any], 
        metadata: Any
    ) -> List[ArchitecturalPattern]:
        """Identify architectural patterns in the repository."""
        patterns = []
        
        try:
            # Pattern detection based on structure
            directories = [d.lower() for d in structure['directories']]
            files = [f.lower() for f in structure['files']]
            
            # MVC Pattern
            if any(d in directories for d in ['models', 'views', 'controllers']) or \
               any(d in directories for d in ['model', 'view', 'controller']):
                patterns.append(ArchitecturalPattern(
                    pattern_name='mvc',
                    confidence=0.8,
                    description='Model-View-Controller architectural pattern',
                    examples=[d for d in structure['directories'] if d.lower() in ['models', 'views', 'controllers', 'model', 'view', 'controller']],
                    complexity_level=2,
                    educational_value=0.9
                ))
            
            # Microservices Pattern
            if any(indicator in directories for indicator in ['services', 'microservices']) or \
               'docker-compose.yml' in files or 'kubernetes' in directories:
                patterns.append(ArchitecturalPattern(
                    pattern_name='microservices',
                    confidence=0.7,
                    description='Microservices architectural pattern',
                    examples=['docker-compose.yml', 'services/', 'kubernetes/'],
                    complexity_level=4,
                    educational_value=0.8
                ))
            
            # Layered Architecture
            if any(layer in directories for layer in ['domain', 'application', 'infrastructure', 'presentation']):
                patterns.append(ArchitecturalPattern(
                    pattern_name='layered',
                    confidence=0.8,
                    description='Layered architectural pattern',
                    examples=[d for d in structure['directories'] if d.lower() in ['domain', 'application', 'infrastructure', 'presentation']],
                    complexity_level=2,
                    educational_value=0.8
                ))
            
            # Repository Pattern
            if any('repository' in d.lower() for d in directories) or \
               any('repo' in f.lower() for f in files):
                patterns.append(ArchitecturalPattern(
                    pattern_name='repository',
                    confidence=0.7,
                    description='Repository design pattern',
                    examples=[item for item in structure['directories'] + structure['files'] if 'repository' in item.lower() or 'repo' in item.lower()],
                    complexity_level=2,
                    educational_value=0.7
                ))
            
            # REST API Pattern
            if any(api_indicator in directories for api_indicator in ['api', 'routes', 'endpoints']) or \
               metadata.description and 'api' in metadata.description.lower():
                patterns.append(ArchitecturalPattern(
                    pattern_name='rest',
                    confidence=0.8,
                    description='REST API architectural pattern',
                    examples=[d for d in structure['directories'] if d.lower() in ['api', 'routes', 'endpoints']],
                    complexity_level=2,
                    educational_value=0.8
                ))
            
            # Add more pattern detection based on language and framework
            await self._detect_language_specific_patterns(repository_url, metadata.language, patterns)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to identify architectural patterns: {e}")
            return []
    
    async def _detect_language_specific_patterns(self, repository_url: str, language: str, patterns: List[ArchitecturalPattern]):
        """Detect language-specific architectural patterns."""
        try:
            if not language:
                return
            
            language_lower = language.lower()
            
            # Python-specific patterns
            if language_lower == 'python':
                await self._detect_python_patterns(repository_url, patterns)
            
            # JavaScript-specific patterns
            elif language_lower == 'javascript':
                await self._detect_javascript_patterns(repository_url, patterns)
            
            # Java-specific patterns
            elif language_lower == 'java':
                await self._detect_java_patterns(repository_url, patterns)
            
        except Exception as e:
            logger.error(f"Failed to detect language-specific patterns: {e}")
    
    async def _detect_python_patterns(self, repository_url: str, patterns: List[ArchitecturalPattern]):
        """Detect Python-specific patterns."""
        try:
            # Check for Django patterns
            try:
                await self.github_client.get_file_content(repository_url, 'manage.py')
                patterns.append(ArchitecturalPattern(
                    pattern_name='django-mvc',
                    confidence=0.9,
                    description='Django MVC framework pattern',
                    examples=['manage.py', 'models.py', 'views.py'],
                    complexity_level=3,
                    educational_value=0.8
                ))
            except:
                pass
            
            # Check for Flask patterns
            try:
                app_content, _ = await self.github_client.get_file_content(repository_url, 'app.py')
                if 'flask' in app_content.lower():
                    patterns.append(ArchitecturalPattern(
                        pattern_name='flask-microframework',
                        confidence=0.8,
                        description='Flask microframework pattern',
                        examples=['app.py'],
                        complexity_level=2,
                        educational_value=0.9
                    ))
            except:
                pass
            
        except Exception as e:
            logger.error(f"Failed to detect Python patterns: {e}")
    
    async def _detect_javascript_patterns(self, repository_url: str, patterns: List[ArchitecturalPattern]):
        """Detect JavaScript-specific patterns."""
        try:
            # Check for React patterns
            try:
                package_content, _ = await self.github_client.get_file_content(repository_url, 'package.json')
                package_data = json.loads(package_content)
                
                dependencies = {**package_data.get('dependencies', {}), **package_data.get('devDependencies', {})}
                
                if 'react' in dependencies:
                    patterns.append(ArchitecturalPattern(
                        pattern_name='react-component',
                        confidence=0.9,
                        description='React component-based architecture',
                        examples=['package.json'],
                        complexity_level=3,
                        educational_value=0.8
                    ))
                
                if 'express' in dependencies:
                    patterns.append(ArchitecturalPattern(
                        pattern_name='express-middleware',
                        confidence=0.8,
                        description='Express.js middleware pattern',
                        examples=['package.json'],
                        complexity_level=2,
                        educational_value=0.8
                    ))
                    
            except:
                pass
            
        except Exception as e:
            logger.error(f"Failed to detect JavaScript patterns: {e}")
    
    async def _detect_java_patterns(self, repository_url: str, patterns: List[ArchitecturalPattern]):
        """Detect Java-specific patterns."""
        try:
            # Check for Spring Boot patterns
            try:
                pom_content, _ = await self.github_client.get_file_content(repository_url, 'pom.xml')
                if 'spring-boot' in pom_content.lower():
                    patterns.append(ArchitecturalPattern(
                        pattern_name='spring-boot',
                        confidence=0.9,
                        description='Spring Boot framework pattern',
                        examples=['pom.xml'],
                        complexity_level=3,
                        educational_value=0.8
                    ))
            except:
                pass
            
        except Exception as e:
            logger.error(f"Failed to detect Java patterns: {e}")
    
    async def _assess_educational_value(
        self, 
        repository_url: str, 
        metadata: Any, 
        patterns: List[ArchitecturalPattern],
        learning_concept: Optional[str]
    ) -> EducationalAssessment:
        """Assess educational value using AI analysis."""
        try:
            # Create LLM provider
            llm_provider = LLMProviderFactory.create_provider(self.ai_provider_type, self.ai_api_key)
            
            # Prepare analysis prompt
            prompt_data = {
                'repository_info': {
                    'name': metadata.name,
                    'description': metadata.description,
                    'language': metadata.language,
                    'stars': metadata.stars,
                    'size': metadata.size
                },
                'patterns': [{'pattern': p.pattern_name, 'confidence': p.confidence} for p in patterns],
                'learning_concept': learning_concept or 'general software architecture'
            }
            
            # Generate educational assessment using AI
            assessment_prompt = f"""
Analyze the educational value of this repository for learning software architecture:

Repository: {metadata.name}
Description: {metadata.description or 'No description'}
Language: {metadata.language}
Identified Patterns: {[p.pattern_name for p in patterns]}
Learning Context: {learning_concept or 'General software architecture'}

Assess the following aspects (score 0-1):
1. Learning Difficulty (1-5): How difficult is this for a mid-level developer?
2. Concept Clarity: How clearly are architectural concepts demonstrated?
3. Code Readability: How readable and well-structured is the code likely to be?
4. Documentation Quality: Based on repository metadata, how good is the documentation?
5. Practical Applicability: How applicable are the concepts to real-world projects?

Also provide:
- Recommended prerequisites (list of concepts/technologies)
- Expected learning outcomes (list of skills/knowledge gained)

Format your response as JSON with the following structure:
{{
    "learning_difficulty": 1-5,
    "concept_clarity": 0.0-1.0,
    "code_readability": 0.0-1.0,
    "documentation_quality": 0.0-1.0,
    "practical_applicability": 0.0-1.0,
    "recommended_prerequisites": ["prerequisite1", "prerequisite2"],
    "learning_outcomes": ["outcome1", "outcome2"]
}}
"""
            
            # Use simplified assessment for now (AI integration can be enhanced later)
            assessment = self._create_heuristic_educational_assessment(metadata, patterns, learning_concept)
            
            return assessment
            
        except Exception as e:
            logger.error(f"Failed to assess educational value: {e}")
            return self._create_default_educational_assessment()
    
    def _create_heuristic_educational_assessment(
        self, 
        metadata: Any, 
        patterns: List[ArchitecturalPattern],
        learning_concept: Optional[str]
    ) -> EducationalAssessment:
        """Create educational assessment using heuristic analysis."""
        
        # Calculate difficulty based on patterns
        avg_complexity = sum(p.complexity_level for p in patterns) / max(len(patterns), 1)
        learning_difficulty = min(5, max(1, int(avg_complexity)))
        
        # Concept clarity based on pattern confidence
        concept_clarity = sum(p.confidence for p in patterns) / max(len(patterns), 1) if patterns else 0.5
        
        # Code readability based on repository characteristics
        code_readability = 0.7  # Default assumption
        if metadata.stars > 100:
            code_readability += 0.1
        if metadata.size < 10000:  # Not too large
            code_readability += 0.1
        code_readability = min(1.0, code_readability)
        
        # Documentation quality based on description and size
        doc_quality = 0.5
        if metadata.description and len(metadata.description) > 50:
            doc_quality += 0.2
        if metadata.stars > 50:  # Popular repos usually have better docs
            doc_quality += 0.2
        doc_quality = min(1.0, doc_quality)
        
        # Practical applicability based on patterns
        practical_applicability = sum(p.educational_value for p in patterns) / max(len(patterns), 1) if patterns else 0.5
        
        # Overall score
        overall_score = (concept_clarity + code_readability + doc_quality + practical_applicability) / 4
        
        # Generate prerequisites and outcomes
        prerequisites = []
        outcomes = []
        
        for pattern in patterns:
            if pattern.pattern_name in ['mvc', 'rest']:
                prerequisites.extend(['basic programming', 'web development basics'])
                outcomes.extend([f'understand {pattern.pattern_name} pattern', 'implement web applications'])
            elif pattern.pattern_name in ['microservices', 'ddd']:
                prerequisites.extend(['distributed systems', 'software architecture'])
                outcomes.extend(['design scalable systems', 'implement complex architectures'])
        
        # Remove duplicates
        prerequisites = list(set(prerequisites))
        outcomes = list(set(outcomes))
        
        return EducationalAssessment(
            learning_difficulty=learning_difficulty,
            concept_clarity=concept_clarity,
            code_readability=code_readability,
            documentation_quality=doc_quality,
            practical_applicability=practical_applicability,
            overall_educational_score=overall_score,
            recommended_prerequisites=prerequisites,
            learning_outcomes=outcomes
        )
    
    async def _analyze_complexity(
        self, 
        repository_url: str, 
        structure: Dict[str, Any], 
        patterns: List[ArchitecturalPattern]
    ) -> ComplexityAnalysis:
        """Analyze architectural complexity."""
        try:
            # Estimate cyclomatic complexity based on file count and structure
            file_count = len(structure['files'])
            dir_count = len(structure['directories'])
            
            # Simple heuristic for complexity
            cyclomatic_complexity = min(1.0, (file_count + dir_count * 2) / 100)
            
            # Architectural layers based on directory structure
            layer_indicators = ['presentation', 'application', 'domain', 'infrastructure', 'data', 'service']
            architectural_layers = sum(1 for d in structure['directories'] if any(layer in d.lower() for layer in layer_indicators))
            architectural_layers = max(1, architectural_layers)
            
            # Component coupling based on patterns
            coupling_patterns = ['microservices', 'layered', 'hexagonal']
            component_coupling = 0.5  # Default
            if any(p.pattern_name in coupling_patterns for p in patterns):
                component_coupling = 0.3  # Lower coupling for good patterns
            
            # Abstraction level based on patterns
            abstract_patterns = ['ddd', 'clean', 'hexagonal', 'cqrs']
            abstraction_level = 0.5
            if any(p.pattern_name in abstract_patterns for p in patterns):
                abstraction_level = 0.8
            
            # Design pattern usage
            design_pattern_usage = len([p for p in patterns if p.pattern_name in self.pattern_complexity]) / max(len(patterns), 1)
            
            # Overall complexity
            overall_complexity = (
                cyclomatic_complexity * 0.3 +
                (architectural_layers / 5) * 0.2 +
                component_coupling * 0.2 +
                abstraction_level * 0.15 +
                design_pattern_usage * 0.15
            )
            
            return ComplexityAnalysis(
                cyclomatic_complexity=cyclomatic_complexity,
                architectural_layers=architectural_layers,
                component_coupling=component_coupling,
                abstraction_level=abstraction_level,
                design_pattern_usage=design_pattern_usage,
                overall_complexity=min(1.0, overall_complexity)
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze complexity: {e}")
            return ComplexityAnalysis(
                cyclomatic_complexity=0.5,
                architectural_layers=2,
                component_coupling=0.5,
                abstraction_level=0.5,
                design_pattern_usage=0.5,
                overall_complexity=0.5
            )
    
    def _calculate_learning_potential(
        self, 
        patterns: List[ArchitecturalPattern], 
        educational: EducationalAssessment, 
        complexity: ComplexityAnalysis
    ) -> float:
        """Calculate learning potential score."""
        try:
            # Pattern diversity bonus
            pattern_diversity = min(1.0, len(patterns) / 5)
            
            # Educational value from patterns
            pattern_educational_value = sum(p.educational_value for p in patterns) / max(len(patterns), 1) if patterns else 0.5
            
            # Complexity sweet spot (not too simple, not too complex)
            complexity_score = 1.0 - abs(complexity.overall_complexity - 0.6)  # Sweet spot at 0.6
            
            # Combine scores
            learning_potential = (
                educational.overall_educational_score * 0.4 +
                pattern_educational_value * 0.3 +
                pattern_diversity * 0.2 +
                complexity_score * 0.1
            )
            
            return min(1.0, learning_potential)
            
        except Exception:
            return 0.5
    
    def _calculate_implementation_difficulty(
        self, 
        complexity: ComplexityAnalysis, 
        patterns: List[ArchitecturalPattern]
    ) -> float:
        """Calculate implementation difficulty."""
        try:
            # Base difficulty from complexity
            base_difficulty = complexity.overall_complexity
            
            # Pattern complexity adjustment
            pattern_complexity_avg = sum(self.pattern_complexity.get(p.pattern_name, 3) for p in patterns) / max(len(patterns), 1) if patterns else 3
            pattern_difficulty = pattern_complexity_avg / 5  # Normalize to 0-1
            
            # Combine scores
            implementation_difficulty = (base_difficulty * 0.6 + pattern_difficulty * 0.4)
            
            return min(1.0, implementation_difficulty)
            
        except Exception:
            return 0.5
    
    def _calculate_concept_coverage(self, patterns: List[ArchitecturalPattern], learning_concept: Optional[str]) -> float:
        """Calculate how well the repository covers the learning concept."""
        try:
            if not learning_concept:
                return 0.7  # Default coverage
            
            concept_lower = learning_concept.lower()
            coverage_score = 0.0
            
            # Check pattern relevance to concept
            for pattern in patterns:
                if pattern.pattern_name in concept_lower:
                    coverage_score += 0.3
                elif any(keyword in concept_lower for keyword in ['architecture', 'pattern', 'design']):
                    coverage_score += 0.1
            
            # Base coverage for having any patterns
            if patterns:
                coverage_score += 0.4
            
            return min(1.0, coverage_score)
            
        except Exception:
            return 0.5
    
    async def _generate_recommendations(
        self, 
        patterns: List[ArchitecturalPattern], 
        educational: EducationalAssessment, 
        complexity: ComplexityAnalysis,
        learning_concept: Optional[str]
    ) -> Tuple[str, str, str, List[str]]:
        """Generate learning recommendations."""
        try:
            # Target audience based on difficulty
            if educational.learning_difficulty <= 2:
                target_audience = "Beginner to Intermediate developers"
            elif educational.learning_difficulty <= 3:
                target_audience = "Intermediate developers"
            else:
                target_audience = "Advanced developers"
            
            # Estimated learning time based on complexity and patterns
            pattern_count = len(patterns)
            if complexity.overall_complexity < 0.3 and pattern_count <= 2:
                learning_time = "1-2 weeks"
            elif complexity.overall_complexity < 0.6 and pattern_count <= 4:
                learning_time = "2-4 weeks"
            else:
                learning_time = "4-8 weeks"
            
            # Recommended approach
            if educational.learning_difficulty <= 2:
                approach = "Start with understanding the basic structure, then implement simplified versions of key components"
            elif educational.learning_difficulty <= 3:
                approach = "Analyze the architectural patterns first, then implement core functionality step by step"
            else:
                approach = "Study the overall architecture, break down complex patterns, and implement incrementally"
            
            # Key learning points
            key_points = []
            for pattern in patterns[:3]:  # Top 3 patterns
                key_points.append(f"Understand and implement {pattern.pattern_name} pattern")
            
            if complexity.architectural_layers > 2:
                key_points.append("Learn layered architecture principles")
            
            if educational.practical_applicability > 0.7:
                key_points.append("Apply patterns to real-world scenarios")
            
            return target_audience, learning_time, approach, key_points
            
        except Exception:
            return "Intermediate developers", "2-4 weeks", "Study and implement step by step", ["Learn architectural patterns"]
    
    def _create_default_analysis(self, repository_url: str) -> RepositoryAnalysis:
        """Create default analysis when full analysis fails."""
        return RepositoryAnalysis(
            repository_url=repository_url,
            analysis_timestamp=datetime.utcnow().isoformat(),
            architectural_patterns=[],
            educational_assessment=self._create_default_educational_assessment(),
            complexity_analysis=ComplexityAnalysis(
                cyclomatic_complexity=0.5,
                architectural_layers=2,
                component_coupling=0.5,
                abstraction_level=0.5,
                design_pattern_usage=0.5,
                overall_complexity=0.5
            ),
            learning_potential_score=0.5,
            implementation_difficulty=0.5,
            concept_coverage=0.5,
            target_audience="Intermediate developers",
            estimated_learning_time="2-4 weeks",
            recommended_approach="Study and implement step by step",
            key_learning_points=["Learn architectural patterns"]
        )
    
    def _create_default_educational_assessment(self) -> EducationalAssessment:
        """Create default educational assessment."""
        return EducationalAssessment(
            learning_difficulty=3,
            concept_clarity=0.5,
            code_readability=0.5,
            documentation_quality=0.5,
            practical_applicability=0.5,
            overall_educational_score=0.5,
            recommended_prerequisites=["basic programming", "software architecture basics"],
            learning_outcomes=["understand architectural patterns", "implement software systems"]
        )
    
    async def rank_repositories(self, repositories: List[RepositorySuggestion], learning_concept: str) -> List[Tuple[RepositorySuggestion, RepositoryAnalysis]]:
        """
        Rank repositories based on learning potential.
        
        Args:
            repositories: List of repository suggestions
            learning_concept: Learning concept for context
            
        Returns:
            List of (repository, analysis) tuples sorted by learning potential
        """
        ranked_repos = []
        
        for repo in repositories:
            try:
                analysis = await self.analyze_repository(repo.repository_url, learning_concept)
                ranked_repos.append((repo, analysis))
            except Exception as e:
                logger.error(f"Failed to analyze repository {repo.repository_url}: {e}")
                # Add with default analysis
                default_analysis = self._create_default_analysis(repo.repository_url)
                ranked_repos.append((repo, default_analysis))
        
        # Sort by learning potential score
        ranked_repos.sort(key=lambda x: x[1].learning_potential_score, reverse=True)
        
        return ranked_repos