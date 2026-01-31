"""
Repository Analysis Agent - AI service for analyzing repositories and extracting learning content

Features:
- Repository structure analysis
- Architectural pattern detection
- Code complexity assessment for skill level matching
- Learning opportunity identification
- Educational value scoring for code segments
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import re
from dataclasses import dataclass, asdict
from enum import Enum
import ast
import os

from ..llm_provider import LLMProvider
from ..github_client import GitHubClient
from ..cache import cache_manager

logger = logging.getLogger(__name__)

class ArchitecturalPattern(Enum):
    MVC = "mvc"
    MVP = "mvp"
    MVVM = "mvvm"
    LAYERED = "layered"
    MICROSERVICES = "microservices"
    MONOLITHIC = "monolithic"
    COMPONENT_BASED = "component_based"
    EVENT_DRIVEN = "event_driven"
    PIPE_AND_FILTER = "pipe_and_filter"
    REPOSITORY_PATTERN = "repository_pattern"
    FACTORY_PATTERN = "factory_pattern"
    OBSERVER_PATTERN = "observer_pattern"
    SINGLETON_PATTERN = "singleton_pattern"

class ComplexityLevel(Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

@dataclass
class CodeSegment:
    """Represents a code segment with learning value"""
    file_path: str
    start_line: int
    end_line: int
    content: str
    language: str
    complexity: ComplexityLevel
    educational_value: float  # 0-100
    concepts: List[str]
    patterns: List[ArchitecturalPattern]
    learning_notes: str
    difficulty_level: str

@dataclass
class ArchitecturalAnalysis:
    """Analysis of architectural patterns in repository"""
    primary_patterns: List[ArchitecturalPattern]
    secondary_patterns: List[ArchitecturalPattern]
    pattern_confidence: Dict[str, float]
    architecture_description: str
    key_components: List[str]
    data_flow: str
    scalability_patterns: List[str]
    design_principles: List[str]

@dataclass
class ComplexityAnalysis:
    """Code complexity analysis"""
    overall_complexity: ComplexityLevel
    complexity_by_file: Dict[str, ComplexityLevel]
    complexity_factors: List[str]
    beginner_friendly_files: List[str]
    intermediate_files: List[str]
    advanced_files: List[str]
    complexity_score: float  # 0-100
    skill_level_recommendation: str

@dataclass
class LearningOpportunity:
    """Identified learning opportunity"""
    id: str
    title: str
    description: str
    file_paths: List[str]
    concepts: List[str]
    difficulty: str
    estimated_time: str
    prerequisites: List[str]
    learning_objectives: List[str]
    code_examples: List[CodeSegment]
    related_opportunities: List[str]

@dataclass
class RepositoryAnalysis:
    """Complete repository analysis"""
    repository_id: str
    repository_name: str
    analysis_timestamp: datetime
    
    # Structure analysis
    project_structure: Dict[str, Any]
    file_organization: Dict[str, List[str]]
    key_directories: List[str]
    entry_points: List[str]
    
    # Architectural analysis
    architecture: ArchitecturalAnalysis
    
    # Complexity analysis
    complexity: ComplexityAnalysis
    
    # Learning opportunities
    learning_opportunities: List[LearningOpportunity]
    
    # Code segments
    educational_segments: List[CodeSegment]
    
    # Overall assessment
    educational_value_score: float  # 0-100
    beginner_friendliness: float  # 0-100
    code_quality_score: float  # 0-100
    documentation_quality: float  # 0-100
    
    # Recommendations
    learning_path: List[str]
    skill_level_match: Dict[str, float]  # beginner, intermediate, advanced, expert
    recommended_focus_areas: List[str]

class RepositoryAnalysisAgent:
    """AI service for analyzing repositories and extracting learning content"""
    
    def __init__(self, llm_provider: LLMProvider, github_client: GitHubClient):
        self.llm_provider = llm_provider
        self.github_client = github_client
        self.cache_ttl = 7200  # 2 hours cache
        
        # File extensions for different languages
        self.language_extensions = {
            'python': ['.py'],
            'javascript': ['.js', '.jsx', '.ts', '.tsx'],
            'java': ['.java'],
            'csharp': ['.cs'],
            'go': ['.go'],
            'rust': ['.rs'],
            'php': ['.php'],
            'ruby': ['.rb'],
            'cpp': ['.cpp', '.cc', '.cxx', '.c++'],
            'c': ['.c', '.h']
        }
    
    async def analyze_repository(
        self,
        repository_full_name: str,
        user_skill_level: str = "intermediate",
        focus_areas: List[str] = None
    ) -> RepositoryAnalysis:
        """
        Analyze repository for learning content
        
        Args:
            repository_full_name: Full name of repository (owner/repo)
            user_skill_level: User's skill level for personalized analysis
            focus_areas: Specific areas to focus analysis on
            
        Returns:
            Complete repository analysis
        """
        try:
            logger.info(f"Starting repository analysis for {repository_full_name}")
            
            # Check cache first
            cache_key = f"repo_analysis:{repository_full_name}:{user_skill_level}"
            cached_analysis = await self._get_cached_analysis(cache_key)
            if cached_analysis:
                logger.info("Returning cached repository analysis")
                return cached_analysis
            
            # Get repository structure
            repo_structure = await self._analyze_repository_structure(repository_full_name)
            
            # Get key files for analysis
            key_files = await self._identify_key_files(repository_full_name, repo_structure)
            
            # Analyze architecture
            architecture = await self._analyze_architecture(repository_full_name, key_files)
            
            # Analyze complexity
            complexity = await self._analyze_complexity(repository_full_name, key_files, user_skill_level)
            
            # Identify learning opportunities
            learning_opportunities = await self._identify_learning_opportunities(
                repository_full_name, key_files, architecture, user_skill_level, focus_areas
            )
            
            # Extract educational code segments
            educational_segments = await self._extract_educational_segments(
                repository_full_name, key_files, user_skill_level
            )
            
            # Calculate overall scores
            scores = await self._calculate_educational_scores(
                repository_full_name, architecture, complexity, learning_opportunities
            )
            
            # Generate learning path
            learning_path = await self._generate_learning_path(
                learning_opportunities, user_skill_level
            )
            
            # Create analysis result
            analysis = RepositoryAnalysis(
                repository_id=repository_full_name.replace('/', '_'),
                repository_name=repository_full_name,
                analysis_timestamp=datetime.now(),
                project_structure=repo_structure,
                file_organization=self._organize_files_by_type(repo_structure),
                key_directories=self._extract_key_directories(repo_structure),
                entry_points=self._identify_entry_points(key_files),
                architecture=architecture,
                complexity=complexity,
                learning_opportunities=learning_opportunities,
                educational_segments=educational_segments,
                educational_value_score=scores['educational_value'],
                beginner_friendliness=scores['beginner_friendliness'],
                code_quality_score=scores['code_quality'],
                documentation_quality=scores['documentation_quality'],
                learning_path=learning_path,
                skill_level_match=scores['skill_level_match'],
                recommended_focus_areas=self._recommend_focus_areas(learning_opportunities)
            )
            
            # Cache the analysis
            await self._cache_analysis(cache_key, analysis)
            
            logger.info(f"Repository analysis complete for {repository_full_name}")
            return analysis
            
        except Exception as e:
            logger.error(f"Repository analysis failed for {repository_full_name}: {e}")
            raise
    
    async def _analyze_repository_structure(self, repo_full_name: str) -> Dict[str, Any]:
        """Analyze repository structure"""
        try:
            # Get repository tree
            tree = await self.github_client.get_repository_tree(repo_full_name, recursive=True)
            
            if not tree:
                return {}
            
            # Organize files by directory
            structure = {}
            for item in tree.get('tree', []):
                path = item['path']
                path_parts = path.split('/')
                
                current = structure
                for part in path_parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                if item['type'] == 'blob':
                    current[path_parts[-1]] = {
                        'type': 'file',
                        'size': item.get('size', 0),
                        'sha': item['sha']
                    }
                elif item['type'] == 'tree':
                    if path_parts[-1] not in current:
                        current[path_parts[-1]] = {}
            
            return structure
            
        except Exception as e:
            logger.error(f"Failed to analyze repository structure: {e}")
            return {}
    
    async def _identify_key_files(
        self, 
        repo_full_name: str, 
        structure: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify key files for analysis"""
        
        key_files = []
        
        def traverse_structure(current_structure, current_path=""):
            for name, content in current_structure.items():
                full_path = f"{current_path}/{name}" if current_path else name
                
                if isinstance(content, dict) and content.get('type') == 'file':
                    # Check if this is a key file
                    if self._is_key_file(name, full_path):
                        key_files.append({
                            'path': full_path,
                            'name': name,
                            'size': content.get('size', 0),
                            'sha': content.get('sha', '')
                        })
                elif isinstance(content, dict) and 'type' not in content:
                    # This is a directory, recurse
                    traverse_structure(content, full_path)
        
        traverse_structure(structure)
        
        # Sort by importance and limit to reasonable number
        key_files.sort(key=lambda f: self._calculate_file_importance(f), reverse=True)
        return key_files[:50]  # Limit to 50 key files
    
    def _is_key_file(self, filename: str, filepath: str) -> bool:
        """Determine if a file is important for analysis"""
        
        # Important filenames
        important_names = [
            'main.py', 'app.py', 'index.js', 'main.js', 'app.js',
            'main.go', 'main.rs', 'Program.cs', 'Main.java',
            'README.md', 'package.json', 'requirements.txt',
            'Dockerfile', 'docker-compose.yml', 'Makefile'
        ]
        
        if filename.lower() in [name.lower() for name in important_names]:
            return True
        
        # Configuration files
        config_patterns = [
            r'.*config.*\.(json|yaml|yml|toml|ini)$',
            r'.*\.config\.(js|ts)$',
            r'webpack\..*\.js$',
            r'babel\.config\.js$',
            r'tsconfig\.json$'
        ]
        
        for pattern in config_patterns:
            if re.match(pattern, filename.lower()):
                return True
        
        # Source code files in important directories
        important_dirs = ['src', 'lib', 'app', 'components', 'services', 'controllers', 'models']
        for dir_name in important_dirs:
            if f'/{dir_name}/' in filepath.lower() or filepath.lower().startswith(f'{dir_name}/'):
                # Check if it's a source code file
                for lang, extensions in self.language_extensions.items():
                    if any(filename.lower().endswith(ext) for ext in extensions):
                        return True
        
        return False
    
    def _calculate_file_importance(self, file_info: Dict[str, Any]) -> int:
        """Calculate importance score for a file"""
        score = 0
        filename = file_info['name'].lower()
        filepath = file_info['path'].lower()
        
        # Main files get highest priority
        if filename in ['main.py', 'app.py', 'index.js', 'main.js', 'main.go']:
            score += 100
        
        # README and documentation
        if filename.startswith('readme'):
            score += 90
        
        # Configuration files
        if 'config' in filename or filename.endswith('.json'):
            score += 80
        
        # Source files in important directories
        important_dirs = ['src', 'app', 'lib']
        for dir_name in important_dirs:
            if f'/{dir_name}/' in filepath:
                score += 70
                break
        
        # Smaller files are often more focused and educational
        size = file_info.get('size', 0)
        if 100 <= size <= 5000:  # Sweet spot for educational content
            score += 50
        elif size <= 100:
            score += 20
        elif size > 10000:
            score -= 20
        
        return score
    
    async def _analyze_architecture(
        self, 
        repo_full_name: str, 
        key_files: List[Dict[str, Any]]
    ) -> ArchitecturalAnalysis:
        """Analyze architectural patterns"""
        
        try:
            # Get content of key files for analysis
            file_contents = {}
            for file_info in key_files[:10]:  # Analyze top 10 files
                try:
                    content = await self.github_client.get_file_content(
                        repo_full_name, file_info['path']
                    )
                    if content:
                        file_contents[file_info['path']] = content
                except Exception as e:
                    logger.warning(f"Failed to get content for {file_info['path']}: {e}")
                    continue
            
            # Use LLM to analyze architecture
            analysis_prompt = f"""
            Analyze the architectural patterns in this repository based on the following files:
            
            {self._format_files_for_analysis(file_contents)}
            
            Identify:
            1. Primary architectural patterns (MVC, MVP, MVVM, Layered, Microservices, etc.)
            2. Secondary patterns and design patterns used
            3. Key components and their relationships
            4. Data flow patterns
            5. Scalability patterns
            6. Design principles followed
            
            Return a JSON object with:
            {{
                "primary_patterns": ["pattern1", "pattern2"],
                "secondary_patterns": ["pattern3", "pattern4"],
                "pattern_confidence": {{"pattern1": 0.9, "pattern2": 0.7}},
                "architecture_description": "Brief description of the architecture",
                "key_components": ["component1", "component2"],
                "data_flow": "Description of data flow",
                "scalability_patterns": ["pattern1", "pattern2"],
                "design_principles": ["principle1", "principle2"]
            }}
            """
            
            response = await self.llm_provider.generate_completion(analysis_prompt)
            
            try:
                analysis_data = json.loads(response)
                
                return ArchitecturalAnalysis(
                    primary_patterns=[ArchitecturalPattern(p) for p in analysis_data.get('primary_patterns', [])],
                    secondary_patterns=[ArchitecturalPattern(p) for p in analysis_data.get('secondary_patterns', [])],
                    pattern_confidence=analysis_data.get('pattern_confidence', {}),
                    architecture_description=analysis_data.get('architecture_description', ''),
                    key_components=analysis_data.get('key_components', []),
                    data_flow=analysis_data.get('data_flow', ''),
                    scalability_patterns=analysis_data.get('scalability_patterns', []),
                    design_principles=analysis_data.get('design_principles', [])
                )
                
            except json.JSONDecodeError:
                # Fallback to heuristic analysis
                return self._heuristic_architecture_analysis(file_contents)
                
        except Exception as e:
            logger.error(f"Architecture analysis failed: {e}")
            return self._heuristic_architecture_analysis({})
    
    def _format_files_for_analysis(self, file_contents: Dict[str, str]) -> str:
        """Format file contents for LLM analysis"""
        formatted = []
        for filepath, content in file_contents.items():
            # Truncate very long files
            truncated_content = content[:2000] + "..." if len(content) > 2000 else content
            formatted.append(f"File: {filepath}\n```\n{truncated_content}\n```\n")
        
        return "\n".join(formatted)
    
    def _heuristic_architecture_analysis(self, file_contents: Dict[str, str]) -> ArchitecturalAnalysis:
        """Fallback heuristic architecture analysis"""
        
        patterns = []
        components = []
        
        # Simple pattern detection based on file structure
        file_paths = list(file_contents.keys())
        
        # Check for MVC pattern
        if any('controller' in path.lower() for path in file_paths):
            if any('model' in path.lower() for path in file_paths):
                if any('view' in path.lower() for path in file_paths):
                    patterns.append(ArchitecturalPattern.MVC)
        
        # Check for component-based architecture
        if any('component' in path.lower() for path in file_paths):
            patterns.append(ArchitecturalPattern.COMPONENT_BASED)
        
        # Check for layered architecture
        layers = ['service', 'repository', 'controller', 'model']
        found_layers = sum(1 for layer in layers if any(layer in path.lower() for path in file_paths))
        if found_layers >= 3:
            patterns.append(ArchitecturalPattern.LAYERED)
        
        return ArchitecturalAnalysis(
            primary_patterns=patterns[:2],
            secondary_patterns=patterns[2:],
            pattern_confidence={p.value: 0.6 for p in patterns},
            architecture_description="Architecture analysis based on file structure patterns",
            key_components=components,
            data_flow="Standard request-response flow",
            scalability_patterns=[],
            design_principles=["Separation of Concerns"]
        )
    
    async def _analyze_complexity(
        self,
        repo_full_name: str,
        key_files: List[Dict[str, Any]],
        user_skill_level: str
    ) -> ComplexityAnalysis:
        """Analyze code complexity"""
        
        try:
            complexity_by_file = {}
            complexity_factors = []
            beginner_files = []
            intermediate_files = []
            advanced_files = []
            
            # Analyze complexity of key files
            for file_info in key_files[:15]:  # Analyze top 15 files
                try:
                    content = await self.github_client.get_file_content(
                        repo_full_name, file_info['path']
                    )
                    if content:
                        file_complexity = self._analyze_file_complexity(content, file_info['path'])
                        complexity_by_file[file_info['path']] = file_complexity
                        
                        # Categorize files by complexity
                        if file_complexity in [ComplexityLevel.VERY_LOW, ComplexityLevel.LOW]:
                            beginner_files.append(file_info['path'])
                        elif file_complexity == ComplexityLevel.MEDIUM:
                            intermediate_files.append(file_info['path'])
                        else:
                            advanced_files.append(file_info['path'])
                            
                except Exception as e:
                    logger.warning(f"Failed to analyze complexity for {file_info['path']}: {e}")
                    continue
            
            # Calculate overall complexity
            if complexity_by_file:
                complexity_values = [self._complexity_to_numeric(c) for c in complexity_by_file.values()]
                avg_complexity = sum(complexity_values) / len(complexity_values)
                overall_complexity = self._numeric_to_complexity(avg_complexity)
            else:
                overall_complexity = ComplexityLevel.MEDIUM
            
            # Generate complexity factors
            complexity_factors = self._identify_complexity_factors(complexity_by_file)
            
            # Calculate complexity score
            complexity_score = self._calculate_complexity_score(overall_complexity, complexity_factors)
            
            # Generate skill level recommendation
            skill_recommendation = self._recommend_skill_level(overall_complexity, user_skill_level)
            
            return ComplexityAnalysis(
                overall_complexity=overall_complexity,
                complexity_by_file=complexity_by_file,
                complexity_factors=complexity_factors,
                beginner_friendly_files=beginner_files,
                intermediate_files=intermediate_files,
                advanced_files=advanced_files,
                complexity_score=complexity_score,
                skill_level_recommendation=skill_recommendation
            )
            
        except Exception as e:
            logger.error(f"Complexity analysis failed: {e}")
            return ComplexityAnalysis(
                overall_complexity=ComplexityLevel.MEDIUM,
                complexity_by_file={},
                complexity_factors=[],
                beginner_friendly_files=[],
                intermediate_files=[],
                advanced_files=[],
                complexity_score=50.0,
                skill_level_recommendation="intermediate"
            )
    
    def _analyze_file_complexity(self, content: str, filepath: str) -> ComplexityLevel:
        """Analyze complexity of a single file"""
        
        lines = content.split('\n')
        line_count = len(lines)
        
        # Basic complexity indicators
        complexity_score = 0
        
        # File size factor
        if line_count > 500:
            complexity_score += 3
        elif line_count > 200:
            complexity_score += 2
        elif line_count > 100:
            complexity_score += 1
        
        # Language-specific complexity analysis
        if filepath.endswith('.py'):
            complexity_score += self._analyze_python_complexity(content)
        elif filepath.endswith(('.js', '.jsx', '.ts', '.tsx')):
            complexity_score += self._analyze_javascript_complexity(content)
        elif filepath.endswith('.java'):
            complexity_score += self._analyze_java_complexity(content)
        
        # Convert score to complexity level
        if complexity_score <= 1:
            return ComplexityLevel.VERY_LOW
        elif complexity_score <= 3:
            return ComplexityLevel.LOW
        elif complexity_score <= 6:
            return ComplexityLevel.MEDIUM
        elif complexity_score <= 9:
            return ComplexityLevel.HIGH
        else:
            return ComplexityLevel.VERY_HIGH
    
    def _analyze_python_complexity(self, content: str) -> int:
        """Analyze Python-specific complexity"""
        complexity = 0
        
        # Count complex constructs
        complexity += content.count('class ') * 2
        complexity += content.count('def ') * 1
        complexity += content.count('async def ') * 2
        complexity += content.count('lambda ') * 1
        complexity += content.count('try:') * 1
        complexity += content.count('except') * 1
        complexity += content.count('with ') * 1
        complexity += content.count('yield') * 2
        complexity += content.count('@') * 1  # Decorators
        
        # Advanced patterns
        if 'metaclass' in content:
            complexity += 3
        if '__getattr__' in content or '__setattr__' in content:
            complexity += 2
        if 'threading' in content or 'multiprocessing' in content:
            complexity += 3
        
        return min(complexity // 5, 5)  # Normalize to 0-5 scale
    
    def _analyze_javascript_complexity(self, content: str) -> int:
        """Analyze JavaScript-specific complexity"""
        complexity = 0
        
        # Count complex constructs
        complexity += content.count('function ') * 1
        complexity += content.count('=>') * 1
        complexity += content.count('class ') * 2
        complexity += content.count('async ') * 2
        complexity += content.count('await ') * 1
        complexity += content.count('Promise') * 2
        complexity += content.count('callback') * 1
        complexity += content.count('prototype') * 2
        
        # React/JSX complexity
        if '.jsx' in content or 'React' in content:
            complexity += content.count('useState') * 1
            complexity += content.count('useEffect') * 2
            complexity += content.count('useContext') * 2
            complexity += content.count('useReducer') * 3
        
        # Advanced patterns
        if 'closure' in content or 'bind(' in content:
            complexity += 2
        if 'generator' in content or 'yield' in content:
            complexity += 3
        
        return min(complexity // 5, 5)
    
    def _analyze_java_complexity(self, content: str) -> int:
        """Analyze Java-specific complexity"""
        complexity = 0
        
        # Count complex constructs
        complexity += content.count('class ') * 2
        complexity += content.count('interface ') * 2
        complexity += content.count('abstract ') * 2
        complexity += content.count('synchronized ') * 3
        complexity += content.count('volatile ') * 2
        complexity += content.count('generic') * 2
        complexity += content.count('<T>') * 2
        complexity += content.count('extends ') * 1
        complexity += content.count('implements ') * 1
        
        # Advanced patterns
        if 'reflection' in content.lower():
            complexity += 3
        if 'annotation' in content.lower() or '@' in content:
            complexity += 2
        if 'thread' in content.lower():
            complexity += 3
        
        return min(complexity // 5, 5)
    
    def _complexity_to_numeric(self, complexity: ComplexityLevel) -> float:
        """Convert complexity level to numeric value"""
        mapping = {
            ComplexityLevel.VERY_LOW: 1.0,
            ComplexityLevel.LOW: 2.0,
            ComplexityLevel.MEDIUM: 3.0,
            ComplexityLevel.HIGH: 4.0,
            ComplexityLevel.VERY_HIGH: 5.0
        }
        return mapping.get(complexity, 3.0)
    
    def _numeric_to_complexity(self, value: float) -> ComplexityLevel:
        """Convert numeric value to complexity level"""
        if value <= 1.5:
            return ComplexityLevel.VERY_LOW
        elif value <= 2.5:
            return ComplexityLevel.LOW
        elif value <= 3.5:
            return ComplexityLevel.MEDIUM
        elif value <= 4.5:
            return ComplexityLevel.HIGH
        else:
            return ComplexityLevel.VERY_HIGH
    
    def _identify_complexity_factors(self, complexity_by_file: Dict[str, ComplexityLevel]) -> List[str]:
        """Identify factors contributing to complexity"""
        factors = []
        
        high_complexity_files = [
            path for path, complexity in complexity_by_file.items()
            if complexity in [ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH]
        ]
        
        if len(high_complexity_files) > len(complexity_by_file) * 0.3:
            factors.append("Multiple high-complexity files")
        
        if any('async' in path.lower() for path in complexity_by_file.keys()):
            factors.append("Asynchronous programming patterns")
        
        if any('thread' in path.lower() for path in complexity_by_file.keys()):
            factors.append("Multi-threading implementation")
        
        if any('config' in path.lower() for path in complexity_by_file.keys()):
            factors.append("Complex configuration management")
        
        return factors
    
    def _calculate_complexity_score(self, overall_complexity: ComplexityLevel, factors: List[str]) -> float:
        """Calculate overall complexity score"""
        base_score = self._complexity_to_numeric(overall_complexity) * 20  # 20-100 scale
        factor_penalty = len(factors) * 5
        return min(100, base_score + factor_penalty)
    
    def _recommend_skill_level(self, complexity: ComplexityLevel, user_level: str) -> str:
        """Recommend appropriate skill level for the repository"""
        complexity_to_skill = {
            ComplexityLevel.VERY_LOW: "beginner",
            ComplexityLevel.LOW: "beginner",
            ComplexityLevel.MEDIUM: "intermediate",
            ComplexityLevel.HIGH: "advanced",
            ComplexityLevel.VERY_HIGH: "expert"
        }
        
        recommended = complexity_to_skill.get(complexity, "intermediate")
        
        # Adjust based on user level
        skill_levels = ["beginner", "intermediate", "advanced", "expert"]
        user_index = skill_levels.index(user_level) if user_level in skill_levels else 1
        recommended_index = skill_levels.index(recommended)
        
        # If repository is too complex, suggest it's for learning advanced concepts
        if recommended_index > user_index + 1:
            return f"advanced (challenging for {user_level})"
        elif recommended_index < user_index - 1:
            return f"beginner (may be too simple for {user_level})"
        else:
            return recommended
    
    # Additional methods for learning opportunities, educational segments, etc.
    # would continue here... (truncated for length)
    
    async def _identify_learning_opportunities(
        self,
        repo_full_name: str,
        key_files: List[Dict[str, Any]],
        architecture: ArchitecturalAnalysis,
        user_skill_level: str,
        focus_areas: List[str] = None
    ) -> List[LearningOpportunity]:
        """Identify learning opportunities in the repository"""
        
        opportunities = []
        
        # Generate opportunities based on architectural patterns
        for pattern in architecture.primary_patterns:
            opportunity = LearningOpportunity(
                id=f"arch_{pattern.value}",
                title=f"Study {pattern.value.replace('_', ' ').title()} Pattern",
                description=f"Learn how the {pattern.value.replace('_', ' ')} pattern is implemented in this codebase",
                file_paths=[],  # Would be populated with relevant files
                concepts=[pattern.value, "architecture", "design patterns"],
                difficulty=user_skill_level,
                estimated_time="2-3 hours",
                prerequisites=["basic programming concepts"],
                learning_objectives=[
                    f"Understand {pattern.value.replace('_', ' ')} pattern implementation",
                    "Identify pattern benefits and trade-offs",
                    "Apply pattern in own projects"
                ],
                code_examples=[],
                related_opportunities=[]
            )
            opportunities.append(opportunity)
        
        return opportunities[:10]  # Limit to 10 opportunities
    
    async def _extract_educational_segments(
        self,
        repo_full_name: str,
        key_files: List[Dict[str, Any]],
        user_skill_level: str
    ) -> List[CodeSegment]:
        """Extract educational code segments"""
        
        segments = []
        
        # This would analyze code and extract meaningful segments
        # For now, return empty list as placeholder
        
        return segments
    
    async def _calculate_educational_scores(
        self,
        repo_full_name: str,
        architecture: ArchitecturalAnalysis,
        complexity: ComplexityAnalysis,
        opportunities: List[LearningOpportunity]
    ) -> Dict[str, Any]:
        """Calculate educational value scores"""
        
        # Calculate scores based on analysis
        educational_value = min(100, len(opportunities) * 10 + len(architecture.primary_patterns) * 15)
        beginner_friendliness = 100 - complexity.complexity_score
        code_quality = len(architecture.design_principles) * 20
        documentation_quality = 70  # Would be calculated from actual documentation analysis
        
        skill_level_match = {
            "beginner": max(0, 100 - complexity.complexity_score),
            "intermediate": min(100, complexity.complexity_score + 20),
            "advanced": min(100, complexity.complexity_score + 40),
            "expert": complexity.complexity_score
        }
        
        return {
            'educational_value': educational_value,
            'beginner_friendliness': beginner_friendliness,
            'code_quality': code_quality,
            'documentation_quality': documentation_quality,
            'skill_level_match': skill_level_match
        }
    
    async def _generate_learning_path(
        self,
        opportunities: List[LearningOpportunity],
        user_skill_level: str
    ) -> List[str]:
        """Generate recommended learning path"""
        
        # Sort opportunities by difficulty and create learning path
        path = []
        for opportunity in opportunities:
            path.append(f"Study: {opportunity.title}")
        
        return path[:8]  # Limit to 8 steps
    
    def _organize_files_by_type(self, structure: Dict[str, Any]) -> Dict[str, List[str]]:
        """Organize files by type"""
        organization = {
            'source': [],
            'config': [],
            'documentation': [],
            'tests': [],
            'assets': []
        }
        
        def categorize_files(current_structure, current_path=""):
            for name, content in current_structure.items():
                full_path = f"{current_path}/{name}" if current_path else name
                
                if isinstance(content, dict) and content.get('type') == 'file':
                    # Categorize file
                    if name.lower().endswith(('.py', '.js', '.java', '.go', '.rs', '.cs')):
                        organization['source'].append(full_path)
                    elif name.lower().endswith(('.json', '.yaml', '.yml', '.toml', '.ini')):
                        organization['config'].append(full_path)
                    elif name.lower().endswith(('.md', '.rst', '.txt')):
                        organization['documentation'].append(full_path)
                    elif 'test' in name.lower() or 'spec' in name.lower():
                        organization['tests'].append(full_path)
                    else:
                        organization['assets'].append(full_path)
                elif isinstance(content, dict) and 'type' not in content:
                    categorize_files(content, full_path)
        
        categorize_files(structure)
        return organization
    
    def _extract_key_directories(self, structure: Dict[str, Any]) -> List[str]:
        """Extract key directories from structure"""
        key_dirs = []
        
        def find_directories(current_structure, current_path=""):
            for name, content in current_structure.items():
                full_path = f"{current_path}/{name}" if current_path else name
                
                if isinstance(content, dict) and 'type' not in content:
                    # This is a directory
                    if name.lower() in ['src', 'app', 'lib', 'components', 'services', 'controllers', 'models']:
                        key_dirs.append(full_path)
                    find_directories(content, full_path)
        
        find_directories(structure)
        return key_dirs
    
    def _identify_entry_points(self, key_files: List[Dict[str, Any]]) -> List[str]:
        """Identify entry points of the application"""
        entry_points = []
        
        entry_file_patterns = [
            'main.py', 'app.py', 'index.js', 'main.js', 'app.js',
            'main.go', 'main.rs', 'Program.cs', 'Main.java'
        ]
        
        for file_info in key_files:
            if file_info['name'].lower() in [p.lower() for p in entry_file_patterns]:
                entry_points.append(file_info['path'])
        
        return entry_points
    
    def _recommend_focus_areas(self, opportunities: List[LearningOpportunity]) -> List[str]:
        """Recommend focus areas based on learning opportunities"""
        focus_areas = []
        
        # Extract concepts from opportunities
        all_concepts = []
        for opportunity in opportunities:
            all_concepts.extend(opportunity.concepts)
        
        # Count concept frequency
        concept_counts = {}
        for concept in all_concepts:
            concept_counts[concept] = concept_counts.get(concept, 0) + 1
        
        # Get top concepts as focus areas
        sorted_concepts = sorted(concept_counts.items(), key=lambda x: x[1], reverse=True)
        focus_areas = [concept for concept, count in sorted_concepts[:5]]
        
        return focus_areas
    
    async def _get_cached_analysis(self, cache_key: str) -> Optional[RepositoryAnalysis]:
        """Get cached analysis"""
        try:
            cached_data = await cache_manager.get(cache_key)
            if cached_data:
                analysis_dict = json.loads(cached_data)
                # Convert dict back to RepositoryAnalysis
                # This is simplified - in production, you'd want proper deserialization
                return RepositoryAnalysis(**analysis_dict)
        except Exception as e:
            logger.warning(f"Failed to get cached analysis: {e}")
        return None
    
    async def _cache_analysis(self, cache_key: str, analysis: RepositoryAnalysis):
        """Cache analysis results"""
        try:
            analysis_dict = asdict(analysis)
            cached_data = json.dumps(analysis_dict, default=str)
            await cache_manager.set(cache_key, cached_data, ttl=self.cache_ttl)
        except Exception as e:
            logger.warning(f"Failed to cache analysis: {e}")

# Factory function
def create_repository_analysis_agent(
    llm_provider: LLMProvider,
    github_client: GitHubClient
) -> RepositoryAnalysisAgent:
    """Create repository analysis agent instance"""
    return RepositoryAnalysisAgent(llm_provider, github_client)