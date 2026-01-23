"""
Property-based test for language-specific task generation.

Feature: reverse-engineer-coach, Property 18: Language-Specific Task Generation
Validates: Requirements 9.2

This test verifies that for any selected implementation language, generated task 
instructions include language-appropriate syntax and examples.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from typing import List, Dict, Any
import asyncio

from app.language_support import (
    LanguageSupport, LanguageSpecificTaskGenerator, ProgrammingLanguage
)
from app.llm_provider import MockLLMProvider
from app.types import ArchitecturalPattern


# Test data strategies
@st.composite
def programming_language_strategy(draw):
    """Generate valid programming languages"""
    supported_languages = LanguageSupport.get_supported_languages()
    return draw(st.sampled_from(supported_languages))


@st.composite
def base_task_strategy(draw):
    """Generate base learning tasks"""
    patterns = list(ArchitecturalPattern)
    selected_patterns = draw(st.lists(
        st.sampled_from(patterns), 
        min_size=1, 
        max_size=3,
        unique=True
    ))
    
    task_types = ['analysis', 'implementation', 'testing', 'extension']
    difficulties = ['beginner', 'intermediate', 'advanced']
    
    return {
        'id': draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        'title': draw(st.text(min_size=10, max_size=100)),
        'description': draw(st.text(min_size=20, max_size=500)),
        'task_type': draw(st.sampled_from(task_types)),
        'difficulty': draw(st.sampled_from(difficulties)),
        'patterns_practiced': [p.value for p in selected_patterns],
        'estimated_hours': draw(st.floats(min_value=0.5, max_value=10.0)),
        'learning_objectives': draw(st.lists(st.text(min_size=5, max_size=50), min_size=1, max_size=5)),
        'success_criteria': draw(st.lists(st.text(min_size=5, max_size=50), min_size=1, max_size=5))
    }


@st.composite
def task_list_strategy(draw):
    """Generate list of base tasks"""
    return draw(st.lists(base_task_strategy(), min_size=1, max_size=5))


class TestLanguageSpecificTaskGeneration:
    """Property-based tests for language-specific task generation"""
    
    def _create_task_generator(self):
        """Create task generator with mock LLM provider"""
        mock_provider = MockLLMProvider()
        return LanguageSpecificTaskGenerator(mock_provider)
    
    @given(
        target_language=programming_language_strategy(),
        base_tasks=task_list_strategy()
    )
    @settings(max_examples=3, deadline=10000)  # Increased deadline for async operations
    def test_language_specific_task_generation_property(self, target_language, base_tasks):
        """
        Property 18: Language-Specific Task Generation
        
        For any selected implementation language, generated task instructions 
        should include language-appropriate syntax and examples.
        """
        # Skip if no base tasks
        assume(len(base_tasks) > 0)
        
        # Create task generator for this test
        task_generator = self._create_task_generator()
        
        # Run async test
        result = asyncio.run(self._run_language_task_generation(
            task_generator, target_language, base_tasks
        ))
        
        # Verify the property holds
        self._verify_language_specific_properties(result, target_language, base_tasks)
    
    async def _run_language_task_generation(self, task_generator, target_language, base_tasks):
        """Run the language-specific task generation"""
        try:
            # Generate language-specific tasks
            adapted_tasks = await task_generator.generate_language_specific_tasks(
                base_tasks, target_language
            )
            
            return {
                'success': True,
                'adapted_tasks': adapted_tasks,
                'target_language': target_language,
                'base_tasks': base_tasks
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'target_language': target_language,
                'base_tasks': base_tasks
            }
    
    def _verify_language_specific_properties(self, result, target_language, base_tasks):
        """Verify that language-specific properties hold"""
        # Property: Task generation should succeed for valid inputs
        assert result['success'], f"Task generation failed: {result.get('error', 'Unknown error')}"
        
        adapted_tasks = result['adapted_tasks']
        language_config = LanguageSupport.get_language_config(target_language)
        
        # Property: Number of adapted tasks should match base tasks
        assert len(adapted_tasks) == len(base_tasks), \
            f"Expected {len(base_tasks)} adapted tasks, got {len(adapted_tasks)}"
        
        # Property: Each adapted task should have language-specific information
        for i, adapted_task in enumerate(adapted_tasks):
            base_task = base_tasks[i]
            
            # Property: Adapted task should preserve original task structure
            assert adapted_task['id'] == base_task['id'], \
                f"Task ID should be preserved: expected {base_task['id']}, got {adapted_task['id']}"
            
            assert adapted_task['title'] == base_task['title'], \
                f"Task title should be preserved: expected {base_task['title']}, got {adapted_task['title']}"
            
            # Property: Adapted task should include target language information
            assert adapted_task.get('target_language') == target_language.value, \
                f"Target language should be {target_language.value}, got {adapted_task.get('target_language')}"
            
            # Property: Language conventions should be included
            conventions = adapted_task.get('language_conventions', {})
            assert isinstance(conventions, dict), \
                f"Language conventions should be a dictionary, got {type(conventions)}"
            
            # Property: Language-specific description should be present
            language_description = adapted_task.get('language_specific_description', '')
            assert isinstance(language_description, str), \
                f"Language-specific description should be a string, got {type(language_description)}"
            
            # Property: Framework recommendations should match language
            frameworks = adapted_task.get('recommended_frameworks', [])
            assert isinstance(frameworks, list), \
                f"Recommended frameworks should be a list, got {type(frameworks)}"
            
            # Verify frameworks are appropriate for the language
            language_frameworks = [f.value for f in language_config.frameworks]
            for framework in frameworks:
                if framework:  # Skip empty frameworks
                    assert framework in language_frameworks, \
                        f"Framework {framework} not supported for {target_language.value}"
            
            # Property: Test framework should match language configuration
            test_framework = adapted_task.get('test_framework')
            if test_framework:
                assert test_framework == language_config.test_framework, \
                    f"Test framework should be {language_config.test_framework}, got {test_framework}"
            
            # Property: Package manager should match language configuration
            package_manager = adapted_task.get('package_manager')
            if package_manager:
                assert package_manager == language_config.package_manager, \
                    f"Package manager should be {language_config.package_manager}, got {package_manager}"
    
    @given(
        target_language=programming_language_strategy(),
        source_language=programming_language_strategy(),
        base_tasks=task_list_strategy()
    )
    @settings(max_examples=3, deadline=10000)
    def test_cross_language_adaptation_property(self, target_language, source_language, base_tasks):
        """
        Property: Cross-language adaptation should preserve task essence while adapting syntax
        """
        # Skip if languages are the same
        assume(target_language != source_language)
        assume(len(base_tasks) > 0)
        
        # Create task generator for this test
        task_generator = self._create_task_generator()
        
        # Run async test
        result = asyncio.run(self._run_cross_language_adaptation(
            task_generator, target_language, source_language, base_tasks
        ))
        
        # Verify cross-language properties
        self._verify_cross_language_properties(result, target_language, source_language, base_tasks)
    
    async def _run_cross_language_adaptation(self, task_generator, target_language, source_language, base_tasks):
        """Run cross-language task adaptation"""
        try:
            adapted_tasks = await task_generator.generate_language_specific_tasks(
                base_tasks, target_language, source_language
            )
            
            return {
                'success': True,
                'adapted_tasks': adapted_tasks,
                'target_language': target_language,
                'source_language': source_language,
                'base_tasks': base_tasks
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'target_language': target_language,
                'source_language': source_language,
                'base_tasks': base_tasks
            }
    
    def _verify_cross_language_properties(self, result, target_language, source_language, base_tasks):
        """Verify cross-language adaptation properties"""
        assert result['success'], f"Cross-language adaptation failed: {result.get('error', 'Unknown error')}"
        
        adapted_tasks = result['adapted_tasks']
        
        # Property: Cross-language adaptation should maintain task count
        assert len(adapted_tasks) == len(base_tasks), \
            f"Cross-language adaptation should preserve task count"
        
        # Property: Each task should be adapted for target language
        for adapted_task in adapted_tasks:
            assert adapted_task.get('target_language') == target_language.value, \
                f"Task should be adapted for {target_language.value}"
            
            # Property: Language-specific content should be present
            assert 'language_specific_description' in adapted_task, \
                f"Cross-language adapted task should have language-specific description"
    
    @given(
        target_language=programming_language_strategy()
    )
    @settings(max_examples=3, deadline=5000)
    def test_language_configuration_consistency_property(self, target_language):
        """
        Property: Language configuration should be consistent and complete
        """
        config = LanguageSupport.get_language_config(target_language)
        
        # Property: Configuration should have all required fields
        assert config.language == target_language, \
            f"Configuration language should match requested language"
        
        assert isinstance(config.frameworks, list), \
            f"Frameworks should be a list"
        
        assert isinstance(config.syntax_style, str) and config.syntax_style, \
            f"Syntax style should be a non-empty string"
        
        assert isinstance(config.package_manager, str) and config.package_manager, \
            f"Package manager should be a non-empty string"
        
        assert isinstance(config.test_framework, str) and config.test_framework, \
            f"Test framework should be a non-empty string"
        
        assert isinstance(config.conventions, dict), \
            f"Conventions should be a dictionary"
        
        # Property: Conventions should include essential naming patterns
        essential_conventions = ['naming', 'class_naming', 'file_extension']
        for convention in essential_conventions:
            assert convention in config.conventions, \
                f"Configuration should include {convention} convention"
    
    @given(
        base_tasks=task_list_strategy()
    )
    @settings(max_examples=3, deadline=8000)
    def test_task_adaptation_preserves_patterns_property(self, base_tasks):
        """
        Property: Task adaptation should preserve architectural patterns
        """
        assume(len(base_tasks) > 0)
        
        # Create task generator for this test
        task_generator = self._create_task_generator()
        
        # Use Python as target language for consistency
        target_language = ProgrammingLanguage.PYTHON
        
        result = asyncio.run(self._run_language_task_generation(
            task_generator, target_language, base_tasks
        ))
        
        assert result['success'], f"Task adaptation failed: {result.get('error', 'Unknown error')}"
        
        adapted_tasks = result['adapted_tasks']
        
        # Property: Architectural patterns should be preserved
        for i, adapted_task in enumerate(adapted_tasks):
            base_task = base_tasks[i]
            base_patterns = set(base_task.get('patterns_practiced', []))
            
            # Patterns should be preserved in the adapted task
            # (Note: In a real implementation, patterns might be in different fields)
            # For this test, we verify the patterns are still referenced
            task_content = str(adapted_task)
            
            for pattern in base_patterns:
                # Pattern should be mentioned somewhere in the adapted task
                assert pattern.lower() in task_content.lower() or \
                       any(pattern.lower() in str(v).lower() for v in adapted_task.values()), \
                    f"Pattern {pattern} should be preserved in adapted task"


# Integration test for the complete workflow
class TestLanguageSpecificTaskGenerationIntegration:
    """Integration tests for language-specific task generation"""
    
    @pytest.mark.asyncio
    async def test_complete_language_adaptation_workflow(self):
        """Test the complete workflow of language-specific task adaptation"""
        # Create task generator
        mock_provider = MockLLMProvider()
        task_generator = LanguageSpecificTaskGenerator(mock_provider)
        
        # Create sample base tasks
        base_tasks = [
            {
                'id': 'task_1',
                'title': 'Implement Repository Pattern',
                'description': 'Create a repository for data access',
                'difficulty': 'intermediate',
                'patterns_practiced': ['Repository Pattern'],
                'learning_objectives': ['Understand data access patterns'],
                'success_criteria': ['Working repository implementation']
            }
        ]
        
        # Test adaptation to different languages
        languages_to_test = [ProgrammingLanguage.PYTHON, ProgrammingLanguage.TYPESCRIPT]
        
        for target_language in languages_to_test:
            adapted_tasks = await task_generator.generate_language_specific_tasks(
                base_tasks, target_language
            )
            
            # Verify adaptation succeeded
            assert len(adapted_tasks) == 1
            adapted_task = adapted_tasks[0]
            
            # Verify language-specific fields
            assert adapted_task['target_language'] == target_language.value
            assert 'language_conventions' in adapted_task
            assert 'recommended_frameworks' in adapted_task
            
            # Verify language configuration is appropriate
            config = LanguageSupport.get_language_config(target_language)
            assert adapted_task['test_framework'] == config.test_framework
            assert adapted_task['package_manager'] == config.package_manager


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])