"""
Multi-Language Support for The Reverse Engineer Coach.

This module implements language selection, language-specific task generation,
and cross-language concept translation capabilities.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from app.types import (
    ProgrammingLanguage, LanguageFramework, LanguageSpecification,
    CrossLanguageMapping, ArchitecturalPattern, StructuralElement
)
from app.llm_provider import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class LanguageSupport:
    """Main class for handling multi-language support"""
    
    # Language-specific configurations
    LANGUAGE_CONFIGS = {
        ProgrammingLanguage.PYTHON: LanguageSpecification(
            language=ProgrammingLanguage.PYTHON,
            frameworks=[LanguageFramework.FASTAPI, LanguageFramework.DJANGO, LanguageFramework.FLASK],
            syntax_style="object_oriented",
            package_manager="pip",
            test_framework="pytest",
            conventions={
                "naming": "snake_case",
                "class_naming": "PascalCase",
                "constant_naming": "UPPER_SNAKE_CASE",
                "file_extension": ".py",
                "interface_pattern": "ABC (Abstract Base Class)",
                "dependency_injection": "constructor injection"
            }
        ),
        ProgrammingLanguage.TYPESCRIPT: LanguageSpecification(
            language=ProgrammingLanguage.TYPESCRIPT,
            frameworks=[LanguageFramework.REACT, LanguageFramework.NEXTJS, LanguageFramework.NESTJS],
            syntax_style="object_oriented",
            package_manager="npm",
            test_framework="jest",
            conventions={
                "naming": "camelCase",
                "class_naming": "PascalCase",
                "constant_naming": "UPPER_SNAKE_CASE",
                "file_extension": ".ts",
                "interface_pattern": "interface keyword",
                "dependency_injection": "constructor injection"
            }
        ),
        ProgrammingLanguage.GO: LanguageSpecification(
            language=ProgrammingLanguage.GO,
            frameworks=[LanguageFramework.GIN, LanguageFramework.ECHO, LanguageFramework.FIBER],
            syntax_style="functional",
            package_manager="go mod",
            test_framework="testing",
            conventions={
                "naming": "camelCase",
                "class_naming": "PascalCase",
                "constant_naming": "PascalCase",
                "file_extension": ".go",
                "interface_pattern": "interface type",
                "dependency_injection": "function parameters"
            }
        ),
        ProgrammingLanguage.RUST: LanguageSpecification(
            language=ProgrammingLanguage.RUST,
            frameworks=[LanguageFramework.ACTIX, LanguageFramework.WARP],
            syntax_style="functional",
            package_manager="cargo",
            test_framework="cargo test",
            conventions={
                "naming": "snake_case",
                "class_naming": "PascalCase",
                "constant_naming": "UPPER_SNAKE_CASE",
                "file_extension": ".rs",
                "interface_pattern": "trait",
                "dependency_injection": "trait objects"
            }
        ),
        ProgrammingLanguage.JAVA: LanguageSpecification(
            language=ProgrammingLanguage.JAVA,
            frameworks=[LanguageFramework.SPRING, LanguageFramework.QUARKUS],
            syntax_style="object_oriented",
            package_manager="maven",
            test_framework="junit",
            conventions={
                "naming": "camelCase",
                "class_naming": "PascalCase",
                "constant_naming": "UPPER_SNAKE_CASE",
                "file_extension": ".java",
                "interface_pattern": "interface keyword",
                "dependency_injection": "annotation-based"
            }
        )
    }
    
    # Cross-language concept mappings
    CROSS_LANGUAGE_MAPPINGS = {
        (ProgrammingLanguage.PYTHON, ProgrammingLanguage.TYPESCRIPT): CrossLanguageMapping(
            source_language=ProgrammingLanguage.PYTHON,
            target_language=ProgrammingLanguage.TYPESCRIPT,
            concept_mappings={
                "class": "class",
                "interface": "interface",
                "function": "function",
                "method": "method",
                "property": "property",
                "constructor": "constructor",
                "inheritance": "extends",
                "composition": "composition",
                "module": "module/namespace"
            },
            pattern_adaptations={
                "Repository Pattern": "Use TypeScript interfaces and dependency injection",
                "Factory Pattern": "Use TypeScript generics and factory functions",
                "Observer Pattern": "Use EventEmitter or custom event system",
                "Strategy Pattern": "Use TypeScript interfaces and polymorphism"
            },
            syntax_translations={
                "def function_name(self, param):": "functionName(param: Type): ReturnType {",
                "class ClassName:": "class ClassName {",
                "from module import Class": "import { Class } from 'module';",
                "__init__(self, param)": "constructor(param: Type)",
                "self.property = value": "this.property = value;"
            }
        ),
        (ProgrammingLanguage.GO, ProgrammingLanguage.PYTHON): CrossLanguageMapping(
            source_language=ProgrammingLanguage.GO,
            target_language=ProgrammingLanguage.PYTHON,
            concept_mappings={
                "struct": "class",
                "interface": "ABC (Abstract Base Class)",
                "func": "def",
                "method": "method",
                "field": "property",
                "package": "module",
                "embedding": "inheritance/composition"
            },
            pattern_adaptations={
                "Repository Pattern": "Use ABC and concrete implementations",
                "Factory Pattern": "Use class methods or factory functions",
                "Observer Pattern": "Use callback functions or observer pattern",
                "Strategy Pattern": "Use ABC and concrete strategy classes"
            },
            syntax_translations={
                "type Interface interface {": "class Interface(ABC):",
                "func (r *Receiver) Method()": "def method(self):",
                "type Struct struct {": "class Struct:",
                "package main": "# Python module",
                "import \"package\"": "import package"
            }
        )
    }
    
    @classmethod
    def get_language_config(cls, language: ProgrammingLanguage) -> LanguageSpecification:
        """Get language-specific configuration"""
        return cls.LANGUAGE_CONFIGS.get(language, cls.LANGUAGE_CONFIGS[ProgrammingLanguage.PYTHON])
    
    @classmethod
    def get_supported_languages(cls) -> List[ProgrammingLanguage]:
        """Get list of supported programming languages"""
        return list(cls.LANGUAGE_CONFIGS.keys())
    
    @classmethod
    def get_cross_language_mapping(cls, source: ProgrammingLanguage, 
                                 target: ProgrammingLanguage) -> Optional[CrossLanguageMapping]:
        """Get cross-language mapping between two languages"""
        return cls.CROSS_LANGUAGE_MAPPINGS.get((source, target))
    
    @classmethod
    def detect_source_language(cls, code_content: str) -> ProgrammingLanguage:
        """Detect programming language from code content"""
        # Simple heuristic-based detection
        if "def " in code_content and "import " in code_content:
            return ProgrammingLanguage.PYTHON
        elif "interface " in code_content and "export " in code_content:
            return ProgrammingLanguage.TYPESCRIPT
        elif "func " in code_content and "package " in code_content:
            return ProgrammingLanguage.GO
        elif "fn " in code_content and "use " in code_content:
            return ProgrammingLanguage.RUST
        elif "public class " in code_content and "import java" in code_content:
            return ProgrammingLanguage.JAVA
        else:
            return ProgrammingLanguage.PYTHON  # Default fallback


class LanguageSpecificTaskGenerator:
    """Generates language-specific learning tasks"""
    
    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm_provider = llm_provider
        self.language_support = LanguageSupport()
    
    async def generate_language_specific_tasks(self, 
                                             base_tasks: List[Dict[str, Any]],
                                             target_language: ProgrammingLanguage,
                                             source_language: Optional[ProgrammingLanguage] = None) -> List[Dict[str, Any]]:
        """
        Generate language-specific versions of learning tasks.
        
        Args:
            base_tasks: Original tasks from pattern analysis
            target_language: Target implementation language
            source_language: Source language of the analyzed code
            
        Returns:
            List of language-adapted tasks
        """
        logger.info(f"Generating {target_language.value} specific tasks")
        
        language_config = self.language_support.get_language_config(target_language)
        adapted_tasks = []
        
        for task in base_tasks:
            adapted_task = await self._adapt_task_to_language(
                task, language_config, source_language
            )
            adapted_tasks.append(adapted_task)
        
        return adapted_tasks
    
    async def _adapt_task_to_language(self, 
                                    task: Dict[str, Any],
                                    language_config: LanguageSpecification,
                                    source_language: Optional[ProgrammingLanguage]) -> Dict[str, Any]:
        """Adapt a single task to target language"""
        try:
            # Create language-specific prompt
            adaptation_prompt = self._create_language_adaptation_prompt(
                task, language_config, source_language
            )
            
            # Generate adapted task using LLM
            async with self.llm_provider as provider:
                response = await provider.generate_learning_tasks(
                    adaptation_prompt, task.get('difficulty', 'intermediate')
                )
            
            if response.success:
                # Parse and enhance the adapted task
                adapted_task = task.copy()
                adapted_task.update({
                    'language_specific_description': response.content,
                    'target_language': language_config.language.value,
                    'language_conventions': language_config.conventions,
                    'recommended_frameworks': [f.value for f in language_config.frameworks],
                    'test_framework': language_config.test_framework,
                    'package_manager': language_config.package_manager
                })
                
                return adapted_task
            else:
                logger.warning(f"Failed to adapt task {task.get('id', 'unknown')}: {response.error_message}")
                return task
                
        except Exception as e:
            logger.error(f"Error adapting task to {language_config.language.value}: {e}")
            return task
    
    def _create_language_adaptation_prompt(self, 
                                         task: Dict[str, Any],
                                         language_config: LanguageSpecification,
                                         source_language: Optional[ProgrammingLanguage]) -> str:
        """Create prompt for language-specific task adaptation"""
        
        base_prompt = f"""
