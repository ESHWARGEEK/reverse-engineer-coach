"""
Shared types and enums for The Reverse Engineer Coach.

This module contains common data structures and enums used across
the specification generator and task generator modules.
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass, field


class ProgrammingLanguage(Enum):
    """Supported programming languages for implementation"""
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    CPP = "cpp"
    CSHARP = "csharp"


class LanguageFramework(Enum):
    """Popular frameworks for each language"""
    # Python frameworks
    FASTAPI = "fastapi"
    DJANGO = "django"
    FLASK = "flask"
    
    # TypeScript/JavaScript frameworks
    REACT = "react"
    NEXTJS = "nextjs"
    EXPRESS = "express"
    NESTJS = "nestjs"
    
    # Go frameworks
    GIN = "gin"
    ECHO = "echo"
    FIBER = "fiber"
    
    # Java frameworks
    SPRING = "spring"
    QUARKUS = "quarkus"
    
    # Rust frameworks
    ACTIX = "actix"
    WARP = "warp"
    
    # C# frameworks
    ASPNET = "aspnet"


@dataclass
class LanguageSpecification:
    """Language-specific implementation details"""
    language: ProgrammingLanguage
    frameworks: List[LanguageFramework] = field(default_factory=list)
    syntax_style: str = "standard"  # 'standard', 'functional', 'object_oriented'
    package_manager: str = ""  # npm, pip, cargo, etc.
    test_framework: str = ""  # jest, pytest, etc.
    conventions: Dict[str, str] = field(default_factory=dict)


@dataclass
class CrossLanguageMapping:
    """Mapping between concepts across different languages"""
    source_language: ProgrammingLanguage
    target_language: ProgrammingLanguage
    concept_mappings: Dict[str, str] = field(default_factory=dict)
    pattern_adaptations: Dict[str, str] = field(default_factory=dict)
    syntax_translations: Dict[str, str] = field(default_factory=dict)


class ArchitecturalPattern(Enum):
    """Common architectural patterns that can be identified in code"""
    HANDLER = "Handler Pattern"
    SERVICE_LAYER = "Service Layer Pattern"
    REPOSITORY = "Repository Pattern"
    FACTORY = "Factory Pattern"
    BUILDER = "Builder Pattern"
    OBSERVER = "Observer Pattern"
    STRATEGY = "Strategy Pattern"
    COMMAND = "Command Pattern"
    ADAPTER = "Adapter Pattern"
    FACADE = "Facade Pattern"
    SINGLETON = "Singleton Pattern"
    DEPENDENCY_INJECTION = "Dependency Injection"
    MVC = "Model-View-Controller"
    MICROSERVICE = "Microservice Pattern"
    EVENT_SOURCING = "Event Sourcing"
    CQRS = "Command Query Responsibility Segregation"
    CIRCUIT_BREAKER = "Circuit Breaker Pattern"
    LOAD_BALANCER = "Load Balancer Pattern"
    CACHE_ASIDE = "Cache-Aside Pattern"
    PUBLISH_SUBSCRIBE = "Publish-Subscribe Pattern"


@dataclass
class PatternAnalysis:
    """Analysis of architectural patterns found in the codebase"""
    pattern: ArchitecturalPattern
    confidence: float  # 0.0 to 1.0
    evidence: List[str]  # Code elements that support this pattern
    related_files: List[str]
    learning_value: float  # Educational value score
    implementation_complexity: str  # 'beginner', 'intermediate', 'advanced'


@dataclass
class StructuralElement:
    """Represents a structural element extracted from code"""
    name: str
    element_type: str  # 'interface', 'class', 'struct', 'function', 'type'
    file_path: str
    start_line: int
    end_line: int
    language: str
    content: str
    dependencies: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    properties: List[str] = field(default_factory=list)
    patterns: List[ArchitecturalPattern] = field(default_factory=list)
    complexity_score: float = 0.0
    architectural_significance: float = 0.0
    language_specific_features: Dict[str, str] = field(default_factory=dict)


@dataclass
class SimplifiedCode:
    """Represents simplified code with production complexity removed"""
    original_element: StructuralElement
    simplified_content: str
    removed_complexity: List[str] = field(default_factory=list)
    preserved_patterns: List[ArchitecturalPattern] = field(default_factory=list)
    learning_focus: List[str] = field(default_factory=list)
    target_language: Optional[ProgrammingLanguage] = None
    language_adaptations: Dict[str, str] = field(default_factory=dict)