"""
Task Sequence Generator for The Reverse Engineer Coach.

This module implements task generation logic based on identified patterns,
learning path optimization, and task-to-reference-snippet linking.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json

from app.types import ArchitecturalPattern, PatternAnalysis, StructuralElement
from app.mcp_client import CodeSnippet

logger = logging.getLogger(__name__)


class TaskDifficulty(Enum):
    """Task difficulty levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class TaskType(Enum):
    """Types of learning tasks"""
    ANALYSIS = "analysis"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    EXTENSION = "extension"
    INTEGRATION = "integration"
    OPTIMIZATION = "optimization"


@dataclass
class LearningTask:
    """Represents a single learning task"""
    id: str
    title: str
    description: str
    task_type: TaskType
    difficulty: TaskDifficulty
    estimated_hours: float
    prerequisites: List[str] = field(default_factory=list)
    learning_objectives: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    reference_snippets: List[str] = field(default_factory=list)  # CodeSnippet IDs
    deliverables: List[str] = field(default_factory=list)
    hints: List[str] = field(default_factory=list)
    patterns_practiced: List[ArchitecturalPattern] = field(default_factory=list)
    order_index: int = 0


@dataclass
class LearningPath:
    """Represents a complete learning path with ordered tasks"""
    name: str
    description: str
    target_audience: str
    total_estimated_hours: float
    tasks: List[LearningTask] = field(default_factory=list)
    milestones: List[str] = field(default_factory=list)
    completion_criteria: List[str] = field(default_factory=list)


class TaskSequenceOptimizer:
    """Optimizes the sequence of learning tasks for maximum educational value"""
    
    @staticmethod
    def optimize_task_sequence(tasks: List[LearningTask]) -> List[LearningTask]:
        """
        Optimize the sequence of tasks based on dependencies and learning progression.
        
        Args:
            tasks: List of unordered learning tasks
            
        Returns:
            List of tasks in optimal learning sequence
        """
        # Create dependency graph
        task_map = {task.id: task for task in tasks}
        
        # Topological sort based on prerequisites
        visited = set()
        temp_visited = set()
        ordered_tasks = []
        
        def visit(task_id: str):
            if task_id in temp_visited:
                # Circular dependency detected, skip
                return
            if task_id in visited:
                return
            
            temp_visited.add(task_id)
            
            task = task_map.get(task_id)
            if task:
                # Visit prerequisites first
                for prereq in task.prerequisites:
                    if prereq in task_map:
                        visit(prereq)
                
                temp_visited.remove(task_id)
                visited.add(task_id)
                ordered_tasks.append(task)
        
        # Visit all tasks
        for task in tasks:
            if task.id not in visited:
                visit(task.id)
        
        # Assign order indices
        for i, task in enumerate(ordered_tasks):
            task.order_index = i + 1
        
        return ordered_tasks
    
    @staticmethod
    def balance_difficulty_progression(tasks: List[LearningTask]) -> List[LearningTask]:
        """
        Balance the difficulty progression to ensure smooth learning curve.
        
        Args:
            tasks: List of tasks to balance
            
        Returns:
            List of tasks with balanced difficulty progression
        """
        # Group tasks by difficulty
        difficulty_groups = {
            TaskDifficulty.BEGINNER: [],
            TaskDifficulty.INTERMEDIATE: [],
            TaskDifficulty.ADVANCED: []
        }
        
        for task in tasks:
            difficulty_groups[task.difficulty].append(task)
        
        # Create balanced sequence: start with beginners, mix intermediate, end with advanced
        balanced_tasks = []
        
        # Add beginner tasks first
        balanced_tasks.extend(difficulty_groups[TaskDifficulty.BEGINNER])
        
        # Interleave intermediate and remaining beginner tasks
        intermediate_tasks = difficulty_groups[TaskDifficulty.INTERMEDIATE]
        for i, task in enumerate(intermediate_tasks):
            balanced_tasks.append(task)
        
        # Add advanced tasks at the end
        balanced_tasks.extend(difficulty_groups[TaskDifficulty.ADVANCED])
        
        # Update order indices
        for i, task in enumerate(balanced_tasks):
            task.order_index = i + 1
        
        return balanced_tasks