Adapt the following learning task for {language_config.language.value} implementation:

**Original Task:**
- Title: {task.get('title', 'Unknown')}
- Description: {task.get('description', 'No description')}
- Patterns: {', '.join(task.get('patterns_practiced', []))}
- Difficulty: {task.get('difficulty', 'intermediate')}

**Target Language Configuration:**
- Language: {language_config.language.value}
- Syntax Style: {language_config.syntax_style}
- Naming Conventions: {language_config.conventions.get('naming', 'standard')}
- Test Framework: {language_config.test_framework}
- Package Manager: {language_config.package_manager}
- Recommended Frameworks: {', '.join([f.value for f in language_config.frameworks])}

**Requirements:**
1. Adapt the task description to use {language_config.language.value} syntax and conventions
2. Include language-specific implementation guidance
3. Reference appropriate frameworks and libraries
4. Provide {language_config.language.value}-specific code examples
5. Adapt success criteria to language-specific best practices
6. Include testing approach using {language_config.test_framework}

**Output Format:**
Provide a detailed task description that includes:
- Language-specific implementation steps
- Code examples in {language_config.language.value}
- Framework recommendations
- Testing strategy
- Success criteria adapted for {language_config.language.value}
"""
        
        # Add cross-language translation context if source language is different
        if source_language and source_language != language_config.language:
            mapping = self.language_support.get_cross_language_mapping(
                source_language, language_config.language
            )
            if mapping:
                base_prompt += f"""

