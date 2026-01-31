"""
Curriculum Generation Agent - AI service for generating personalized learning curricula

Features:
- Progressive learning path generation
- Personalized task creation based on user preferences
- Difficulty progression analysis
- Supporting materials generation
- Adaptive curriculum based on user progress
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import uuid
from dataclasses import dataclass, asdict
from enum import Enum

from ..llm_provider import LLMProvider
from .repository_analysis_agent import RepositoryAnalysis, LearningOpportunity
from .repository_discovery_agent import DiscoveredRepository
from ..cache import cache_manager

logger = logging.getLogger(__name__)

class TaskType(Enum):
    EXPLORATION = "exploration"
    IMPLEMENTATION = "implementation"
    ANALYSIS = "analysis"
    DEBUGGING = "debugging"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"
    RESEARCH = "research"

class DifficultyProgression(Enum):
    GENTLE = "gentle"
    MODERATE = "moderate"
    STEEP = "steep"
    ADAPTIVE = "adaptive"

@dataclass
class LearningTask:
    """Individual learning task"""
    id: str
    title: str
    description: str
    task_type: TaskType
    difficulty_level: str  # beginner, intermediate, advanced
    estimated_time: str
    prerequisites: List[str]
    learning_objectives: List[str]
    instructions: List[str]
    code_files_to_study: List[str]
    code_files_to_modify: List[str]
    expected_outcomes: List[str]
    hints: List[str]
    resources: List[str]
    validation_criteria: List[str]
    next_tasks: List[str]  # Task IDs that should follow this one
    concepts: List[str]
    skills_developed: List[str]

@dataclass
class LearningModule:
    """Collection of related learning tasks"""
    id: str
    title: str
    description: str
    learning_objectives: List[str]
    estimated_duration: str
    difficulty_level: str
    prerequisites: List[str]
    tasks: List[LearningTask]
    concepts_covered: List[str]
    skills_developed: List[str]
    assessment_criteria: List[str]
    completion_requirements: List[str]

@dataclass
class SupportingMaterial:
    """Supporting learning material"""
    id: str
    title: str
    type: str  # article, video, documentation, tutorial, example
    url: Optional[str]
    content: Optional[str]
    description: str
    difficulty_level: str
    estimated_time: str
    related_concepts: List[str]
    related_tasks: List[str]

@dataclass
class ProgressionPath:
    """Learning progression path"""
    id: str
    name: str
    description: str
    modules: List[str]  # Module IDs in order
    branching_points: Dict[str, List[str]]  # Module ID -> alternative paths
    difficulty_curve: List[float]  # Difficulty progression (0-100)
    estimated_total_time: str
    completion_criteria: List[str]

@dataclass
class PersonalizedCurriculum:
    """Complete personalized learning curriculum"""
    id: str
    user_id: str
    repository_id: str
    repository_name: str
    created_at: datetime
    updated_at: datetime
    
    # User context
    user_skill_level: str
    user_goals: List[str]
    time_commitment: str
    learning_style: str
    preferred_technologies: List[str]
    
    # Curriculum structure
    title: str
    description: str
    learning_objectives: List[str]
    modules: List[LearningModule]
    progression_paths: List[ProgressionPath]
    supporting_materials: List[SupportingMaterial]
    
    # Metadata
    estimated_total_duration: str
    difficulty_progression: DifficultyProgression
    completion_percentage: float
    current_module: Optional[str]
    current_task: Optional[str]
    
    # Personalization
    personalization_notes: str
    adaptation_history: List[Dict[str, Any]]
    success_metrics: Dict[str, float]

class CurriculumGenerationAgent:
    """AI service for generating personalized learning curricula"""
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider
        self.cache_ttl = 3600  # 1 hour cache
        
        # Task templates for different types
        self.task_templates = {
            TaskType.EXPLORATION: {
                "title_template": "Explore {component}",
                "description_template": "Study and understand the {component} implementation",
                "instructions_template": [
                    "Read through the {files} files",
                    "Identify the main components and their relationships",
                    "Document your understanding of the architecture",
                    "Note any patterns or interesting implementations"
                ]
            },
            TaskType.IMPLEMENTATION: {
                "title_template": "Implement {feature}",
                "description_template": "Build a {feature} following the patterns in the codebase",
                "instructions_template": [
                    "Analyze similar implementations in the codebase",
                    "Design your {feature} following the established patterns",
                    "Implement the {feature} with proper error handling",
                    "Test your implementation thoroughly"
                ]
            },
            TaskType.ANALYSIS: {
                "title_template": "Analyze {aspect}",
                "description_template": "Deep dive into {aspect} and understand its implementation",
                "instructions_template": [
                    "Study the {aspect} implementation in detail",
                    "Identify the design decisions and trade-offs",
                    "Compare with alternative approaches",
                    "Document your analysis and insights"
                ]
            }
        }
    
    async def generate_curriculum(
        self,
        repository: DiscoveredRepository,
        repository_analysis: RepositoryAnalysis,
        user_profile: Dict[str, Any],
        customization_options: Dict[str, Any] = None
    ) -> PersonalizedCurriculum:
        """
        Generate personalized learning curriculum
        
        Args:
            repository: Discovered repository information
            repository_analysis: Detailed repository analysis
            user_profile: User skills, goals, and preferences
            customization_options: Additional customization options
            
        Returns:
            Complete personalized curriculum
        """
        try:
            logger.info(f"Generating curriculum for repository {repository.name}")
            
            # Generate cache key
            cache_key = self._generate_cache_key(repository.id, user_profile)
            
            # Check cache first
            cached_curriculum = await self._get_cached_curriculum(cache_key)
            if cached_curriculum:
                logger.info("Returning cached curriculum")
                return cached_curriculum
            
            # Extract user context
            user_context = self._extract_user_context(user_profile)
            
            # Generate learning objectives
            learning_objectives = await self._generate_learning_objectives(
                repository, repository_analysis, user_context
            )
            
            # Generate learning modules
            modules = await self._generate_learning_modules(
                repository, repository_analysis, user_context, learning_objectives
            )
            
            # Generate progression paths
            progression_paths = await self._generate_progression_paths(
                modules, user_context
            )
            
            # Generate supporting materials
            supporting_materials = await self._generate_supporting_materials(
                repository, repository_analysis, modules, user_context
            )
            
            # Calculate curriculum metadata
            metadata = self._calculate_curriculum_metadata(modules, user_context)
            
            # Generate personalization notes
            personalization_notes = await self._generate_personalization_notes(
                repository, user_context, modules
            )
            
            # Create curriculum
            curriculum = PersonalizedCurriculum(
                id=str(uuid.uuid4()),
                user_id=user_profile.get('user_id', 'anonymous'),
                repository_id=repository.id,
                repository_name=repository.name,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                user_skill_level=user_context['skill_level'],
                user_goals=user_context['goals'],
                time_commitment=user_context['time_commitment'],
                learning_style=user_context['learning_style'],
                preferred_technologies=user_context['technologies'],
                title=f"Master {repository.name}",
                description=f"Comprehensive learning curriculum for {repository.name}",
                learning_objectives=learning_objectives,
                modules=modules,
                progression_paths=progression_paths,
                supporting_materials=supporting_materials,
                estimated_total_duration=metadata['total_duration'],
                difficulty_progression=metadata['difficulty_progression'],
                completion_percentage=0.0,
                current_module=modules[0].id if modules else None,
                current_task=modules[0].tasks[0].id if modules and modules[0].tasks else None,
                personalization_notes=personalization_notes,
                adaptation_history=[],
                success_metrics={}
            )
            
            # Cache the curriculum
            await self._cache_curriculum(cache_key, curriculum)
            
            logger.info(f"Curriculum generation complete: {len(modules)} modules, {sum(len(m.tasks) for m in modules)} tasks")
            return curriculum
            
        except Exception as e:
            logger.error(f"Curriculum generation failed: {e}")
            raise
    
    def _extract_user_context(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize user context"""
        return {
            'skill_level': user_profile.get('experience_level', 'intermediate'),
            'goals': user_profile.get('learning_goals', []),
            'time_commitment': user_profile.get('time_commitment', 'moderate'),
            'learning_style': user_profile.get('learning_style', 'hands_on'),
            'technologies': user_profile.get('technologies', []),
            'current_skills': user_profile.get('current_skills', []),
            'motivation': user_profile.get('motivation', '')
        }
    
    async def _generate_learning_objectives(
        self,
        repository: DiscoveredRepository,
        analysis: RepositoryAnalysis,
        user_context: Dict[str, Any]
    ) -> List[str]:
        """Generate high-level learning objectives"""
        
        try:
            prompt = f"""
            Generate 5-8 high-level learning objectives for studying this repository:
            
            Repository: {repository.name}
            Description: {repository.description}
            Language: {repository.language}
            Topics: {', '.join(repository.topics)}
            
            User Profile:
            - Skill Level: {user_context['skill_level']}
            - Goals: {', '.join(user_context['goals'])}
            - Technologies: {', '.join(user_context['technologies'])}
            
            Repository Analysis:
            - Architecture Patterns: {', '.join([p.value for p in analysis.architecture.primary_patterns])}
            - Complexity: {analysis.complexity.overall_complexity.value}
            - Key Components: {', '.join(analysis.architecture.key_components)}
            
            Generate specific, measurable learning objectives that:
            1. Match the user's skill level and goals
            2. Cover the key aspects of the repository
            3. Progress from basic understanding to advanced application
            4. Are achievable within the user's time commitment
            
            Return only the objectives, one per line, starting with action verbs.
            """
            
            response = await self.llm_provider.generate_completion(prompt)
            objectives = [obj.strip() for obj in response.split('\n') if obj.strip()]
            
            return objectives[:8]  # Limit to 8 objectives
            
        except Exception as e:
            logger.warning(f"Failed to generate learning objectives: {e}")
            # Fallback objectives
            return [
                f"Understand the architecture and structure of {repository.name}",
                f"Learn the key {repository.language} patterns used in the project",
                "Analyze the codebase organization and design decisions",
                "Implement similar features using the project's patterns",
                "Understand the testing and deployment strategies"
            ]
    
    async def _generate_learning_modules(
        self,
        repository: DiscoveredRepository,
        analysis: RepositoryAnalysis,
        user_context: Dict[str, Any],
        learning_objectives: List[str]
    ) -> List[LearningModule]:
        """Generate learning modules with tasks"""
        
        modules = []
        
        # Module 1: Project Overview and Setup
        overview_module = await self._create_overview_module(
            repository, analysis, user_context
        )
        modules.append(overview_module)
        
        # Module 2: Architecture Analysis
        architecture_module = await self._create_architecture_module(
            repository, analysis, user_context
        )
        modules.append(architecture_module)
        
        # Module 3: Core Implementation Study
        implementation_module = await self._create_implementation_module(
            repository, analysis, user_context
        )
        modules.append(implementation_module)
        
        # Module 4: Hands-on Practice
        practice_module = await self._create_practice_module(
            repository, analysis, user_context
        )
        modules.append(practice_module)
        
        # Module 5: Advanced Topics (if appropriate for skill level)
        if user_context['skill_level'] in ['intermediate', 'advanced', 'expert']:
            advanced_module = await self._create_advanced_module(
                repository, analysis, user_context
            )
            modules.append(advanced_module)
        
        return modules
    
    async def _create_overview_module(
        self,
        repository: DiscoveredRepository,
        analysis: RepositoryAnalysis,
        user_context: Dict[str, Any]
    ) -> LearningModule:
        """Create project overview module"""
        
        tasks = []
        
        # Task 1: Repository exploration
        exploration_task = LearningTask(
            id=str(uuid.uuid4()),
            title="Explore Project Structure",
            description="Get familiar with the overall project structure and organization",
            task_type=TaskType.EXPLORATION,
            difficulty_level="beginner",
            estimated_time="30-45 minutes",
            prerequisites=[],
            learning_objectives=[
                "Understand the project directory structure",
                "Identify key files and their purposes",
                "Recognize the project's technology stack"
            ],
            instructions=[
                "Clone the repository to your local machine",
                "Explore the directory structure and identify main folders",
                "Read the README.md file thoroughly",
                "Identify the main entry points of the application",
                "List the key technologies and dependencies used"
            ],
            code_files_to_study=analysis.entry_points + ["README.md", "package.json"],
            code_files_to_modify=[],
            expected_outcomes=[
                "Clear understanding of project structure",
                "Identification of main application components",
                "Knowledge of setup and running procedures"
            ],
            hints=[
                "Pay attention to naming conventions used in the project",
                "Look for configuration files that reveal the tech stack",
                "Check for documentation in docs/ or similar folders"
            ],
            resources=[],
            validation_criteria=[
                "Can explain the purpose of each main directory",
                "Can identify the application entry points",
                "Can list the main technologies used"
            ],
            next_tasks=[],
            concepts=["project structure", "file organization", "documentation"],
            skills_developed=["code navigation", "project analysis"]
        )
        tasks.append(exploration_task)
        
        # Task 2: Setup and run
        setup_task = LearningTask(
            id=str(uuid.uuid4()),
            title="Setup and Run the Project",
            description="Set up the development environment and run the project",
            task_type=TaskType.IMPLEMENTATION,
            difficulty_level="beginner",
            estimated_time="20-30 minutes",
            prerequisites=[exploration_task.id],
            learning_objectives=[
                "Set up the development environment",
                "Successfully run the project locally",
                "Understand the build and deployment process"
            ],
            instructions=[
                "Install required dependencies",
                "Follow setup instructions in README",
                "Run the project in development mode",
                "Explore the running application",
                "Try different build/run commands"
            ],
            code_files_to_study=["package.json", "Makefile", "docker-compose.yml"],
            code_files_to_modify=[],
            expected_outcomes=[
                "Working development environment",
                "Successfully running application",
                "Understanding of build process"
            ],
            hints=[
                "Check for environment variables that need to be set",
                "Look for Docker setup if available",
                "Pay attention to any error messages during setup"
            ],
            resources=[],
            validation_criteria=[
                "Project runs without errors",
                "Can access the application interface",
                "Understands how to start/stop the application"
            ],
            next_tasks=[],
            concepts=["development environment", "build process", "dependencies"],
            skills_developed=["environment setup", "troubleshooting"]
        )
        tasks.append(setup_task)
        
        return LearningModule(
            id=str(uuid.uuid4()),
            title="Project Overview and Setup",
            description="Get familiar with the project and set up your development environment",
            learning_objectives=[
                "Understand the project structure and purpose",
                "Set up a working development environment",
                "Navigate the codebase effectively"
            ],
            estimated_duration="1-2 hours",
            difficulty_level="beginner",
            prerequisites=[],
            tasks=tasks,
            concepts_covered=["project structure", "development environment", "documentation"],
            skills_developed=["code navigation", "environment setup", "project analysis"],
            assessment_criteria=[
                "Can navigate the project structure confidently",
                "Has a working development environment",
                "Understands the project's purpose and scope"
            ],
            completion_requirements=[
                "Complete all exploration tasks",
                "Successfully run the project locally",
                "Document key findings about the project"
            ]
        )
    
    async def _create_architecture_module(
        self,
        repository: DiscoveredRepository,
        analysis: RepositoryAnalysis,
        user_context: Dict[str, Any]
    ) -> LearningModule:
        """Create architecture analysis module"""
        
        tasks = []
        
        # Generate tasks based on identified architectural patterns
        for i, pattern in enumerate(analysis.architecture.primary_patterns[:3]):  # Limit to 3 patterns
            pattern_task = LearningTask(
                id=str(uuid.uuid4()),
                title=f"Analyze {pattern.value.replace('_', ' ').title()} Pattern",
                description=f"Study how the {pattern.value.replace('_', ' ')} pattern is implemented",
                task_type=TaskType.ANALYSIS,
                difficulty_level="intermediate" if user_context['skill_level'] == 'beginner' else user_context['skill_level'],
                estimated_time="45-60 minutes",
                prerequisites=[],
                learning_objectives=[
                    f"Understand {pattern.value.replace('_', ' ')} pattern implementation",
                    "Identify pattern benefits and trade-offs",
                    "Recognize pattern usage throughout the codebase"
                ],
                instructions=[
                    f"Research the {pattern.value.replace('_', ' ')} pattern if unfamiliar",
                    "Identify where this pattern is used in the codebase",
                    "Analyze the implementation details",
                    "Compare with textbook examples of the pattern",
                    "Document how the pattern benefits this specific project"
                ],
                code_files_to_study=analysis.architecture.key_components[:5],
                code_files_to_modify=[],
                expected_outcomes=[
                    f"Clear understanding of {pattern.value} pattern usage",
                    "Identification of pattern instances in code",
                    "Analysis of pattern benefits for this project"
                ],
                hints=[
                    "Look for consistent naming conventions that indicate the pattern",
                    "Pay attention to how components interact",
                    "Consider why this pattern was chosen for this project"
                ],
                resources=[],
                validation_criteria=[
                    f"Can explain how {pattern.value} is implemented",
                    "Can identify multiple instances of the pattern",
                    "Can discuss pattern benefits and trade-offs"
                ],
                next_tasks=[],
                concepts=[pattern.value, "architecture", "design patterns"],
                skills_developed=["pattern recognition", "architectural analysis"]
            )
            tasks.append(pattern_task)
        
        return LearningModule(
            id=str(uuid.uuid4()),
            title="Architecture Analysis",
            description="Deep dive into the architectural patterns and design decisions",
            learning_objectives=[
                "Understand the overall architecture",
                "Recognize design patterns in use",
                "Analyze architectural trade-offs"
            ],
            estimated_duration="2-3 hours",
            difficulty_level="intermediate",
            prerequisites=["Project Overview and Setup"],
            tasks=tasks,
            concepts_covered=["architecture", "design patterns", "system design"],
            skills_developed=["architectural analysis", "pattern recognition", "system thinking"],
            assessment_criteria=[
                "Can explain the overall architecture",
                "Can identify and explain key design patterns",
                "Can discuss architectural decisions and trade-offs"
            ],
            completion_requirements=[
                "Complete analysis of all major patterns",
                "Create architectural diagram or documentation",
                "Present findings on architectural decisions"
            ]
        )
    
    async def _create_implementation_module(
        self,
        repository: DiscoveredRepository,
        analysis: RepositoryAnalysis,
        user_context: Dict[str, Any]
    ) -> LearningModule:
        """Create core implementation study module"""
        
        tasks = []
        
        # Create tasks based on key components
        for component in analysis.architecture.key_components[:4]:  # Limit to 4 components
            component_task = LearningTask(
                id=str(uuid.uuid4()),
                title=f"Study {component} Implementation",
                description=f"Deep dive into the {component} implementation details",
                task_type=TaskType.ANALYSIS,
                difficulty_level=user_context['skill_level'],
                estimated_time="60-90 minutes",
                prerequisites=[],
                learning_objectives=[
                    f"Understand {component} functionality",
                    "Analyze implementation techniques",
                    "Identify reusable patterns"
                ],
                instructions=[
                    f"Locate all files related to {component}",
                    "Study the main implementation logic",
                    "Trace through key execution paths",
                    "Identify dependencies and interactions",
                    "Document key insights and patterns"
                ],
                code_files_to_study=[],  # Would be populated with actual files
                code_files_to_modify=[],
                expected_outcomes=[
                    f"Complete understanding of {component}",
                    "Documentation of key implementation details",
                    "Identification of reusable patterns"
                ],
                hints=[
                    "Start with the main interface or entry point",
                    "Follow the data flow through the component",
                    "Pay attention to error handling and edge cases"
                ],
                resources=[],
                validation_criteria=[
                    f"Can explain how {component} works",
                    "Can trace through main execution paths",
                    "Can identify key design decisions"
                ],
                next_tasks=[],
                concepts=[component, "implementation", "code analysis"],
                skills_developed=["code reading", "system understanding", "debugging"]
            )
            tasks.append(component_task)
        
        return LearningModule(
            id=str(uuid.uuid4()),
            title="Core Implementation Study",
            description="Study the key implementation details and techniques",
            learning_objectives=[
                "Understand core implementation patterns",
                "Analyze key components in detail",
                "Learn implementation best practices"
            ],
            estimated_duration="4-6 hours",
            difficulty_level=user_context['skill_level'],
            prerequisites=["Architecture Analysis"],
            tasks=tasks,
            concepts_covered=["implementation", "code analysis", "best practices"],
            skills_developed=["code reading", "system understanding", "pattern recognition"],
            assessment_criteria=[
                "Can explain key implementation details",
                "Can trace through complex code paths",
                "Can identify and explain best practices used"
            ],
            completion_requirements=[
                "Complete study of all key components",
                "Create detailed implementation notes",
                "Identify patterns for future use"
            ]
        )
    
    async def _create_practice_module(
        self,
        repository: DiscoveredRepository,
        analysis: RepositoryAnalysis,
        user_context: Dict[str, Any]
    ) -> LearningModule:
        """Create hands-on practice module"""
        
        tasks = []
        
        # Create implementation tasks based on learning opportunities
        for opportunity in analysis.learning_opportunities[:3]:  # Limit to 3 opportunities
            practice_task = LearningTask(
                id=str(uuid.uuid4()),
                title=f"Implement: {opportunity.title}",
                description=f"Hands-on implementation based on {opportunity.description}",
                task_type=TaskType.IMPLEMENTATION,
                difficulty_level=opportunity.difficulty,
                estimated_time=opportunity.estimated_time,
                prerequisites=opportunity.prerequisites,
                learning_objectives=opportunity.learning_objectives,
                instructions=[
                    "Plan your implementation approach",
                    "Create necessary files and structure",
                    "Implement the feature following project patterns",
                    "Test your implementation thoroughly",
                    "Document your approach and decisions"
                ],
                code_files_to_study=opportunity.file_paths,
                code_files_to_modify=[],  # User will create new files
                expected_outcomes=[
                    "Working implementation of the feature",
                    "Code that follows project conventions",
                    "Comprehensive testing of the implementation"
                ],
                hints=[
                    "Study similar implementations in the codebase first",
                    "Follow the established patterns and conventions",
                    "Don't forget error handling and edge cases"
                ],
                resources=[],
                validation_criteria=[
                    "Implementation works correctly",
                    "Code follows project style and patterns",
                    "Includes appropriate tests and documentation"
                ],
                next_tasks=[],
                concepts=opportunity.concepts,
                skills_developed=["implementation", "problem solving", "testing"]
            )
            tasks.append(practice_task)
        
        return LearningModule(
            id=str(uuid.uuid4()),
            title="Hands-on Practice",
            description="Apply your learning through practical implementation tasks",
            learning_objectives=[
                "Apply learned patterns in practice",
                "Implement features using project conventions",
                "Develop problem-solving skills"
            ],
            estimated_duration="6-8 hours",
            difficulty_level=user_context['skill_level'],
            prerequisites=["Core Implementation Study"],
            tasks=tasks,
            concepts_covered=["implementation", "problem solving", "testing"],
            skills_developed=["coding", "debugging", "testing", "documentation"],
            assessment_criteria=[
                "Can implement features following project patterns",
                "Code quality meets project standards",
                "Includes comprehensive testing"
            ],
            completion_requirements=[
                "Complete all implementation tasks",
                "Code passes all tests",
                "Documentation is complete and clear"
            ]
        )
    
    async def _create_advanced_module(
        self,
        repository: DiscoveredRepository,
        analysis: RepositoryAnalysis,
        user_context: Dict[str, Any]
    ) -> LearningModule:
        """Create advanced topics module"""
        
        tasks = []
        
        # Advanced refactoring task
        refactoring_task = LearningTask(
            id=str(uuid.uuid4()),
            title="Refactor and Optimize",
            description="Identify and implement improvements to the codebase",
            task_type=TaskType.REFACTORING,
            difficulty_level="advanced",
            estimated_time="2-3 hours",
            prerequisites=[],
            learning_objectives=[
                "Identify areas for improvement",
                "Apply refactoring techniques",
                "Optimize performance and maintainability"
            ],
            instructions=[
                "Analyze the codebase for improvement opportunities",
                "Identify code smells and technical debt",
                "Plan and implement refactoring changes",
                "Ensure all tests still pass",
                "Measure and document improvements"
            ],
            code_files_to_study=analysis.complexity.advanced_files,
            code_files_to_modify=analysis.complexity.advanced_files,
            expected_outcomes=[
                "Improved code quality and maintainability",
                "Better performance where applicable",
                "Comprehensive documentation of changes"
            ],
            hints=[
                "Start with small, safe refactoring changes",
                "Use automated refactoring tools where available",
                "Always run tests after each change"
            ],
            resources=[],
            validation_criteria=[
                "Code quality metrics show improvement",
                "All existing functionality is preserved",
                "Changes are well documented"
            ],
            next_tasks=[],
            concepts=["refactoring", "code quality", "optimization"],
            skills_developed=["refactoring", "optimization", "quality assessment"]
        )
        tasks.append(refactoring_task)
        
        return LearningModule(
            id=str(uuid.uuid4()),
            title="Advanced Topics",
            description="Explore advanced concepts and contribute improvements",
            learning_objectives=[
                "Master advanced implementation techniques",
                "Contribute meaningful improvements",
                "Develop expertise in the technology stack"
            ],
            estimated_duration="4-6 hours",
            difficulty_level="advanced",
            prerequisites=["Hands-on Practice"],
            tasks=tasks,
            concepts_covered=["refactoring", "optimization", "advanced patterns"],
            skills_developed=["advanced coding", "optimization", "contribution"],
            assessment_criteria=[
                "Can identify and implement improvements",
                "Demonstrates mastery of advanced concepts",
                "Contributions are meaningful and well-executed"
            ],
            completion_requirements=[
                "Complete advanced implementation tasks",
                "Demonstrate measurable improvements",
                "Create comprehensive documentation"
            ]
        )
    
    async def _generate_progression_paths(
        self,
        modules: List[LearningModule],
        user_context: Dict[str, Any]
    ) -> List[ProgressionPath]:
        """Generate learning progression paths"""
        
        # Main linear path
        main_path = ProgressionPath(
            id=str(uuid.uuid4()),
            name="Complete Learning Path",
            description="Follow all modules in sequence for comprehensive learning",
            modules=[module.id for module in modules],
            branching_points={},
            difficulty_curve=[i * 20 for i in range(len(modules))],  # Gradual increase
            estimated_total_time=self._calculate_total_time(modules),
            completion_criteria=[
                "Complete all modules",
                "Pass all assessments",
                "Demonstrate practical application"
            ]
        )
        
        # Fast track path (skip some beginner content)
        if user_context['skill_level'] in ['intermediate', 'advanced', 'expert']:
            fast_track_modules = [m.id for m in modules if m.difficulty_level != 'beginner']
            fast_track_path = ProgressionPath(
                id=str(uuid.uuid4()),
                name="Fast Track",
                description="Accelerated path for experienced developers",
                modules=fast_track_modules,
                branching_points={},
                difficulty_curve=[30 + i * 25 for i in range(len(fast_track_modules))],
                estimated_total_time=self._calculate_total_time([m for m in modules if m.id in fast_track_modules]),
                completion_criteria=[
                    "Complete core modules",
                    "Demonstrate advanced understanding",
                    "Complete practical projects"
                ]
            )
            return [main_path, fast_track_path]
        
        return [main_path]
    
    async def _generate_supporting_materials(
        self,
        repository: DiscoveredRepository,
        analysis: RepositoryAnalysis,
        modules: List[LearningModule],
        user_context: Dict[str, Any]
    ) -> List[SupportingMaterial]:
        """Generate supporting learning materials"""
        
        materials = []
        
        # Documentation material
        if repository.description:
            doc_material = SupportingMaterial(
                id=str(uuid.uuid4()),
                title=f"{repository.name} Documentation",
                type="documentation",
                url=repository.url,
                content=None,
                description="Official repository documentation and README",
                difficulty_level="beginner",
                estimated_time="15-30 minutes",
                related_concepts=repository.topics,
                related_tasks=[modules[0].tasks[0].id if modules and modules[0].tasks else ""]
            )
            materials.append(doc_material)
        
        # Technology-specific resources
        for tech in user_context['technologies'][:3]:  # Limit to 3 technologies
            tech_material = SupportingMaterial(
                id=str(uuid.uuid4()),
                title=f"{tech} Best Practices",
                type="article",
                url=None,
                content=f"Study {tech} best practices and patterns used in this project",
                description=f"Learn {tech} best practices relevant to this project",
                difficulty_level=user_context['skill_level'],
                estimated_time="30-45 minutes",
                related_concepts=[tech, "best practices"],
                related_tasks=[]
            )
            materials.append(tech_material)
        
        return materials
    
    def _calculate_curriculum_metadata(
        self,
        modules: List[LearningModule],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate curriculum metadata"""
        
        total_duration = self._calculate_total_time(modules)
        
        # Determine difficulty progression
        difficulty_progression = DifficultyProgression.MODERATE
        if user_context['skill_level'] == 'beginner':
            difficulty_progression = DifficultyProgression.GENTLE
        elif user_context['skill_level'] in ['advanced', 'expert']:
            difficulty_progression = DifficultyProgression.STEEP
        
        return {
            'total_duration': total_duration,
            'difficulty_progression': difficulty_progression
        }
    
    def _calculate_total_time(self, modules: List[LearningModule]) -> str:
        """Calculate total estimated time for modules"""
        
        total_hours = 0
        for module in modules:
            # Parse duration string (e.g., "2-3 hours" -> average 2.5)
            duration_str = module.estimated_duration
            if '-' in duration_str:
                parts = duration_str.split('-')
                if len(parts) == 2:
                    try:
                        min_hours = float(parts[0])
                        max_hours = float(parts[1].split()[0])  # Remove "hours" part
                        total_hours += (min_hours + max_hours) / 2
                    except ValueError:
                        total_hours += 2  # Default fallback
            else:
                try:
                    total_hours += float(duration_str.split()[0])
                except (ValueError, IndexError):
                    total_hours += 2  # Default fallback
        
        if total_hours < 1:
            return "Less than 1 hour"
        elif total_hours < 2:
            return "1-2 hours"
        elif total_hours < 8:
            return f"{int(total_hours)}-{int(total_hours)+1} hours"
        else:
            days = total_hours / 8  # Assume 8 hours per day
            if days < 2:
                return "1-2 days"
            else:
                return f"{int(days)}-{int(days)+1} days"
    
    async def _generate_personalization_notes(
        self,
        repository: DiscoveredRepository,
        user_context: Dict[str, Any],
        modules: List[LearningModule]
    ) -> str:
        """Generate personalization notes"""
        
        try:
            prompt = f"""
            Generate personalization notes for this learning curriculum:
            
            Repository: {repository.name} - {repository.description}
            User Profile:
            - Skill Level: {user_context['skill_level']}
            - Goals: {', '.join(user_context['goals'])}
            - Time Commitment: {user_context['time_commitment']}
            - Learning Style: {user_context['learning_style']}
            - Technologies: {', '.join(user_context['technologies'])}
            
            Curriculum: {len(modules)} modules with {sum(len(m.tasks) for m in modules)} tasks
            
            Provide 2-3 paragraphs explaining:
            1. How this curriculum is personalized for the user
            2. Key adaptations made based on their profile
            3. Recommendations for getting the most out of the curriculum
            
            Keep it encouraging and specific to their situation.
            """
            
            response = await self.llm_provider.generate_completion(prompt)
            return response.strip()
            
        except Exception as e:
            logger.warning(f"Failed to generate personalization notes: {e}")
            return f"This curriculum has been personalized for a {user_context['skill_level']} developer interested in {', '.join(user_context['technologies'])}. The learning path is designed to match your {user_context['learning_style']} learning style and {user_context['time_commitment']} time commitment."
    
    def _generate_cache_key(self, repository_id: str, user_profile: Dict[str, Any]) -> str:
        """Generate cache key for curriculum"""
        profile_str = json.dumps({
            'skill_level': user_profile.get('experience_level', ''),
            'goals': user_profile.get('learning_goals', []),
            'technologies': user_profile.get('technologies', [])
        }, sort_keys=True)
        
        import hashlib
        cache_data = f"{repository_id}:{profile_str}"
        return f"curriculum:{hashlib.md5(cache_data.encode()).hexdigest()}"
    
    async def _get_cached_curriculum(self, cache_key: str) -> Optional[PersonalizedCurriculum]:
        """Get cached curriculum"""
        try:
            cached_data = await cache_manager.get(cache_key)
            if cached_data:
                curriculum_dict = json.loads(cached_data)
                # Convert dict back to PersonalizedCurriculum
                # This is simplified - in production, you'd want proper deserialization
                return PersonalizedCurriculum(**curriculum_dict)
        except Exception as e:
            logger.warning(f"Failed to get cached curriculum: {e}")
        return None
    
    async def _cache_curriculum(self, cache_key: str, curriculum: PersonalizedCurriculum):
        """Cache curriculum"""
        try:
            curriculum_dict = asdict(curriculum)
            cached_data = json.dumps(curriculum_dict, default=str)
            await cache_manager.set(cache_key, cached_data, ttl=self.cache_ttl)
        except Exception as e:
            logger.warning(f"Failed to cache curriculum: {e}")

# Factory function
def create_curriculum_generation_agent(llm_provider: LLMProvider) -> CurriculumGenerationAgent:
    """Create curriculum generation agent instance"""
    return CurriculumGenerationAgent(llm_provider)