class TaskGenerator:
    """Generates learning tasks based on architectural patterns and code analysis"""
    
    def __init__(self):
        self.optimizer = TaskSequenceOptimizer()
    
    def generate_learning_path(self, 
                             specification: Dict[str, Any],
                             target_audience: str = "mid-level software engineers",
                             focus_patterns: Optional[List[str]] = None) -> LearningPath:
        """
        Generate a complete learning path from specification data.
        
        Args:
            specification: Complete specification from SpecificationGenerator
            target_audience: Target audience for the learning path
            focus_patterns: Optional list of patterns to focus on
            
        Returns:
            Complete learning path with optimized task sequence
        """
        logger.info(f"Generating learning path for {target_audience}")
        
        # Extract data from specification
        repo_info = specification.get('repository_info', {})
        pattern_analysis = specification.get('pattern_analysis', [])
        structural_elements = specification.get('structural_elements', [])
        simplified_code = specification.get('simplified_code', [])
        
        # Filter patterns if focus is specified
        if focus_patterns:
            pattern_analysis = [p for p in pattern_analysis if p.get('pattern') in focus_patterns]
        
        # Generate tasks for each pattern
        all_tasks = []
        
        # 1. Analysis tasks (understand existing patterns)
        analysis_tasks = self._generate_analysis_tasks(pattern_analysis, structural_elements)
        all_tasks.extend(analysis_tasks)
        
        # 2. Implementation tasks (build simplified versions)
        implementation_tasks = self._generate_implementation_tasks(
            pattern_analysis, simplified_code, target_audience
        )
        all_tasks.extend(implementation_tasks)
        
        # 3. Testing tasks (validate implementations)
        testing_tasks = self._generate_testing_tasks(pattern_analysis, target_audience)
        all_tasks.extend(testing_tasks)
        
        # 4. Extension tasks (add features and complexity)
        extension_tasks = self._generate_extension_tasks(pattern_analysis, target_audience)
        all_tasks.extend(extension_tasks)
        
        # 5. Integration tasks (combine patterns)
        if len(pattern_analysis) > 1:
            integration_tasks = self._generate_integration_tasks(pattern_analysis, target_audience)
            all_tasks.extend(integration_tasks)
        
        # Optimize task sequence
        optimized_tasks = self.optimizer.optimize_task_sequence(all_tasks)
        balanced_tasks = self.optimizer.balance_difficulty_progression(optimized_tasks)
        
        # Calculate total time
        total_hours = sum(task.estimated_hours for task in balanced_tasks)
        
        # Create learning path
        path = LearningPath(
            name=f"Reverse Engineering {repo_info.get('name', 'Repository')}",
            description=f"Learn architectural patterns from {repo_info.get('name', 'a production system')}",
            target_audience=target_audience,
            total_estimated_hours=total_hours,
            tasks=balanced_tasks,
            milestones=self._generate_milestones(balanced_tasks),
            completion_criteria=self._generate_completion_criteria(pattern_analysis)
        )
        
        logger.info(f"Generated learning path with {len(balanced_tasks)} tasks, "
                   f"estimated {total_hours:.1f} hours")
        
        return path
    
    def _generate_analysis_tasks(self, pattern_analysis: List[Dict], 
                               structural_elements: List[Dict]) -> List[LearningTask]:
        """Generate tasks for analyzing existing patterns"""
        tasks = []
        
        for i, pattern in enumerate(pattern_analysis):
            pattern_name = pattern.get('pattern', 'Unknown Pattern')
            confidence = pattern.get('confidence', 0.0)
            evidence = pattern.get('evidence', [])
            
            # Determine difficulty based on pattern complexity
            difficulty = self._determine_difficulty(pattern.get('implementation_complexity', 'intermediate'))
            
            task = LearningTask(
                id=f"analysis_{i+1}",
                title=f"Analyze {pattern_name} Implementation",
                description=f"Study how {pattern_name} is implemented in the codebase. "
                           f"Examine the evidence: {', '.join(evidence[:3])}",
                task_type=TaskType.ANALYSIS,
                difficulty=difficulty,
                estimated_hours=1.5 + (confidence * 0.5),  # More confident patterns take longer to analyze
                learning_objectives=[
                    f"Understand the purpose of {pattern_name}",
                    f"Identify key components and their relationships",
                    f"Recognize the pattern in different contexts"
                ],
                success_criteria=[
                    f"Document the structure of {pattern_name}",
                    f"Explain the benefits and trade-offs",
                    f"Identify at least 2 key components"
                ],
                reference_snippets=evidence[:5],  # Link to evidence code snippets
                deliverables=[
                    f"{pattern_name} analysis document",
                    "Component relationship diagram",
                    "Benefits and trade-offs summary"
                ],
                patterns_practiced=[self._string_to_pattern(pattern_name)]
            )
            
            tasks.append(task)
        
        return tasks
    
    def _generate_implementation_tasks(self, pattern_analysis: List[Dict], 
                                     simplified_code: List[Dict],
                                     target_audience: str) -> List[LearningTask]:
        """Generate tasks for implementing simplified versions of patterns"""
        tasks = []
        
        for i, pattern in enumerate(pattern_analysis):
            pattern_name = pattern.get('pattern', 'Unknown Pattern')
            learning_value = pattern.get('learning_value', 0.5)
            
            # Find related simplified code
            related_code = [code for code in simplified_code 
                          if pattern_name in code.get('preserved_patterns', [])]
            
            difficulty = self._determine_difficulty(pattern.get('implementation_complexity', 'intermediate'))
            
            # Adjust difficulty based on target audience
            if 'junior' in target_audience.lower():
                difficulty = TaskDifficulty.BEGINNER
            elif 'senior' in target_audience.lower() and difficulty == TaskDifficulty.BEGINNER:
                difficulty = TaskDifficulty.INTERMEDIATE
            
            task = LearningTask(
                id=f"implement_{i+1}",
                title=f"Implement Simplified {pattern_name}",
                description=f"Create a simplified implementation of {pattern_name} "
                           f"focusing on core functionality without production complexity.",
                task_type=TaskType.IMPLEMENTATION,
                difficulty=difficulty,
                estimated_hours=3.0 + (learning_value * 2.0),  # Higher learning value = more time
                prerequisites=[f"analysis_{i+1}"],  # Must analyze before implementing
                learning_objectives=[
                    f"Implement core {pattern_name} functionality",
                    f"Apply architectural principles",
                    f"Create clean, maintainable code"
                ],
                success_criteria=[
                    f"Working {pattern_name} implementation",
                    "Code follows established patterns",
                    "Implementation is well-documented",
                    "Core functionality is demonstrated"
                ],
                reference_snippets=[code.get('name', '') for code in related_code[:3]],
                deliverables=[
                    f"Simplified {pattern_name} implementation",
                    "Unit tests for core functionality",
                    "Implementation documentation"
                ],
                hints=[
                    f"Start with the core interface or abstract class",
                    f"Focus on the essential behavior of {pattern_name}",
                    "Remove logging, metrics, and error handling initially",
                    "Add complexity incrementally"
                ],
                patterns_practiced=[self._string_to_pattern(pattern_name)]
            )
            
            tasks.append(task)
        
        return tasks
    
    def _generate_testing_tasks(self, pattern_analysis: List[Dict], 
                              target_audience: str) -> List[LearningTask]:
        """Generate tasks for testing implementations"""
        tasks = []
        
        for i, pattern in enumerate(pattern_analysis):
            pattern_name = pattern.get('pattern', 'Unknown Pattern')
            
            task = LearningTask(
                id=f"test_{i+1}",
                title=f"Test {pattern_name} Implementation",
                description=f"Create comprehensive tests for your {pattern_name} implementation "
                           f"to ensure correctness and reliability.",
                task_type=TaskType.TESTING,
                difficulty=TaskDifficulty.INTERMEDIATE,
                estimated_hours=2.0,
                prerequisites=[f"implement_{i+1}"],
                learning_objectives=[
                    f"Validate {pattern_name} behavior",
                    "Learn testing best practices",
                    "Ensure implementation correctness"
                ],
                success_criteria=[
                    "All tests pass",
                    "Edge cases are covered",
                    "Test coverage is adequate",
                    "Tests are maintainable"
                ],
                deliverables=[
                    f"Test suite for {pattern_name}",
                    "Test coverage report",
                    "Edge case documentation"
                ],
                hints=[
                    "Test the happy path first",
                    "Consider boundary conditions",
                    "Test error scenarios",
                    "Use descriptive test names"
                ],
                patterns_practiced=[self._string_to_pattern(pattern_name)]
            )
            
            tasks.append(task)
        
        return tasks
    
    def _generate_extension_tasks(self, pattern_analysis: List[Dict], 
                                target_audience: str) -> List[LearningTask]:
        """Generate tasks for extending implementations with additional features"""
        tasks = []
        
        for i, pattern in enumerate(pattern_analysis):
            pattern_name = pattern.get('pattern', 'Unknown Pattern')
            
            task = LearningTask(
                id=f"extend_{i+1}",
                title=f"Extend {pattern_name} with Advanced Features",
                description=f"Add advanced features to your {pattern_name} implementation "
                           f"such as error handling, logging, and performance optimizations.",
                task_type=TaskType.EXTENSION,
                difficulty=TaskDifficulty.ADVANCED,
                estimated_hours=4.0,
                prerequisites=[f"test_{i+1}"],
                learning_objectives=[
                    f"Add production-ready features to {pattern_name}",
                    "Learn about error handling and logging",
                    "Understand performance considerations"
                ],
                success_criteria=[
                    "Advanced features are implemented",
                    "Error handling is comprehensive",
                    "Performance is acceptable",
                    "Code remains maintainable"
                ],
                deliverables=[
                    f"Enhanced {pattern_name} implementation",
                    "Error handling documentation",
                    "Performance benchmarks"
                ],
                hints=[
                    "Add error handling gradually",
                    "Consider logging at appropriate levels",
                    "Profile before optimizing",
                    "Maintain backward compatibility"
                ],
                patterns_practiced=[self._string_to_pattern(pattern_name)]
            )
            
            tasks.append(task)
        
        return tasks
    
    def _generate_integration_tasks(self, pattern_analysis: List[Dict], 
                                  target_audience: str) -> List[LearningTask]:
        """Generate tasks for integrating multiple patterns"""
        tasks = []
        
        if len(pattern_analysis) < 2:
            return tasks
        
        # Create integration tasks for pattern combinations
        patterns = [p.get('pattern', 'Unknown') for p in pattern_analysis]
        
        task = LearningTask(
            id="integration_1",
            title="Integrate Multiple Architectural Patterns",
            description=f"Combine your implementations of {', '.join(patterns[:3])} "
                       f"into a cohesive system that demonstrates how patterns work together.",
            task_type=TaskType.INTEGRATION,
            difficulty=TaskDifficulty.ADVANCED,
            estimated_hours=6.0,
            prerequisites=[f"extend_{i+1}" for i in range(len(pattern_analysis))],
            learning_objectives=[
                "Understand pattern interactions",
                "Create cohesive system architecture",
                "Learn integration best practices"
            ],
            success_criteria=[
                "Patterns work together seamlessly",
                "System demonstrates clear architecture",
                "Integration is well-documented",
                "System handles realistic scenarios"
            ],
            deliverables=[
                "Integrated system implementation",
                "Architecture documentation",
                "Integration test suite",
                "System demonstration"
            ],
            hints=[
                "Start with clear interfaces between patterns",
                "Consider data flow between components",
                "Test integration points thoroughly",
                "Document architectural decisions"
            ],
            patterns_practiced=[self._string_to_pattern(p) for p in patterns]
        )
        
        tasks.append(task)
        
        return tasks
    
    def _generate_milestones(self, tasks: List[LearningTask]) -> List[str]:
        """Generate learning milestones based on task progression"""
        milestones = []
        
        # Group tasks by type
        task_groups = {}
        for task in tasks:
            task_type = task.task_type
            if task_type not in task_groups:
                task_groups[task_type] = []
            task_groups[task_type].append(task)
        
        # Create milestones for each task type completion
        if TaskType.ANALYSIS in task_groups:
            milestones.append(f"Pattern Analysis Complete ({len(task_groups[TaskType.ANALYSIS])} patterns analyzed)")
        
        if TaskType.IMPLEMENTATION in task_groups:
            milestones.append(f"Core Implementation Complete ({len(task_groups[TaskType.IMPLEMENTATION])} patterns implemented)")
        
        if TaskType.TESTING in task_groups:
            milestones.append(f"Testing Phase Complete (All implementations validated)")
        
        if TaskType.EXTENSION in task_groups:
            milestones.append(f"Advanced Features Complete (Production-ready implementations)")
        
        if TaskType.INTEGRATION in task_groups:
            milestones.append(f"System Integration Complete (Cohesive architecture demonstrated)")
        
        return milestones
    
    def _generate_completion_criteria(self, pattern_analysis: List[Dict]) -> List[str]:
        """Generate overall completion criteria for the learning path"""
        criteria = [
            "All learning tasks completed successfully",
            "All deliverables submitted and reviewed",
            f"Demonstrated understanding of {len(pattern_analysis)} architectural patterns",
            "Created working implementations of all patterns",
            "Integrated patterns into cohesive system"
        ]
        
        if len(pattern_analysis) > 2:
            criteria.append("Explained pattern interactions and trade-offs")
        
        return criteria
    
    def _determine_difficulty(self, complexity_str: str) -> TaskDifficulty:
        """Convert complexity string to TaskDifficulty enum"""
        complexity_map = {
            'beginner': TaskDifficulty.BEGINNER,
            'intermediate': TaskDifficulty.INTERMEDIATE,
            'advanced': TaskDifficulty.ADVANCED
        }
        return complexity_map.get(complexity_str.lower(), TaskDifficulty.INTERMEDIATE)
    
    def _string_to_pattern(self, pattern_str: str) -> ArchitecturalPattern:
        """Convert pattern string to ArchitecturalPattern enum"""
        # Try to match the pattern string to enum values
        for pattern in ArchitecturalPattern:
            if pattern.value.lower() == pattern_str.lower():
                return pattern
        
        # Default fallback
        return ArchitecturalPattern.HANDLER
    
    def link_tasks_to_snippets(self, tasks: List[LearningTask], 
                             code_snippets: List[CodeSnippet]) -> List[LearningTask]:
        """
        Link learning tasks to relevant code snippets for reference.
        
        Args:
            tasks: List of learning tasks
            code_snippets: List of available code snippets
            
        Returns:
            Tasks with updated reference_snippets links
        """
        # Create snippet lookup by name and patterns
        snippet_map = {}
        for snippet in code_snippets:
            snippet_map[snippet.name] = snippet
        
        # Link tasks to snippets
        for task in tasks:
            # Find snippets that match task patterns
            relevant_snippets = []
            
            for pattern in task.patterns_practiced:
                for snippet in code_snippets:
                    # Check if snippet name or content relates to the pattern
                    pattern_keywords = pattern.value.lower().split()
                    snippet_name_lower = snippet.name.lower()
                    
                    if any(keyword in snippet_name_lower for keyword in pattern_keywords):
                        if snippet.name not in relevant_snippets:
                            relevant_snippets.append(snippet.name)
            
            # Update task with relevant snippets
            task.reference_snippets.extend(relevant_snippets[:3])  # Limit to 3 most relevant
        
        return tasks
    
    def export_learning_path_markdown(self, learning_path: LearningPath) -> str:
        """Export learning path as formatted Markdown"""
        md_content = f"""# {learning_path.name}

## Overview
{learning_path.description}

**Target Audience:** {learning_path.target_audience}
**Estimated Time:** {learning_path.total_estimated_hours:.1f} hours

## Learning Tasks

"""
        
        for task in learning_path.tasks:
            md_content += f"""### {task.order_index}. {task.title}

**Type:** {task.task_type.value.title()}  
**Difficulty:** {task.difficulty.value.title()}  
**Estimated Time:** {task.estimated_hours:.1f} hours

{task.description}

**Learning Objectives:**
{chr(10).join(f"- {obj}" for obj in task.learning_objectives)}

**Success Criteria:**
{chr(10).join(f"- {criteria}" for criteria in task.success_criteria)}

**Deliverables:**
{chr(10).join(f"- {deliverable}" for deliverable in task.deliverables)}

"""
            
            if task.hints:
                md_content += f"""**Hints:**
{chr(10).join(f"- {hint}" for hint in task.hints)}

"""
            
            if task.reference_snippets:
                md_content += f"""**Reference Code:**
{chr(10).join(f"- {snippet}" for snippet in task.reference_snippets)}

"""
        
        md_content += f"""## Milestones

{chr(10).join(f"- {milestone}" for milestone in learning_path.milestones)}

## Completion Criteria

{chr(10).join(f"- {criteria}" for criteria in learning_path.completion_criteria)}
"""
        
        return md_content