"""
Specification Generator Engine for The Reverse Engineer Coach.

This module implements pattern extraction, code analysis, and specification generation
for transforming complex production systems into structured learning curricula.
"""

import re
import ast
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path

from app.mcp_client import CodeSnippet, RepositoryAnalysis
from app.llm_provider import (
    BaseLLMProvider, 
    LLMProviderFactory, 
    SpecificationPrompt,
    LLMResponse
)
from app.types import (
    ArchitecturalPattern, PatternAnalysis, StructuralElement, SimplifiedCode,
    ProgrammingLanguage, LanguageSpecification
)
from app.task_generator import TaskGenerator, LearningPath
from app.language_support import (
    LanguageSupport, LanguageSpecificTaskGenerator, CrossLanguageTranslator
)

logger = logging.getLogger(__name__)


class CodePatternExtractor:
    """Extracts and identifies architectural patterns from code"""
    
    # Pattern recognition rules
    PATTERN_RULES = {
        ArchitecturalPattern.HANDLER: {
            'name_patterns': [r'.*handler.*', r'.*processor.*', r'.*controller.*'],
            'method_patterns': [r'handle.*', r'process.*', r'execute.*'],
            'interface_indicators': ['handle', 'process', 'execute']
        },
        ArchitecturalPattern.SERVICE_LAYER: {
            'name_patterns': [r'.*service.*', r'.*manager.*'],
            'method_patterns': [r'create.*', r'update.*', r'delete.*', r'get.*'],
            'interface_indicators': ['service', 'manager']
        },
        ArchitecturalPattern.REPOSITORY: {
            'name_patterns': [r'.*repository.*', r'.*repo.*', r'.*dao.*'],
            'method_patterns': [r'save.*', r'find.*', r'delete.*', r'update.*'],
            'interface_indicators': ['repository', 'store', 'dao']
        },
        ArchitecturalPattern.FACTORY: {
            'name_patterns': [r'.*factory.*', r'.*creator.*'],
            'method_patterns': [r'create.*', r'build.*', r'make.*', r'new.*'],
            'interface_indicators': ['factory', 'creator', 'builder']
        },
        ArchitecturalPattern.OBSERVER: {
            'name_patterns': [r'.*observer.*', r'.*listener.*', r'.*subscriber.*'],
            'method_patterns': [r'notify.*', r'update.*', r'on.*', r'subscribe.*'],
            'interface_indicators': ['observer', 'listener', 'subscriber']
        },
        ArchitecturalPattern.STRATEGY: {
            'name_patterns': [r'.*strategy.*', r'.*algorithm.*', r'.*policy.*'],
            'method_patterns': [r'execute.*', r'apply.*', r'run.*'],
            'interface_indicators': ['strategy', 'algorithm', 'policy']
        }
    }
    
    @classmethod
    def extract_structural_elements(cls, code_snippets: List[CodeSnippet]) -> List[StructuralElement]:
        """Extract structural elements from code snippets"""
        elements = []
        
        for snippet in code_snippets:
            element = cls._create_structural_element(snippet)
            if element:
                elements.append(element)
        
        return elements
    
    @classmethod
    def _create_structural_element(cls, snippet: CodeSnippet) -> Optional[StructuralElement]:
        """Create a structural element from a code snippet"""
        try:
            # Extract dependencies, methods, and properties based on language
            dependencies = cls._extract_dependencies(snippet.content, snippet.language)
            methods = cls._extract_methods(snippet.content, snippet.language)
            properties = cls._extract_properties(snippet.content, snippet.language)
            
            # Identify patterns
            patterns = cls._identify_patterns(snippet.name, methods, snippet.snippet_type)
            
            # Calculate complexity and significance
            complexity = cls._calculate_complexity(snippet.content, methods, dependencies)
            
            element = StructuralElement(
                name=snippet.name,
                element_type=snippet.snippet_type,
                file_path=snippet.file_path,
                start_line=snippet.start_line,
                end_line=snippet.end_line,
                language=snippet.language,
                content=snippet.content,
                dependencies=dependencies,
                methods=methods,
                properties=properties,
                patterns=patterns,
                complexity_score=complexity,
                architectural_significance=snippet.architectural_significance
            )
            
            return element
            
        except Exception as e:
            logger.warning(f"Failed to create structural element from snippet {snippet.name}: {e}")
            return None
    
    @classmethod
    def _extract_dependencies(cls, content: str, language: str) -> List[str]:
        """Extract dependencies from code content"""
        dependencies = []
        
        if language.lower() == 'python':
            # Extract imports
            import_patterns = [
                r'from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import',
                r'import\s+([a-zA-Z_][a-zA-Z0-9_.]*)'
            ]
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                dependencies.extend(matches)
        
        elif language.lower() == 'go':
            # Extract Go imports
            import_pattern = r'import\s+(?:\(\s*)?(?:"([^"]+)"|`([^`]+)`)'
            matches = re.findall(import_pattern, content)
            dependencies.extend([m[0] or m[1] for m in matches])
        
        elif language.lower() in ['typescript', 'javascript']:
            # Extract TypeScript/JavaScript imports
            import_patterns = [
                r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]',
                r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
            ]
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                dependencies.extend(matches)
        
        # Filter out standard library imports and keep only relevant ones
        filtered_deps = []
        for dep in dependencies:
            if not any(std in dep.lower() for std in ['std', 'builtin', 'os', 'sys', 'time']):
                filtered_deps.append(dep)
        
        return list(set(filtered_deps))  # Remove duplicates
    
    @classmethod
    def _extract_methods(cls, content: str, language: str) -> List[str]:
        """Extract method names from code content"""
        methods = []
        
        if language.lower() == 'python':
            # Extract Python methods
            method_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
            methods = re.findall(method_pattern, content)
        
        elif language.lower() == 'go':
            # Extract Go functions/methods
            func_pattern = r'func\s+(?:\([^)]*\)\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
            methods = re.findall(func_pattern, content)
        
        elif language.lower() in ['typescript', 'javascript']:
            # Extract TypeScript/JavaScript methods
            method_patterns = [
                r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*{',  # Regular methods
                r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*\([^)]*\)\s*=>', # Arrow functions
                r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('  # Function declarations
            ]
            for pattern in method_patterns:
                methods.extend(re.findall(pattern, content))
        
        # Filter out private methods and common getters/setters
        filtered_methods = []
        for method in methods:
            if not method.startswith('_') and method not in ['get', 'set', 'toString', 'valueOf']:
                filtered_methods.append(method)
        
        return list(set(filtered_methods))  # Remove duplicates
    
    @classmethod
    def _extract_properties(cls, content: str, language: str) -> List[str]:
        """Extract property names from code content"""
        properties = []
        
        if language.lower() == 'python':
            # Extract Python class attributes
            attr_pattern = r'self\.([a-zA-Z_][a-zA-Z0-9_]*)\s*='
            properties = re.findall(attr_pattern, content)
        
        elif language.lower() == 'go':
            # Extract Go struct fields (simplified)
            field_pattern = r'^\s*([A-Z][a-zA-Z0-9_]*)\s+[a-zA-Z]'
            properties = re.findall(field_pattern, content, re.MULTILINE)
        
        elif language.lower() in ['typescript', 'javascript']:
            # Extract TypeScript/JavaScript properties
            prop_patterns = [
                r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*[a-zA-Z]',  # Type annotations
                r'this\.([a-zA-Z_][a-zA-Z0-9_]*)\s*='  # Instance properties
            ]
            for pattern in prop_patterns:
                properties.extend(re.findall(pattern, content))
        
        return list(set(properties))  # Remove duplicates
    
    @classmethod
    def _identify_patterns(cls, name: str, methods: List[str], element_type: str) -> List[ArchitecturalPattern]:
        """Identify architectural patterns based on naming and structure"""
        patterns = []
        name_lower = name.lower()
        methods_lower = [m.lower() for m in methods]
        
        for pattern, rules in cls.PATTERN_RULES.items():
            confidence = 0.0
            
            # Check name patterns
            for name_pattern in rules.get('name_patterns', []):
                if re.match(name_pattern, name_lower):
                    confidence += 0.4
            
            # Check method patterns
            for method_pattern in rules.get('method_patterns', []):
                if any(re.match(method_pattern, method) for method in methods_lower):
                    confidence += 0.3
            
            # Check interface indicators
            if element_type == 'interface':
                for indicator in rules.get('interface_indicators', []):
                    if indicator in name_lower:
                        confidence += 0.3
            
            # Add pattern if confidence is high enough
            if confidence >= 0.4:
                patterns.append(pattern)
        
        return patterns
    
    @classmethod
    def _calculate_complexity(cls, content: str, methods: List[str], dependencies: List[str]) -> float:
        """Calculate complexity score for a structural element"""
        # Base complexity from content length
        length_score = min(len(content) / 1000, 0.3)
        
        # Complexity from number of methods
        method_score = min(len(methods) / 10, 0.3)
        
        # Complexity from dependencies
        dep_score = min(len(dependencies) / 5, 0.2)
        
        # Complexity from nesting (count braces/indentation)
        nesting_score = min(content.count('{') / 10, 0.2)
        
        return min(length_score + method_score + dep_score + nesting_score, 1.0)


class CodeSimplifier:
    """Simplifies code by removing production complexity while preserving architectural essence"""
    
    # Production complexity patterns to remove
    COMPLEXITY_PATTERNS = {
        'logging': [
            r'logger\.[a-zA-Z]+\([^)]*\)',
            r'log\.[a-zA-Z]+\([^)]*\)',
            r'console\.[a-zA-Z]+\([^)]*\)',
            r'fmt\.Print[a-zA-Z]*\([^)]*\)'
        ],
        'error_handling': [
            r'try:\s*\n.*?except.*?:\s*\n.*?(?=\n\S|\Z)',
            r'if\s+err\s*!=\s*nil\s*{[^}]*}',
            r'catch\s*\([^)]*\)\s*{[^}]*}'
        ],
        'metrics': [
            r'metrics\.[a-zA-Z]+\([^)]*\)',
            r'prometheus\.[a-zA-Z]+\([^)]*\)',
            r'statsd\.[a-zA-Z]+\([^)]*\)'
        ],
        'configuration': [
            r'config\.[a-zA-Z]+',
            r'settings\.[a-zA-Z]+',
            r'env\.[a-zA-Z]+'
        ],
        'validation': [
            r'validate\.[a-zA-Z]+\([^)]*\)',
            r'if\s+.*\s*==\s*nil\s*{[^}]*return[^}]*}',
            r'if\s+.*\s*is\s+None:[^:]*return[^:]*'
        ]
    }
    
    @classmethod
    def simplify_code(cls, elements: List[StructuralElement]) -> List[SimplifiedCode]:
        """Simplify structural elements by removing production complexity"""
        simplified = []
        
        for element in elements:
            simplified_element = cls._simplify_element(element)
            if simplified_element:
                simplified.append(simplified_element)
        
        return simplified
    
    @classmethod
    def _simplify_element(cls, element: StructuralElement) -> Optional[SimplifiedCode]:
        """Simplify a single structural element"""
        try:
            content = element.content
            removed_complexity = []
            
            # Remove production complexity patterns
            for complexity_type, patterns in cls.COMPLEXITY_PATTERNS.items():
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
                    if matches:
                        content = re.sub(pattern, '', content, flags=re.DOTALL | re.MULTILINE)
                        removed_complexity.append(complexity_type)
            
            # Clean up extra whitespace
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
            content = content.strip()
            
            # Identify preserved patterns
            preserved_patterns = element.patterns
            
            # Determine learning focus
            learning_focus = cls._determine_learning_focus(element, removed_complexity)
            
            # Only return if we actually simplified something
            if removed_complexity or len(content) < len(element.content):
                return SimplifiedCode(
                    original_element=element,
                    simplified_content=content,
                    removed_complexity=list(set(removed_complexity)),
                    preserved_patterns=preserved_patterns,
                    learning_focus=learning_focus
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to simplify element {element.name}: {e}")
            return None
    
    @classmethod
    def _determine_learning_focus(cls, element: StructuralElement, 
                                removed_complexity: List[str]) -> List[str]:
        """Determine what the learner should focus on in this element"""
        focus = []
        
        # Focus based on element type
        if element.element_type == 'interface':
            focus.append('Interface Design')
            focus.append('Contract Definition')
        elif element.element_type == 'class':
            focus.append('Class Structure')
            focus.append('Encapsulation')
        elif element.element_type == 'struct':
            focus.append('Data Structure')
            focus.append('Type Definition')
        
        # Focus based on identified patterns
        for pattern in element.patterns:
            if pattern == ArchitecturalPattern.HANDLER:
                focus.append('Request Processing')
            elif pattern == ArchitecturalPattern.SERVICE_LAYER:
                focus.append('Business Logic')
            elif pattern == ArchitecturalPattern.REPOSITORY:
                focus.append('Data Access')
            elif pattern == ArchitecturalPattern.FACTORY:
                focus.append('Object Creation')
        
        # Focus based on removed complexity
        if 'error_handling' in removed_complexity:
            focus.append('Core Logic Flow')
        if 'logging' in removed_complexity:
            focus.append('Primary Functionality')
        if 'metrics' in removed_complexity:
            focus.append('Business Operations')
        
        return list(set(focus))  # Remove duplicates


class PatternAnalyzer:
    """Analyzes architectural patterns and their learning value"""
    
    @classmethod
    def analyze_patterns(cls, elements: List[StructuralElement]) -> List[PatternAnalysis]:
        """Analyze architectural patterns found in structural elements"""
        pattern_evidence = {}
        
        # Collect evidence for each pattern
        for element in elements:
            for pattern in element.patterns:
                if pattern not in pattern_evidence:
                    pattern_evidence[pattern] = {
                        'elements': [],
                        'files': set(),
                        'confidence_scores': []
                    }
                
                pattern_evidence[pattern]['elements'].append(element.name)
                pattern_evidence[pattern]['files'].add(element.file_path)
                pattern_evidence[pattern]['confidence_scores'].append(
                    element.architectural_significance
                )
        
        # Create pattern analyses
        analyses = []
        for pattern, evidence in pattern_evidence.items():
            analysis = cls._create_pattern_analysis(pattern, evidence)
            if analysis:
                analyses.append(analysis)
        
        # Sort by learning value
        analyses.sort(key=lambda x: x.learning_value, reverse=True)
        return analyses
    
    @classmethod
    def _create_pattern_analysis(cls, pattern: ArchitecturalPattern, 
                               evidence: Dict) -> Optional[PatternAnalysis]:
        """Create a pattern analysis from collected evidence"""
        try:
            # Calculate confidence based on evidence strength
            confidence = min(
                len(evidence['elements']) / 3,  # More elements = higher confidence
                sum(evidence['confidence_scores']) / len(evidence['confidence_scores'])
            )
            
            # Determine learning value
            learning_value = cls._calculate_learning_value(pattern, evidence)
            
            # Determine implementation complexity
            complexity = cls._determine_implementation_complexity(pattern, evidence)
            
            return PatternAnalysis(
                pattern=pattern,
                confidence=confidence,
                evidence=evidence['elements'],
                related_files=list(evidence['files']),
                learning_value=learning_value,
                implementation_complexity=complexity
            )
            
        except Exception as e:
            logger.warning(f"Failed to create pattern analysis for {pattern}: {e}")
            return None
    
    @classmethod
    def _calculate_learning_value(cls, pattern: ArchitecturalPattern, 
                                evidence: Dict) -> float:
        """Calculate educational learning value of a pattern"""
        base_values = {
            ArchitecturalPattern.HANDLER: 0.9,
            ArchitecturalPattern.SERVICE_LAYER: 0.8,
            ArchitecturalPattern.REPOSITORY: 0.8,
            ArchitecturalPattern.FACTORY: 0.7,
            ArchitecturalPattern.OBSERVER: 0.8,
            ArchitecturalPattern.STRATEGY: 0.7,
            ArchitecturalPattern.DEPENDENCY_INJECTION: 0.9,
            ArchitecturalPattern.MVC: 0.8,
            ArchitecturalPattern.MICROSERVICE: 0.9,
            ArchitecturalPattern.CIRCUIT_BREAKER: 0.8,
        }
        
        base_value = base_values.get(pattern, 0.5)
        
        # Boost value based on evidence strength
        evidence_boost = min(len(evidence['elements']) / 5, 0.2)
        
        return min(base_value + evidence_boost, 1.0)
    
    @classmethod
    def _determine_implementation_complexity(cls, pattern: ArchitecturalPattern, 
                                          evidence: Dict) -> str:
        """Determine implementation complexity level"""
        complexity_map = {
            ArchitecturalPattern.HANDLER: 'beginner',
            ArchitecturalPattern.SERVICE_LAYER: 'intermediate',
            ArchitecturalPattern.REPOSITORY: 'beginner',
            ArchitecturalPattern.FACTORY: 'beginner',
            ArchitecturalPattern.OBSERVER: 'intermediate',
            ArchitecturalPattern.STRATEGY: 'intermediate',
            ArchitecturalPattern.DEPENDENCY_INJECTION: 'advanced',
            ArchitecturalPattern.MVC: 'intermediate',
            ArchitecturalPattern.MICROSERVICE: 'advanced',
            ArchitecturalPattern.CIRCUIT_BREAKER: 'advanced',
        }
        
        base_complexity = complexity_map.get(pattern, 'intermediate')
        
        # Adjust based on evidence complexity
        avg_confidence = sum(evidence['confidence_scores']) / len(evidence['confidence_scores'])
        if avg_confidence > 0.8 and len(evidence['elements']) > 3:
            if base_complexity == 'beginner':
                return 'intermediate'
            elif base_complexity == 'intermediate':
                return 'advanced'
        
        return base_complexity


class SpecificationGenerator:
    """Main specification generator that orchestrates pattern extraction and analysis"""
    
    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None, github_token: Optional[str] = None, ai_api_key: Optional[str] = None, ai_provider: str = "openai"):
        self.pattern_extractor = CodePatternExtractor()
        self.code_simplifier = CodeSimplifier()
        self.pattern_analyzer = PatternAnalyzer()
        
        # Initialize LLM provider with user credentials if provided
        if ai_api_key:
            from app.llm_provider import LLMProvider
            provider_type = LLMProvider.OPENAI if ai_provider == "openai" else LLMProvider.ANTHROPIC
            self.llm_provider = LLMProviderFactory.create_provider(provider_type, ai_api_key)
        else:
            self.llm_provider = llm_provider or LLMProviderFactory.get_default_provider()
        
        self.task_generator = TaskGenerator()
        self.language_support = LanguageSupport()
        self.language_task_generator = LanguageSpecificTaskGenerator(self.llm_provider)
        self.cross_language_translator = CrossLanguageTranslator(self.llm_provider)
        
        # Store credentials for MCP client usage
        self.github_token = github_token
        self.ai_api_key = ai_api_key
        self.ai_provider = ai_provider
    
    async def generate_specification(self, repository_analysis: RepositoryAnalysis, 
                                   target_audience: str = "mid-level software engineers",
                                   learning_objectives: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate a complete specification from repository analysis.
        
        Args:
            repository_analysis: Complete repository analysis from MCP client
            target_audience: Target audience for the learning content
            learning_objectives: Specific learning objectives to focus on
            
        Returns:
            Dict containing specification data for curriculum generation
        """
        logger.info(f"Generating specification for {repository_analysis.repository_url}")
        
        # Extract structural elements
        structural_elements = self.pattern_extractor.extract_structural_elements(
            repository_analysis.code_snippets
        )
        
        logger.info(f"Extracted {len(structural_elements)} structural elements")
        
        # Simplify code elements
        simplified_elements = self.code_simplifier.simplify_code(structural_elements)
        
        logger.info(f"Simplified {len(simplified_elements)} code elements")
        
        # Analyze patterns
        pattern_analyses = self.pattern_analyzer.analyze_patterns(structural_elements)
        
        logger.info(f"Identified {len(pattern_analyses)} architectural patterns")
        
        # Generate LLM-powered specification
        llm_specification = await self._generate_llm_specification(
            repository_analysis, structural_elements, pattern_analyses, 
            target_audience, learning_objectives
        )
        
        # Generate learning tasks
        learning_tasks = await self._generate_learning_tasks(
            llm_specification, target_audience
        )
        
        # Generate specification
        specification = {
            'repository_info': {
                'url': repository_analysis.repository_url,
                'name': repository_analysis.metadata.name,
                'description': repository_analysis.metadata.description,
                'language': repository_analysis.primary_language,
                'complexity_score': repository_analysis.complexity_score,
                'stars': repository_analysis.metadata.stars
            },
            'structural_elements': [
                {
                    'name': elem.name,
                    'type': elem.element_type,
                    'file_path': elem.file_path,
                    'patterns': [p.value for p in elem.patterns],
                    'complexity_score': elem.complexity_score,
                    'architectural_significance': elem.architectural_significance,
                    'methods': elem.methods,
                    'dependencies': elem.dependencies
                }
                for elem in structural_elements
            ],
            'simplified_code': [
                {
                    'name': simp.original_element.name,
                    'simplified_content': simp.simplified_content,
                    'removed_complexity': simp.removed_complexity,
                    'preserved_patterns': [p.value for p in simp.preserved_patterns],
                    'learning_focus': simp.learning_focus
                }
                for simp in simplified_elements
            ],
            'pattern_analysis': [
                {
                    'pattern': analysis.pattern.value,
                    'confidence': analysis.confidence,
                    'evidence': analysis.evidence,
                    'related_files': analysis.related_files,
                    'learning_value': analysis.learning_value,
                    'implementation_complexity': analysis.implementation_complexity
                }
                for analysis in pattern_analyses
            ],
            'architecture_insights': {
                'detected_patterns': repository_analysis.architecture_patterns,
                'total_files_analyzed': repository_analysis.total_files_analyzed,
                'code_snippets_count': len(repository_analysis.code_snippets),
                'primary_language': repository_analysis.primary_language
            },
            'llm_generated_content': {
                'specification_markdown': llm_specification.content if llm_specification.success else "",
                'learning_tasks_markdown': learning_tasks.content if learning_tasks.success else "",
                'generation_success': llm_specification.success and learning_tasks.success,
                'tokens_used': (llm_specification.tokens_used if llm_specification.success else 0) + 
                              (learning_tasks.tokens_used if learning_tasks.success else 0)
            }
        }
        
        logger.info("Specification generation complete")
        return specification
    
    async def _generate_llm_specification(self, repository_analysis: RepositoryAnalysis,
                                        structural_elements: List[StructuralElement],
                                        pattern_analyses: List[PatternAnalysis],
                                        target_audience: str,
                                        learning_objectives: Optional[List[str]]) -> LLMResponse:
        """Generate LLM-powered specification content"""
        try:
            # Prepare prompt data
            prompt = SpecificationPrompt(
                repository_info={
                    'name': repository_analysis.metadata.name,
                    'description': repository_analysis.metadata.description,
                    'language': repository_analysis.primary_language,
                    'complexity_score': repository_analysis.complexity_score,
                    'stars': repository_analysis.metadata.stars
                },
                structural_elements=[
                    {
                        'name': elem.name,
                        'type': elem.element_type,
                        'patterns': [p.value for p in elem.patterns],
                        'complexity_score': elem.complexity_score,
                        'architectural_significance': elem.architectural_significance
                    }
                    for elem in structural_elements[:10]  # Limit to top 10 elements
                ],
                pattern_analysis=[
                    {
                        'pattern': analysis.pattern.value,
                        'confidence': analysis.confidence,
                        'learning_value': analysis.learning_value,
                        'implementation_complexity': analysis.implementation_complexity
                    }
                    for analysis in pattern_analyses
                ],
                target_audience=target_audience,
                learning_objectives=learning_objectives
            )
            
            # Generate specification using LLM
            async with self.llm_provider as provider:
                response = await provider.generate_specification(prompt)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate LLM specification: {e}")
            return LLMResponse(
                content="",
                provider=self.llm_provider.__class__.__name__,
                model="unknown",
                tokens_used=0,
                success=False,
                error_message=str(e)
            )
    
    async def _generate_learning_tasks(self, specification_response: LLMResponse,
                                     target_audience: str) -> LLMResponse:
        """Generate learning tasks from specification"""
        try:
            if not specification_response.success:
                return LLMResponse(
                    content="",
                    provider=specification_response.provider,
                    model=specification_response.model,
                    tokens_used=0,
                    success=False,
                    error_message="Cannot generate tasks from failed specification"
                )
            
            # Determine difficulty level from target audience
            difficulty_map = {
                'junior': 'beginner',
                'mid-level': 'intermediate',
                'senior': 'advanced',
                'staff': 'advanced',
                'principal': 'advanced'
            }
            
            difficulty = 'intermediate'  # default
            for key, value in difficulty_map.items():
                if key in target_audience.lower():
                    difficulty = value
                    break
            
            # Generate tasks using LLM
            async with self.llm_provider as provider:
                response = await provider.generate_learning_tasks(
                    specification_response.content, difficulty
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate learning tasks: {e}")
            return LLMResponse(
                content="",
                provider=specification_response.provider,
                model=specification_response.model,
                tokens_used=0,
                success=False,
                error_message=str(e)
            )
    
    async def generate_code_explanation(self, code_snippet: CodeSnippet) -> Dict[str, Any]:
        """Generate simplified explanation for a specific code snippet"""
        try:
            # Extract patterns from the snippet
            element = self.pattern_extractor._create_structural_element(code_snippet)
            if not element:
                return {
                    'success': False,
                    'error': 'Failed to analyze code snippet'
                }
            
            patterns = [p.value for p in element.patterns]
            
            # Generate explanation using LLM
            async with self.llm_provider as provider:
                response = await provider.simplify_code_explanation(
                    code_snippet.content, patterns, code_snippet.language
                )
            
            return {
                'success': response.success,
                'explanation': response.content if response.success else "",
                'patterns_identified': patterns,
                'tokens_used': response.tokens_used,
                'error_message': response.error_message
            }
            
        except Exception as e:
            logger.error(f"Failed to generate code explanation: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def generate_complete_learning_path(self, repository_analysis: RepositoryAnalysis,
                                            target_audience: str = "mid-level software engineers",
                                            learning_objectives: Optional[List[str]] = None,
                                            focus_patterns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate a complete learning path including specification and task sequence.
        
        Args:
            repository_analysis: Complete repository analysis from MCP client
            target_audience: Target audience for the learning content
            learning_objectives: Specific learning objectives to focus on
            focus_patterns: Optional list of patterns to focus on
            
        Returns:
            Dict containing complete learning path with tasks and specifications
        """
        try:
            # Generate specification
            specification = await self.generate_specification(
                repository_analysis, target_audience, learning_objectives
            )
            
            # Generate learning path with task sequence
            learning_path = self.task_generator.generate_learning_path(
                specification, target_audience, focus_patterns
            )
            
            # Link tasks to code snippets
            linked_tasks = self.task_generator.link_tasks_to_snippets(
                learning_path.tasks, repository_analysis.code_snippets
            )
            learning_path.tasks = linked_tasks
            
            # Export as markdown
            learning_path_markdown = self.task_generator.export_learning_path_markdown(learning_path)
            
            return {
                'success': True,
                'specification': specification,
                'learning_path': {
                    'name': learning_path.name,
                    'description': learning_path.description,
                    'target_audience': learning_path.target_audience,
                    'total_estimated_hours': learning_path.total_estimated_hours,
                    'tasks': [
                        {
                            'id': task.id,
                            'title': task.title,
                            'description': task.description,
                            'task_type': task.task_type.value,
                            'difficulty': task.difficulty.value,
                            'estimated_hours': task.estimated_hours,
                            'prerequisites': task.prerequisites,
                            'learning_objectives': task.learning_objectives,
                            'success_criteria': task.success_criteria,
                            'reference_snippets': task.reference_snippets,
                            'deliverables': task.deliverables,
                            'hints': task.hints,
                            'patterns_practiced': [p.value for p in task.patterns_practiced],
                            'order_index': task.order_index
                        }
                        for task in learning_path.tasks
                    ],
                    'milestones': learning_path.milestones,
                    'completion_criteria': learning_path.completion_criteria
                },
                'learning_path_markdown': learning_path_markdown,
                'task_count': len(learning_path.tasks),
                'pattern_count': len(specification.get('pattern_analysis', [])),
                'tokens_used': specification.get('llm_generated_content', {}).get('tokens_used', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate complete learning path: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    async def generate_learning_spec_with_language(self, 
                                                 repository_url: str,
                                                 architecture_topic: str,
                                                 target_language: ProgrammingLanguage,
                                                 preferred_frameworks: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate learning specification with language-specific adaptations.
        
        Args:
            repository_url: GitHub repository URL to analyze
            architecture_topic: Architecture topic to focus on
            target_language: Target programming language for implementation
            preferred_frameworks: Preferred frameworks for the target language
            
        Returns:
            Complete learning specification with language-specific tasks
        """
        try:
            # First, perform standard repository analysis
            from app.mcp_client import MCPClient
            mcp_client = MCPClient()
            
            # Analyze repository
            repository_analysis = await mcp_client.analyze_repository(
                repository_url, architecture_topic
            )
            
            if not repository_analysis:
                return {
                    'success': False,
                    'error': 'Failed to analyze repository'
                }
            
            # Generate base specification
            base_specification = await self.generate_specification(
                repository_analysis, f"developers using {target_language.value}"
            )
            
            # Detect source language from repository
            source_language = self.language_support.detect_source_language(
                repository_analysis.code_snippets[0].content if repository_analysis.code_snippets else ""
            )
            
            # Generate language-specific tasks
            base_tasks = base_specification.get('llm_generated_content', {}).get('learning_tasks_markdown', '')
            
            if base_tasks:
                # Parse base tasks (simplified parsing for demo)
                parsed_tasks = self._parse_tasks_from_markdown(base_tasks)
                
                # Generate language-specific adaptations
                language_specific_tasks = await self.language_task_generator.generate_language_specific_tasks(
                    parsed_tasks, target_language, source_language
                )
                
                # Add cross-language translation examples if needed
                if source_language != target_language:
                    translation_examples = await self._generate_translation_examples(
                        repository_analysis.code_snippets[:3],  # Use first 3 snippets
                        source_language,
                        target_language
                    )
                    base_specification['translation_examples'] = translation_examples
                
                # Update specification with language-specific content
                base_specification['language_specific_tasks'] = language_specific_tasks
                base_specification['target_language'] = target_language.value
                base_specification['source_language'] = source_language.value
                base_specification['preferred_frameworks'] = preferred_frameworks or []
                
                # Get language configuration
                language_config = self.language_support.get_language_config(target_language)
                base_specification['language_config'] = {
                    'syntax_style': language_config.syntax_style,
                    'package_manager': language_config.package_manager,
                    'test_framework': language_config.test_framework,
                    'conventions': language_config.conventions,
                    'frameworks': [f.value for f in language_config.frameworks]
                }
            
            return {
                'success': True,
                'specification': base_specification,
                'target_language': target_language.value,
                'source_language': source_language.value
            }
            
        except Exception as e:
            logger.error(f"Failed to generate language-specific specification: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _parse_tasks_from_markdown(self, markdown_content: str) -> List[Dict[str, Any]]:
        """Parse tasks from markdown content (simplified implementation)"""
        tasks = []
        lines = markdown_content.split('\n')
        current_task = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('## Task') or line.startswith('### Task'):
                if current_task:
                    tasks.append(current_task)
                
                # Extract task title
                title = line.split(':', 1)[-1].strip() if ':' in line else line
                current_task = {
                    'id': f"task_{len(tasks) + 1}",
                    'title': title,
                    'description': '',
                    'difficulty': 'intermediate',
                    'patterns_practiced': []
                }
            elif current_task and line.startswith('**Objective:**'):
                current_task['description'] = line.replace('**Objective:**', '').strip()
            elif current_task and 'pattern' in line.lower():
                # Extract patterns mentioned in the line
                for pattern in ArchitecturalPattern:
                    if pattern.value.lower() in line.lower():
                        if pattern.value not in current_task['patterns_practiced']:
                            current_task['patterns_practiced'].append(pattern.value)
        
        if current_task:
            tasks.append(current_task)
        
        return tasks
    
    async def _generate_translation_examples(self, 
                                           code_snippets: List[CodeSnippet],
                                           source_language: ProgrammingLanguage,
                                           target_language: ProgrammingLanguage) -> List[Dict[str, Any]]:
        """Generate cross-language translation examples"""
        translation_examples = []
        
        for snippet in code_snippets[:2]:  # Limit to 2 examples
            try:
                # Detect patterns in the snippet
                element = self.pattern_extractor._create_structural_element(snippet)
                patterns = element.patterns if element else []
                
                # Translate the code
                translation_result = await self.cross_language_translator.translate_concepts(
                    snippet.content,
                    source_language,
                    target_language,
                    patterns
                )
                
                if translation_result.get('success'):
                    translation_examples.append({
                        'original_file': snippet.file_path,
                        'original_code': snippet.content,
                        'translated_code': translation_result.get('translated_code', ''),
                        'patterns': [p.value for p in patterns],
                        'translation_notes': translation_result.get('translation_notes', [])
                    })
                    
            except Exception as e:
                logger.warning(f"Failed to generate translation example: {e}")
                continue
        
        return translation_examples
    async def generate_enhanced_learning_spec(
        self,
        repository_url: str,
        architecture_topic: str,
        target_language: ProgrammingLanguage,
        preferred_frameworks: Optional[List[str]] = None,
        repository_analysis: Optional[Any] = None,
        repository_suggestion: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate enhanced learning specification using repository analysis and discovery context.
        
        This method leverages the repository analysis from the discovery system to create
        more targeted and contextual learning specifications.
        
        Args:
            repository_url: GitHub repository URL
            architecture_topic: Learning concept/topic
            target_language: Target programming language for implementation
            preferred_frameworks: Preferred frameworks for implementation
            repository_analysis: Repository analysis from discovery system
            repository_suggestion: Repository suggestion metadata
            
        Returns:
            Enhanced learning specification with discovery context
        """
        try:
            logger.info(f"Generating enhanced learning spec for {repository_url}")
            
            # If we have repository analysis, use it to enhance the specification
            if repository_analysis:
                return await self._generate_spec_from_analysis(
                    repository_url,
                    architecture_topic,
                    target_language,
                    preferred_frameworks,
                    repository_analysis,
                    repository_suggestion
                )
            else:
                # Fall back to standard generation
                return await self.generate_learning_spec_with_language(
                    repository_url,
                    architecture_topic,
                    target_language,
                    preferred_frameworks
                )
                
        except Exception as e:
            logger.error(f"Enhanced spec generation failed: {e}")
            return None
    
    async def _generate_spec_from_analysis(
        self,
        repository_url: str,
        architecture_topic: str,
        target_language: ProgrammingLanguage,
        preferred_frameworks: Optional[List[str]],
        repository_analysis: Any,
        repository_suggestion: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate specification using repository analysis data."""
        
        # Extract patterns from analysis
        architectural_patterns = []
        if hasattr(repository_analysis, 'architectural_patterns'):
            for pattern in repository_analysis.architectural_patterns:
                architectural_patterns.append(ArchitecturalPattern(pattern.pattern_name))
        
        # Create enhanced specification prompt
        enhanced_prompt = SpecificationPrompt(
            repository_info={
                'name': repository_suggestion.get('repository_name', 'Unknown') if repository_suggestion else 'Unknown',
                'description': repository_suggestion.get('description', '') if repository_suggestion else '',
                'language': repository_suggestion.get('language', 'Unknown') if repository_suggestion else 'Unknown',
                'stars': repository_suggestion.get('stars', 0) if repository_suggestion else 0,
                'complexity_score': repository_analysis.complexity_analysis.overall_complexity if hasattr(repository_analysis, 'complexity_analysis') else 0.5,
                'educational_value': repository_analysis.educational_assessment.overall_educational_score if hasattr(repository_analysis, 'educational_assessment') else 0.5
            },
            structural_elements=[],  # Would be populated from analysis
            pattern_analysis=[
                {
                    'pattern': pattern.pattern_name,
                    'confidence': pattern.confidence,
                    'description': pattern.description,
                    'complexity_level': pattern.complexity_level,
                    'educational_value': pattern.educational_value
                }
                for pattern in repository_analysis.architectural_patterns
            ] if hasattr(repository_analysis, 'architectural_patterns') else [],
            target_audience=repository_analysis.target_audience if hasattr(repository_analysis, 'target_audience') else "intermediate developers",
            learning_objectives=repository_analysis.key_learning_points if hasattr(repository_analysis, 'key_learning_points') else []
        )
        
        # Generate specification using LLM
        async with self.llm_provider as provider:
            llm_response = await provider.generate_specification(enhanced_prompt)
            
            if not llm_response.success:
                logger.error(f"LLM specification generation failed: {llm_response.error_message}")
                return self._create_fallback_spec(repository_url, architecture_topic, target_language)
            
            specification_content = llm_response.content
        
        # Generate enhanced tasks using analysis context
        tasks = await self._generate_enhanced_tasks(
            specification_content,
            repository_analysis,
            target_language,
            preferred_frameworks
        )
        
        # Create enhanced learning path
        learning_path = LearningPath(
            title=f"Learn {architecture_topic} from {repository_suggestion.get('repository_name', 'Repository') if repository_suggestion else 'Repository'}",
            description=f"Master {architecture_topic} concepts through hands-on implementation",
            difficulty_level=repository_analysis.educational_assessment.learning_difficulty if hasattr(repository_analysis, 'educational_assessment') else 3,
            estimated_duration=repository_analysis.estimated_learning_time if hasattr(repository_analysis, 'estimated_learning_time') else "2-4 weeks",
            prerequisites=repository_analysis.educational_assessment.recommended_prerequisites if hasattr(repository_analysis, 'educational_assessment') else [],
            learning_outcomes=repository_analysis.educational_assessment.learning_outcomes if hasattr(repository_analysis, 'educational_assessment') else [],
            tasks=tasks
        )
        
        return {
            'specification': specification_content,
            'learning_path': learning_path.to_dict(),
            'tasks': [task.to_dict() for task in tasks],
            'patterns': [pattern.pattern_name for pattern in repository_analysis.architectural_patterns] if hasattr(repository_analysis, 'architectural_patterns') else [],
            'target_language': target_language.value,
            'preferred_frameworks': preferred_frameworks or [],
            'repository_metadata': {
                'url': repository_url,
                'analysis_timestamp': repository_analysis.analysis_timestamp if hasattr(repository_analysis, 'analysis_timestamp') else None,
                'complexity_score': repository_analysis.complexity_analysis.overall_complexity if hasattr(repository_analysis, 'complexity_analysis') else 0.5,
                'educational_score': repository_analysis.educational_assessment.overall_educational_score if hasattr(repository_analysis, 'educational_assessment') else 0.5,
                'learning_potential': repository_analysis.learning_potential_score if hasattr(repository_analysis, 'learning_potential_score') else 0.5
            }
        }
    
    async def _generate_enhanced_tasks(
        self,
        specification_content: str,
        repository_analysis: Any,
        target_language: ProgrammingLanguage,
        preferred_frameworks: Optional[List[str]]
    ) -> List[Any]:
        """Generate enhanced tasks using repository analysis context."""
        
        # Get language-specific task generator
        language_config = LanguageSupport.get_language_config(target_language)
        task_generator = LanguageSpecificTaskGenerator(language_config, self.llm_provider)
        
        # Determine difficulty level from analysis
        difficulty_level = "intermediate"
        if hasattr(repository_analysis, 'educational_assessment'):
            if repository_analysis.educational_assessment.learning_difficulty <= 2:
                difficulty_level = "beginner"
            elif repository_analysis.educational_assessment.learning_difficulty >= 4:
                difficulty_level = "advanced"
        
        # Generate tasks with enhanced context
        async with self.llm_provider as provider:
            llm_response = await provider.generate_learning_tasks(
                specification_content,
                difficulty_level
            )
            
            if llm_response.success:
                # Parse tasks from LLM response
                tasks = self._parse_tasks_from_content(llm_response.content)
                
                # Enhance tasks with language-specific details
                enhanced_tasks = []
                for task_data in tasks:
                    enhanced_task = await task_generator.generate_language_specific_task(
                        task_data['title'],
                        task_data['description'],
                        task_data.get('patterns_practiced', []),
                        preferred_frameworks
                    )
                    enhanced_tasks.append(enhanced_task)
                
                return enhanced_tasks
            else:
                # Fallback to basic task generation
                return await self.task_generator.generate_tasks(
                    specification_content,
                    target_language,
                    difficulty_level
                )
    
    def _create_fallback_spec(
        self,
        repository_url: str,
        architecture_topic: str,
        target_language: ProgrammingLanguage
    ) -> Dict[str, Any]:
        """Create fallback specification when enhanced generation fails."""
        
        return {
            'specification': f"""# Learning Specification: {architecture_topic}

## Overview
This learning specification focuses on understanding {architecture_topic} concepts through practical implementation.

## Learning Objectives
- Understand core {architecture_topic} principles
- Implement key patterns and components
- Apply concepts to real-world scenarios

## Implementation Approach
Implement solutions using {target_language.value} following best practices and architectural patterns.

## Progressive Learning Path
1. Analyze existing patterns
2. Implement simplified versions
3. Build complete solutions
4. Extend with additional features
""",
            'learning_path': {
                'title': f"Learn {architecture_topic}",
                'description': f"Master {architecture_topic} through hands-on practice",
                'difficulty_level': 3,
                'estimated_duration': "2-4 weeks",
                'prerequisites': ["basic programming", "software architecture fundamentals"],
                'learning_outcomes': [f"understand {architecture_topic}", "implement architectural patterns"],
                'tasks': []
            },
            'tasks': [],
            'patterns': [],
            'target_language': target_language.value,
            'preferred_frameworks': [],
            'repository_metadata': {
                'url': repository_url,
                'analysis_timestamp': None,
                'complexity_score': 0.5,
                'educational_score': 0.5,
                'learning_potential': 0.5
            }
        }