**Cross-Language Translation Context:**
Source Language: {source_language.value}
Target Language: {language_config.language.value}

Key Concept Mappings:
{chr(10).join([f"- {src} → {tgt}" for src, tgt in mapping.concept_mappings.items()])}

Pattern Adaptations:
{chr(10).join([f"- {pattern}: {adaptation}" for pattern, adaptation in mapping.pattern_adaptations.items()])}
"""
        
        return base_prompt


class CrossLanguageTranslator:
    """Handles cross-language concept translation"""
    
    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm_provider = llm_provider
        self.language_support = LanguageSupport()
    
    async def translate_concepts(self, 
                               source_code: str,
                               source_language: ProgrammingLanguage,
                               target_language: ProgrammingLanguage,
                               patterns: List[ArchitecturalPattern]) -> Dict[str, Any]:
        """
        Translate architectural concepts from source to target language.
        
        Args:
            source_code: Original code in source language
            source_language: Source programming language
            target_language: Target programming language
            patterns: Architectural patterns to preserve
            
        Returns:
            Translation result with adapted code and explanations
        """
        logger.info(f"Translating concepts from {source_language.value} to {target_language.value}")
        
        # Get language configurations
        source_config = self.language_support.get_language_config(source_language)
        target_config = self.language_support.get_language_config(target_language)
        
        # Get cross-language mapping
        mapping = self.language_support.get_cross_language_mapping(source_language, target_language)
        
        # Create translation prompt
        translation_prompt = self._create_translation_prompt(
            source_code, source_config, target_config, mapping, patterns
        )
        
        try:
            # Generate translation using LLM
            async with self.llm_provider as provider:
                response = await provider.simplify_code_explanation(
                    translation_prompt, [p.value for p in patterns], target_language.value
                )
            
            if response.success:
                return {
                    'success': True,
                    'translated_code': response.content,
                    'source_language': source_language.value,
                    'target_language': target_language.value,
                    'preserved_patterns': [p.value for p in patterns],
                    'translation_notes': self._generate_translation_notes(mapping, patterns),
                    'tokens_used': response.tokens_used
                }
            else:
                return {
                    'success': False,
                    'error': response.error_message,
                    'source_language': source_language.value,
                    'target_language': target_language.value
                }
                
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'source_language': source_language.value,
                'target_language': target_language.value
            }
    
    def _create_translation_prompt(self, 
                                 source_code: str,
                                 source_config: LanguageSpecification,
                                 target_config: LanguageSpecification,
                                 mapping: Optional[CrossLanguageMapping],
                                 patterns: List[ArchitecturalPattern]) -> str:
        """Create prompt for cross-language translation"""
        
        prompt = f"""
