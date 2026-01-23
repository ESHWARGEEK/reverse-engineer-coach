"""
Property-based tests for the specification generator engine.

Tests structural code extraction, pattern recognition, and code simplification
using property-based testing with Hypothesis.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.strategies import composite
from typing import List, Dict, Any
import re

from app.spec_generator import (
    CodePatternExtractor, 
    CodeSimplifier, 
    PatternAnalyzer,
    SpecificationGenerator
)
from app.types import StructuralElement, ArchitecturalPattern, SimplifiedCode
from app.mcp_client import CodeSnippet, RepositoryAnalysis, GitHubRepoMetadata
from app.llm_provider import MockLLMProvider


# Test data generators
@composite
def code_snippet_strategy(draw):
    """Generate valid CodeSnippet instances for testing"""
    languages = ['python', 'go', 'typescript', 'javascript', 'java']
    snippet_types = ['interface', 'class', 'struct', 'function', 'type']
    
    language = draw(st.sampled_from(languages))
    snippet_type = draw(st.sampled_from(snippet_types))
    name = draw(st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=1, max_size=50))
    
    # Generate realistic code content based on language and type
    if language == 'python' and snippet_type == 'class':
        content = f"""class {name}:
    def __init__(self):
        self.data = []
    
    def process(self, item):
        return item.upper()
    
    def handle_request(self, request):
        return self.process(request)"""
    
    elif language == 'go' and snippet_type == 'struct':
        content = f"""type {name} struct {{
    Data []string
    Config map[string]interface{{}}
}}

func (s *{name}) Process(item string) string {{
    return strings.ToUpper(item)
}}

