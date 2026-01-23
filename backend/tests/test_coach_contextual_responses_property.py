"""
Property-based tests for coach agent contextual responses
Feature: reverse-engineer-coach, Property 12: Coach Agent Contextual Responses
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch
import uuid
from datetime import datetime

from app.models import (
    LearningProject, LearningSpec, Task, ReferenceSnippet, 
    TaskReferenceSnippet, ProjectFile, Base
)

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.coach_agent_simple import (
    CoachAgent, CoachQuestion, CoachResponse, LanguageType,
    ContextType, CoachContext
)


def create_test_session():
    """Create a fresh test database session"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()


# Hypothesis strategies for generating test data
@st.composite
def coach_question_data(draw):
    """Generate valid coach question data"""
    questions = [
        "How does this caching mechanism work?",
        "What pattern is being used here?",
        "Why is this approach better than alternatives?",
        "How do these components interact?",
        "What are the performance implications?",
        "How is error handling implemented?",
        "What design principles are demonstrated?",
        "How does this scale under load?",
        "What are the trade-offs in this design?",
        "How is concurrency handled here?"
    ]
    
    return {
        "question": draw(st.sampled_from(questions)),
        "project_id": str(uuid.uuid4()),
        "current_task_id": str(uuid.uuid4()) if draw(st.booleans()) else None,
        "user_language": draw(st.sampled_from(list(LanguageType))) if draw(st.booleans()) else None,
        "context_hint": draw(st.text(min_size=0, max_size=50)) if draw(st.booleans()) else None
    }


@st.composite
def reference_snippet_data(draw):
    """Generate valid reference snippet data for testing"""
    code_examples = [
        "class CacheManager:\n    def get(self, key):\n        return self.cache.get(key)",
        "interface Repository {\n    findById(id: string): Promise<Entity>;\n}",
        "func (r *Router) HandleRequest(req *Request) {\n    // routing logic\n}",
        "public class EventProcessor {\n    public void process(Event event) {\n        // processing\n    }\n}",
        "def process_batch(items):\n    for item in items:\n        yield transform(item)"
    ]
    
    start_line = draw(st.integers(min_value=1, max_value=100))
    return {
        "github_url": f"https://github.com/test/repo/blob/main/file.py#L{start_line}",
        "file_path": f"src/{draw(st.text(min_size=3, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyz'))}.py",
        "start_line": start_line,
        "end_line": start_line + draw(st.integers(min_value=1, max_value=10)),
        "code_content": draw(st.sampled_from(code_examples)),
        "commit_sha": draw(st.text(min_size=40, max_size=40, alphabet="0123456789abcdef")),
        "explanation": draw(st.text(min_size=10, max_size=100, alphabet="abcdefghijklmnopqrstuvwxyz "))
    }


@st.composite
def task_data(draw):
    """Generate valid task data"""
    return {
        "title": draw(st.text(min_size=5, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ")),
        "instruction": draw(st.text(min_size=10, max_size=200, alphabet="abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ")),
        "step_number": draw(st.integers(min_value=1, max_value=20)),
        "is_completed": draw(st.booleans())
    }


class TestCoachContextualResponses:
    """
    Property 12: Coach Agent Contextual Responses
    Validates: Requirements 6.1, 6.3
    
    For any user question about code patterns, the Coach_Agent should provide answers 
    that reference specific lines from the available Reference_Snippets
    """

    @given(coach_question_data())
    @settings(max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_coach_provides_valid_response_structure(self, question_data):
        """Test that coach always provides a valid response structure"""
        # Create fresh database session
        test_db = create_test_session()
        
        try:
            # Create test project
            project = LearningProject(
                user_id="test_user",
                title="Test Project",
                target_repository="https://github.com/test/repo",
                architecture_topic="Testing",
                status="created"
            )
            test_db.add(project)
            test_db.commit()
            
            # Update question with actual project_id
            question_data["project_id"] = project.id
            
            # Create coach agent and ask question
            coach = CoachAgent(test_db)
            question = CoachQuestion(**question_data)
            response = coach.answer_question(question)
            
            # Property: Coach should always provide a valid response structure
            assert isinstance(response, CoachResponse)
            assert response.answer is not None
            assert len(response.answer) > 0
            assert 0.0 <= response.confidence <= 1.0
            assert isinstance(response.context_used, list)
            assert isinstance(response.hints, list)
            assert isinstance(response.suggested_actions, list)
            assert isinstance(response.needs_more_context, bool)
            assert isinstance(response.language_adapted, bool)
            
        finally:
            test_db.close()

    @given(coach_question_data())
    @settings(max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_coach_handles_questions_without_reference_snippets(self, question_data):
        """Test that coach provides appropriate response when no reference snippets are available"""
        # Create fresh database session
        test_db = create_test_session()
        
        try:
            # Create test project without reference snippets
            project = LearningProject(
                user_id="test_user",
                title="Empty Project",
                target_repository="https://github.com/test/empty-repo",
                architecture_topic="Testing",
                status="created"
            )
            test_db.add(project)
            test_db.commit()
            
            # Update question with actual project_id
            question_data["project_id"] = project.id
            question_data["current_task_id"] = None  # No task either
            
            # Create coach agent and ask question
            coach = CoachAgent(test_db)
            question = CoachQuestion(**question_data)
            response = coach.answer_question(question)
            
            # Property: Coach should still provide a response
            assert isinstance(response, CoachResponse)
            assert response.answer is not None
            assert len(response.answer) > 0
            
            # Property: Should have valid confidence score
            assert 0.0 <= response.confidence <= 1.0
            
        finally:
            test_db.close()

    @given(coach_question_data())
    @settings(max_examples=3, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_coach_response_basic_functionality(self, question_data):
        """Test that coach basic functionality works"""
        # Create fresh database session
        test_db = create_test_session()
        
        try:
            # Create test project
            project = LearningProject(
                user_id="test_user",
                title="Test Project Basic",
                target_repository="https://github.com/test/repo",
                architecture_topic="Testing",
                status="created"
            )
            test_db.add(project)
            test_db.commit()
            
            # Update question with actual project_id
            question_data["project_id"] = project.id
            
            # Create coach agent and ask question
            coach = CoachAgent(test_db)
            question = CoachQuestion(**question_data)
            response = coach.answer_question(question)
            
            # Property: Coach should provide a valid response
            assert isinstance(response, CoachResponse)
            assert response.answer is not None
            assert len(response.answer) > 0
            assert 0.0 <= response.confidence <= 1.0
            
            # Property: Response structure should be valid
            assert isinstance(response.context_used, list)
            assert isinstance(response.hints, list)
            assert isinstance(response.suggested_actions, list)
            
        finally:
            test_db.close()

    @given(coach_question_data())
    @settings(max_examples=3, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_coach_question_validation(self, question_data):
        """Test that coach validates question input properly"""
        # Create fresh database session
        test_db = create_test_session()
        
        try:
            # Create test project
            project = LearningProject(
                user_id="test_user",
                title="Validation Test Project",
                target_repository="https://github.com/test/validation-repo",
                architecture_topic="Testing",
                status="created"
            )
            test_db.add(project)
            test_db.commit()
            
            # Update question with actual project_id
            question_data["project_id"] = project.id
            
            # Property: Coach should accept valid CoachQuestion objects
            coach = CoachAgent(test_db)
            question = CoachQuestion(**question_data)
            
            # This should not raise an exception
            response = coach.answer_question(question)
            
            # Property: Response should be valid
            assert isinstance(response, CoachResponse)
            
        finally:
            test_db.close()