Translate the following {source_config.language.value} code to {target_config.language.value} while preserving architectural patterns and concepts.

**Source Code ({source_config.language.value}):**
```{source_config.language.value}
{source_code}
```

**Architectural Patterns to Preserve:**
{', '.join([p.value for p in patterns])}

**Source Language Conventions:**
- Naming: {source_config.conventions.get('naming', 'standard')}
- Class Naming: {source_config.conventions.get('class_naming', 'standard')}
- Interface Pattern: {source_config.conventions.get('interface_pattern', 'standard')}

**Target Language Conventions:**
- Naming: {target_config.conventions.get('naming', 'standard')}
- Class Naming: {target_config.conventions.get('class_naming', 'standard')}
- Interface Pattern: {target_config.conventions.get('interface_pattern', 'standard')}
- Syntax Style: {target_config.syntax_style}
"""
        
        if mapping:
            prompt += f"""

**Translation Guidelines:**
Concept Mappings:
{chr(10).join([f"- {src} → {tgt}" for src, tgt in mapping.concept_mappings.items()])}

Pattern Adaptations:
{chr(10).join([f"- {pattern}: {adaptation}" for pattern, adaptation in mapping.pattern_adaptations.items()])}

Syntax Translations:
{chr(10).join([f"- {src} → {tgt}" for src, tgt in mapping.syntax_translations.items()])}
"""
        
        prompt += f"""

**Requirements:**
1. Preserve all architectural patterns and their intent
2. Follow {target_config.language.value} naming conventions and best practices
3. Use appropriate {target_config.language.value} language features
4. Maintain the same level of abstraction
5. Include comments explaining architectural decisions
6. Ensure the translated code is idiomatic {target_config.language.value}

**Output:**
Provide the translated code with explanatory comments about:
- How each pattern is implemented in {target_config.language.value}
- Key differences from the {source_config.language.value} version
- {target_config.language.value}-specific best practices applied
"""
        
        return prompt
    
    def _generate_translation_notes(self, 
                                  mapping: Optional[CrossLanguageMapping],
                                  patterns: List[ArchitecturalPattern]) -> List[str]:
        """Generate notes about the translation process"""
        notes = []
        
        if mapping:
            notes.append(f"Translated from {mapping.source_language.value} to {mapping.target_language.value}")
            
            for pattern in patterns:
                if pattern.value in mapping.pattern_adaptations:
                    notes.append(f"{pattern.value}: {mapping.pattern_adaptations[pattern.value]}")
        
        return notes


class LanguageSpecificHintGenerator:
    """Generates language-specific hints and guidance"""
    
    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm_provider = llm_provider
        self.language_support = LanguageSupport()
    
    async def generate_language_hints(self, 
                                    task_context: str,
                                    target_language: ProgrammingLanguage,
                                    difficulty_level: str = "intermediate") -> List[str]:
        """Generate language-specific hints for a task"""
        
        language_config = self.language_support.get_language_config(target_language)
        
        hint_prompt = f"""
Generate helpful, language-specific hints for implementing the following task in {target_language.value}:

**Task Context:**
{task_context}

**Language:** {target_language.value}
**Difficulty Level:** {difficulty_level}
**Language Conventions:** {language_config.conventions}
**Recommended Frameworks:** {[f.value for f in language_config.frameworks]}

**Requirements:**
1. Provide 3-5 specific, actionable hints
2. Focus on {target_language.value} best practices
3. Include framework-specific guidance where appropriate
4. Mention language-specific features that can help
5. Suggest testing approaches using {language_config.test_framework}

**Format:**
Return hints as a bulleted list, each hint should be concise and actionable.
"""
        
        try:
            async with self.llm_provider as provider:
                response = await provider.simplify_code_explanation(
                    hint_prompt, [], target_language.value
                )
            
            if response.success:
                # Parse hints from response
                hints = []
                for line in response.content.split('\n'):
                    line = line.strip()
                    if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                        hints.append(line[1:].strip())
                
                return hints[:5]  # Limit to 5 hints
            else:
                return [f"Focus on {target_language.value} best practices and conventions"]
                
        except Exception as e:
            logger.error(f"Failed to generate language hints: {e}")
            return [f"Implement using {target_language.value} idioms and patterns"]