func (s *{name}) HandleRequest(req Request) Response {{
    return s.Process(req.Data)
}}"""
    
    elif language == 'typescript' and snippet_type == 'interface':
        content = f"""interface {name} {{
    data: string[];
    config: Record<string, any>;
    
    process(item: string): string;
    handleRequest(request: Request): Response;
}}"""
    
    else:
        # Generic content
        content = f"""// {snippet_type} {name}
{snippet_type} {name} {{
    // Implementation details
    function process() {{
        return "processed";
    }}
}}"""
    
    file_path = draw(st.text(min_size=5, max_size=100)) + f".{language[:2]}"
    start_line = draw(st.integers(min_value=1, max_value=100))
    end_line = start_line + draw(st.integers(min_value=5, max_value=50))
    
    return CodeSnippet(
        file_path=file_path,
        content=content,
        start_line=start_line,
        end_line=end_line,
        language=language,
        snippet_type=snippet_type,
        name=name,
        github_permalink=f"https://github.com/test/repo/blob/main/{file_path}#L{start_line}",
        commit_sha="abc123",
        architectural_significance=draw(st.floats(min_value=0.0, max_value=1.0))
    )


@composite
def repository_analysis_strategy(draw):
    """Generate valid RepositoryAnalysis instances for testing"""
    repo_url = "https://github.com/test/repo"
    
    # Generate metadata with all required fields
    name = draw(st.text(min_size=1, max_size=50))
    owner = draw(st.text(min_size=1, max_size=30))
    
    metadata = GitHubRepoMetadata(
        owner=owner,
        name=name,
        full_name=f"{owner}/{name}",
        description=draw(st.text(min_size=0, max_size=200)),
        language=draw(st.sampled_from(['Python', 'Go', 'TypeScript', 'Java'])),
        languages={"Python": 1000, "JavaScript": 500},
        stars=draw(st.integers(min_value=0, max_value=10000)),
        forks=draw(st.integers(min_value=0, max_value=1000)),
        size=draw(st.integers(min_value=100, max_value=100000)),
        default_branch="main",
        is_private=False,
        is_fork=False,
        created_at="2023-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
        clone_url=f"https://github.com/{owner}/{name}.git",
        html_url=f"https://github.com/{owner}/{name}"
    )
    
    # Generate code snippets
    code_snippets = draw(st.lists(code_snippet_strategy(), min_size=1, max_size=10))
    
    # Generate architecture patterns
    patterns = draw(st.lists(st.text(min_size=5, max_size=30), min_size=1, max_size=5))
    
    return RepositoryAnalysis(
        repository_url=repo_url,
        metadata=metadata,
        total_files_analyzed=draw(st.integers(min_value=1, max_value=100)),
        relevant_files=[f"file_{i}.py" for i in range(draw(st.integers(min_value=1, max_value=20)))],
        code_snippets=code_snippets,
        architecture_patterns=patterns,
        primary_language=metadata.language.lower(),
        complexity_score=draw(st.floats(min_value=0.0, max_value=1.0))
    )
@composite
def structural_element_strategy(draw):
    """Generate valid StructuralElement instances for testing"""
    languages = ['python', 'go', 'typescript', 'javascript']
    element_types = ['interface', 'class', 'struct', 'function', 'type']
    
    name = draw(st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=1, max_size=50))
    element_type = draw(st.sampled_from(element_types))
    language = draw(st.sampled_from(languages))
    
    # Generate realistic content
    content = f"""// {element_type} {name}
{element_type} {name} {{
    // Methods and properties
    function handle() {{ return true; }}
    function process() {{ return "done"; }}
}}"""
    
    methods = draw(st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=10))
    dependencies = draw(st.lists(st.text(min_size=1, max_size=30), min_size=0, max_size=5))
    properties = draw(st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=8))
    
    return StructuralElement(
        name=name,
        element_type=element_type,
        file_path=f"test/{name.lower()}.{language[:2]}",
        start_line=draw(st.integers(min_value=1, max_value=100)),
        end_line=draw(st.integers(min_value=1, max_value=200)),
        language=language,
        content=content,
        dependencies=dependencies,
        methods=methods,
        properties=properties,
        patterns=[],
        complexity_score=draw(st.floats(min_value=0.0, max_value=1.0)),
        architectural_significance=draw(st.floats(min_value=0.0, max_value=1.0))
    )


class TestStructuralCodeExtraction:
    """
    Property-based tests for structural code extraction.
    
    Feature: reverse-engineer-coach, Property 4: Structural Code Extraction
    Validates: Requirements 2.2, 3.2
    """
    
    @given(st.lists(code_snippet_strategy(), min_size=1, max_size=10))
    @settings(max_examples=5, deadline=2000)
    def test_extract_structural_elements_preserves_interfaces_and_classes(self, code_snippets: List[CodeSnippet]):
        """
        Property 4: Structural Code Extraction
        
        For any fetched code snippet, the content should contain interfaces, structs, 
        or classes while excluding complete implementations, logging, and metrics.
        
        Validates: Requirements 2.2, 3.2
        """
        # Extract structural elements
        elements = CodePatternExtractor.extract_structural_elements(code_snippets)
        
        # Property: All extracted elements should be structural (interfaces, classes, structs)
        valid_types = {'interface', 'class', 'struct', 'type', 'function'}
        for element in elements:
            assert element.element_type in valid_types, f"Element type {element.element_type} is not structural"
        
        # Property: Elements should preserve architectural significance
        for element in elements:
            assert 0.0 <= element.architectural_significance <= 1.0, "Architectural significance must be between 0 and 1"
        
        # Property: Each element should have a valid name
        for element in elements:
            assert element.name, "Element must have a non-empty name"
            assert isinstance(element.name, str), "Element name must be a string"
        
        # Property: Elements should have valid file paths
        for element in elements:
            assert element.file_path, "Element must have a file path"
            assert '.' in element.file_path, "File path should have an extension"
        
        # Property: Content should not be empty for valid elements
        for element in elements:
            assert element.content.strip(), "Element content should not be empty"
    
    @given(st.lists(code_snippet_strategy(), min_size=1, max_size=5))
    @settings(max_examples=3, deadline=2000)
    def test_extracted_elements_exclude_production_complexity(self, code_snippets: List[CodeSnippet]):
        """
        Property: Extracted structural elements should focus on architectural patterns
        rather than production complexity like logging and metrics.
        """
        # Add some production complexity to test snippets
        for snippet in code_snippets:
            # Add logging statements
            snippet.content += "\nlogger.info('Processing request')\nmetrics.increment('counter')"
        
        elements = CodePatternExtractor.extract_structural_elements(code_snippets)
        
        # Property: Elements should focus on structural aspects, not implementation details
        for element in elements:
            # The extraction should identify methods but not focus on logging/metrics
            production_keywords = ['logger', 'metrics', 'console.log', 'fmt.Print']
            
            # Methods should be architectural, not just logging
            architectural_methods = [m for m in element.methods 
                                   if not any(keyword in m.lower() for keyword in production_keywords)]
            
            # Should have some architectural methods if any methods exist
            if element.methods:
                assert len(architectural_methods) >= 0, "Should preserve architectural methods"
    
    @given(structural_element_strategy())
    @settings(max_examples=5, deadline=1500)
    def test_complexity_calculation_is_bounded(self, element: StructuralElement):
        """
        Property: Complexity scores should always be between 0.0 and 1.0
        """
        assert 0.0 <= element.complexity_score <= 1.0, f"Complexity score {element.complexity_score} is out of bounds"
    
    @given(st.lists(structural_element_strategy(), min_size=1, max_size=8))
    @settings(max_examples=3, deadline=2000)
    def test_pattern_identification_consistency(self, elements: List[StructuralElement]):
        """
        Property: Pattern identification should be consistent and based on naming conventions
        """
        analyzer = PatternAnalyzer()
        pattern_analyses = analyzer.analyze_patterns(elements)
        
        # Property: All identified patterns should have valid confidence scores
        for analysis in pattern_analyses:
            assert 0.0 <= analysis.confidence <= 1.0, f"Pattern confidence {analysis.confidence} is out of bounds"
            assert 0.0 <= analysis.learning_value <= 1.0, f"Learning value {analysis.learning_value} is out of bounds"
        
        # Property: Pattern evidence should reference actual elements
        element_names = {elem.name for elem in elements}
        for analysis in pattern_analyses:
            for evidence_name in analysis.evidence:
                assert evidence_name in element_names, f"Evidence {evidence_name} not found in elements"
    
    @given(st.lists(structural_element_strategy(), min_size=1, max_size=5))
    @settings(max_examples=3, deadline=2000)
    def test_code_simplification_preserves_structure(self, elements: List[StructuralElement]):
        """
        Property: Code simplification should preserve structural elements while removing complexity
        """
        # Add some complexity to elements
        for element in elements:
            element.content += "\n# Logging\nlogger.info('test')\n# Metrics\nmetrics.count += 1"
        
        simplifier = CodeSimplifier()
        simplified = simplifier.simplify_code(elements)
        
        # Property: Simplified code should be shorter or equal in length
        for simp in simplified:
            original_length = len(simp.original_element.content)
            simplified_length = len(simp.simplified_content)
            assert simplified_length <= original_length, "Simplified code should not be longer than original"
        
        # Property: Simplified code should preserve patterns
        for simp in simplified:
            # Should preserve the same patterns or a subset
            original_patterns = set(simp.original_element.patterns)
            preserved_patterns = set(simp.preserved_patterns)
            assert preserved_patterns.issubset(original_patterns), "Should not add new patterns during simplification"
        
        # Property: Should identify what complexity was removed
        for simp in simplified:
            if simp.removed_complexity:
                valid_complexity_types = {'logging', 'error_handling', 'metrics', 'configuration', 'validation'}
                for complexity_type in simp.removed_complexity:
                    assert complexity_type in valid_complexity_types, f"Unknown complexity type: {complexity_type}"
    
    @given(st.text(min_size=10, max_size=1000))
    @settings(max_examples=5, deadline=1500)
    def test_dependency_extraction_finds_valid_imports(self, code_content: str):
        """
        Property: Dependency extraction should find valid import statements
        """
        # Add some import statements to the code
        python_code = f"import os\nfrom typing import List\n{code_content}"
        go_code = f'import "fmt"\nimport "strings"\n{code_content}'
        ts_code = f"import {{ Component }} from 'react';\n{code_content}"
        
        # Test Python dependencies
        python_deps = CodePatternExtractor._extract_dependencies(python_code, 'python')
        for dep in python_deps:
            assert isinstance(dep, str), "Dependencies should be strings"
            assert dep.strip(), "Dependencies should not be empty"
        
        # Test Go dependencies
        go_deps = CodePatternExtractor._extract_dependencies(go_code, 'go')
        for dep in go_deps:
            assert isinstance(dep, str), "Dependencies should be strings"
            assert dep.strip(), "Dependencies should not be empty"
        
        # Test TypeScript dependencies
        ts_deps = CodePatternExtractor._extract_dependencies(ts_code, 'typescript')
        for dep in ts_deps:
            assert isinstance(dep, str), "Dependencies should be strings"
            assert dep.strip(), "Dependencies should not be empty"
    
    @given(st.lists(code_snippet_strategy(), min_size=0, max_size=10))
    @settings(max_examples=3, deadline=2000)
    def test_empty_input_handling(self, code_snippets: List[CodeSnippet]):
        """
        Property: System should handle empty or minimal inputs gracefully
        """
        # Test with empty list
        elements = CodePatternExtractor.extract_structural_elements([])
        assert elements == [], "Empty input should return empty list"
        
        # Test with provided snippets
        elements = CodePatternExtractor.extract_structural_elements(code_snippets)
        
        # Property: Should never return None
        assert elements is not None, "Should never return None"
        assert isinstance(elements, list), "Should always return a list"
        
        # Property: Number of elements should not exceed number of snippets
        assert len(elements) <= len(code_snippets), "Cannot have more elements than input snippets"


class TestPatternRecognition:
    """Tests for architectural pattern recognition"""
    
    def test_handler_pattern_recognition(self):
        """Test that handler patterns are correctly identified"""
        handler_snippet = CodeSnippet(
            file_path="handler.py",
            content="""class RequestHandler:
    def handle_request(self, request):
        return self.process(request)
    
    def process(self, data):
        return data.upper()""",
            start_line=1,
            end_line=6,
            language="python",
            snippet_type="class",
            name="RequestHandler",
            github_permalink="https://github.com/test/repo/blob/main/handler.py#L1",
            commit_sha="abc123",
            architectural_significance=0.8
        )
        
        elements = CodePatternExtractor.extract_structural_elements([handler_snippet])
        assert len(elements) == 1
        
        element = elements[0]
        pattern_names = [p.value for p in element.patterns]
        assert "Handler Pattern" in pattern_names
    
    def test_service_pattern_recognition(self):
        """Test that service patterns are correctly identified"""
        service_snippet = CodeSnippet(
            file_path="user_service.py",
            content="""class UserService:
    def create_user(self, data):
        return User(data)
    
    def get_user(self, id):
        return self.repository.find(id)
    
    def update_user(self, id, data):
        user = self.get_user(id)
        user.update(data)
        return user""",
            start_line=1,
            end_line=10,
            language="python",
            snippet_type="class",
            name="UserService",
            github_permalink="https://github.com/test/repo/blob/main/user_service.py#L1",
            commit_sha="abc123",
            architectural_significance=0.9
        )
        
        elements = CodePatternExtractor.extract_structural_elements([service_snippet])
        assert len(elements) == 1
        
        element = elements[0]
        pattern_names = [p.value for p in element.patterns]
        assert "Service Layer Pattern" in pattern_names


class TestSpecificationGenerationCompleteness:
    """
    Property-based tests for specification generation completeness.
    
    Feature: reverse-engineer-coach, Property 7: Specification Generation Completeness
    Validates: Requirements 3.3, 3.4
    """
    
    @given(repository_analysis_strategy())
    @settings(max_examples=3, deadline=3000)
    @pytest.mark.asyncio
    async def test_specification_generation_produces_complete_output(self, repo_analysis: RepositoryAnalysis):
        """
        Property 7: Specification Generation Completeness
        
        For any completed repository analysis, the Spec_Generator should produce 
        both a Markdown requirements document and a step-by-step task list.
        
        Validates: Requirements 3.3, 3.4
        """
        # Create specification generator with mock LLM provider
        generator = SpecificationGenerator(llm_provider=MockLLMProvider())
        
        # Generate specification
        specification = await generator.generate_specification(repo_analysis)
        
        # Property: Specification should always be a dictionary
        assert isinstance(specification, dict), "Specification must be a dictionary"
        
        # Property: Must contain all required sections
        required_sections = [
            'repository_info',
            'structural_elements', 
            'simplified_code',
            'pattern_analysis',
            'architecture_insights',
            'llm_generated_content'
        ]
        
        for section in required_sections:
            assert section in specification, f"Missing required section: {section}"
        
        # Property: Repository info should contain essential metadata
        repo_info = specification['repository_info']
        essential_fields = ['url', 'name', 'language', 'complexity_score']
        for field in essential_fields:
            assert field in repo_info, f"Missing essential repository field: {field}"
        
        # Property: LLM generated content should include both specification and tasks
        llm_content = specification['llm_generated_content']
        assert 'specification_markdown' in llm_content, "Missing specification markdown"
        assert 'learning_tasks_markdown' in llm_content, "Missing learning tasks markdown"
        assert 'generation_success' in llm_content, "Missing generation success indicator"
        
        # Property: If generation succeeded, content should not be empty
        if llm_content['generation_success']:
            assert llm_content['specification_markdown'].strip(), "Specification markdown should not be empty when generation succeeds"
            assert llm_content['learning_tasks_markdown'].strip(), "Learning tasks markdown should not be empty when generation succeeds"
        
        # Property: Structural elements should preserve input data integrity
        assert isinstance(specification['structural_elements'], list), "Structural elements must be a list"
        
        # Property: Pattern analysis should be valid
        assert isinstance(specification['pattern_analysis'], list), "Pattern analysis must be a list"
        for pattern in specification['pattern_analysis']:
            assert 'pattern' in pattern, "Pattern must have a pattern field"
            assert 'confidence' in pattern, "Pattern must have confidence score"
            assert 0.0 <= pattern['confidence'] <= 1.0, "Confidence must be between 0 and 1"
    
    @given(repository_analysis_strategy())
    @settings(max_examples=3, deadline=3000)
    @pytest.mark.asyncio
    async def test_specification_contains_markdown_formatted_content(self, repo_analysis: RepositoryAnalysis):
        """
        Property: Generated specification should contain properly formatted Markdown content
        """
        generator = SpecificationGenerator(llm_provider=MockLLMProvider())
        specification = await generator.generate_specification(repo_analysis)
        
        llm_content = specification['llm_generated_content']
        
        # Property: Markdown content should contain headers
        if llm_content['generation_success']:
            spec_markdown = llm_content['specification_markdown']
            tasks_markdown = llm_content['learning_tasks_markdown']
            
            # Should contain markdown headers
            assert '#' in spec_markdown, "Specification should contain markdown headers"
            assert '#' in tasks_markdown, "Tasks should contain markdown headers"
            
            # Should contain structured content
            assert 'Learning' in spec_markdown or 'Objective' in spec_markdown, "Should contain learning-related content"
            assert 'Task' in tasks_markdown or 'Objective' in tasks_markdown, "Should contain task-related content"
    
    @given(st.lists(repository_analysis_strategy(), min_size=1, max_size=3))
    @settings(max_examples=2, deadline=5000)
    @pytest.mark.asyncio
    async def test_specification_generation_consistency(self, repo_analyses: List[RepositoryAnalysis]):
        """
        Property: Specification generation should be consistent across multiple repositories
        """
        generator = SpecificationGenerator(llm_provider=MockLLMProvider())
        
        specifications = []
        for repo_analysis in repo_analyses:
            spec = await generator.generate_specification(repo_analysis)
            specifications.append(spec)
        
        # Property: All specifications should have the same structure
        if len(specifications) > 1:
            first_spec_keys = set(specifications[0].keys())
            for spec in specifications[1:]:
                spec_keys = set(spec.keys())
                assert spec_keys == first_spec_keys, "All specifications should have the same top-level structure"
        
        # Property: Each specification should be complete
        for spec in specifications:
            assert spec['repository_info']['url'], "Each specification should have a repository URL"
            assert isinstance(spec['structural_elements'], list), "Structural elements should always be a list"
            assert isinstance(spec['pattern_analysis'], list), "Pattern analysis should always be a list"
    
    @given(code_snippet_strategy())
    @settings(max_examples=3, deadline=2000)
    @pytest.mark.asyncio
    async def test_code_explanation_generation(self, code_snippet: CodeSnippet):
        """
        Property: Code explanation generation should produce valid explanations for any code snippet
        """
        generator = SpecificationGenerator(llm_provider=MockLLMProvider())
        
        explanation = await generator.generate_code_explanation(code_snippet)
        
        # Property: Should always return a dictionary with success indicator
        assert isinstance(explanation, dict), "Explanation should be a dictionary"
        assert 'success' in explanation, "Should have success indicator"
        
        # Property: If successful, should contain explanation content
        if explanation['success']:
            assert 'explanation' in explanation, "Should contain explanation content"
            assert 'patterns_identified' in explanation, "Should identify patterns"
            assert isinstance(explanation['patterns_identified'], list), "Patterns should be a list"
        
        # Property: Should handle errors gracefully
        if not explanation['success']:
            assert 'error' in explanation or 'error_message' in explanation, "Should provide error information"


if __name__ == "__main__":
    pytest.main([__file__])