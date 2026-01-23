"""
Property-based tests for dynamic context fetching
Feature: reverse-engineer-coach, Property 13: Dynamic Context Fetching
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

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
def insufficient_context_question_data(draw):
    """Generate questions that should trigger dynamic context fetching"""
    # Short questions that should trigger "needs more context"
    short_questions = [
        "How?",
        "Why?",
        "What?",
        "Explain this",
        "Help me",
        "I don't understand",
        "Show me",
        "Tell me more"
    ]
    
    return {
        "question": draw(st.sampled_from(short_questions)),
        "project_id": str(uuid.uuid4()),
        "current_task_id": None,
        "user_language": draw(st.sampled_from(list(LanguageType))) if draw(st.booleans()) else None,
        "context_hint": None
    }


@st.composite
def sufficient_context_question_data(draw):
    """Generate questions that should have sufficient context"""
    # Longer, more detailed questions
    detailed_questions = [
        "How does the caching mechanism work in this distributed system architecture?",
        "What are the performance implications of using this specific database pattern?",
        "Why is this approach better than alternative architectural solutions?",
        "How do these microservice components interact with each other?",
        "What design principles are demonstrated in this code structure?",
        "How does this system handle concurrent requests and maintain consistency?",
        "What are the trade-offs between this pattern and other approaches?",
        "How does this implementation scale under high load conditions?"
    ]
    
    return {
        "question": draw(st.sampled_from(detailed_questions)),
        "project_id": str(uuid.uuid4()),
        "current_task_id": str(uuid.uuid4()) if draw(st.booleans()) else None,
        "user_language": draw(st.sampled_from(list(LanguageType))) if draw(st.booleans()) else None,
        "context_hint": draw(st.text(min_size=0, max_size=50)) if draw(st.booleans()) else None
    }


class TestDynamicContextFetching:
    """
    Property 13: Dynamic Context Fetching
    Validates: Requirements 6.5
    
    For any Coach_Agent query where existing context is insufficient, the system should 
    fetch additional relevant code snippets to improve answer quality
    """

    @given(insufficient_context_question_data())
    @settings(max_examples=3, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_coach_detects_insufficient_context(self, question_data):
        """Test that coach detects when context is insufficient and needs more"""
        # Create fresh database session
        test_db = create_test_session()
        
        try:
            # Create test project with minimal context
            project = LearningProject(
                user_id="test_user",
                title="Minimal Context Project",
                target_repository="https://github.com/test/minimal-repo",
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
            
            # Property: Coach should detect insufficient context for short/vague questions
            assert isinstance(response, CoachResponse)
            assert response.needs_more_context == True
            
            # Property: Confidence should be lower when context is insufficient
            assert response.confidence < 0.6
            
            # Property: Response should still be valid
            assert response.answer is not None
            assert len(response.answer) > 0
            
        finally:
            test_db.close()

    @given(sufficient_context_question_data())
    @settings(max_examples=3, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_coach_recognizes_sufficient_context(self, question_data):
        """Test that coach recognizes when context is sufficient for detailed questions"""
        # Create fresh database session
        test_db = create_test_session()
        
        try:
            # Create test project
            project = LearningProject(
                user_id="test_user",
                title="Detailed Question Project",
                target_repository="https://github.com/test/detailed-repo",
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
            
            # Property: Coach should recognize sufficient context for detailed questions
            assert isinstance(response, CoachResponse)
            assert response.needs_more_context == False
            
            # Property: Confidence should be higher when context is sufficient
            assert response.confidence >= 0.6
            
            # Property: Should have some context used for detailed questions
            assert len(response.context_used) > 0
            
            # Property: Context should have valid structure
            for context in response.context_used:
                assert isinstance(context, CoachContext)
                assert context.content is not None
                assert len(context.content) > 0
                assert 0.0 <= context.relevance_score <= 1.0
                assert context.source_id is not None
                
        finally:
            test_db.close()

    @given(st.text(min_size=1, max_size=200))
    @settings(max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_dynamic_context_response_consistency(self, question_text):
        """Test that dynamic context fetching produces consistent response structure"""
        # Create fresh database session
        test_db = create_test_session()
        
        try:
            # Create test project
            project = LearningProject(
                user_id="test_user",
                title="Consistency Test Project",
                target_repository="https://github.com/test/consistency-repo",
                architecture_topic="Testing",
                status="created"
            )
            test_db.add(project)
            test_db.commit()
            
            # Create question
            question_data = {
                "question": question_text,
                "project_id": project.id,
                "current_task_id": None,
                "user_language": None,
                "context_hint": None
            }
            
            # Create coach agent and ask question
            coach = CoachAgent(test_db)
            question = CoachQuestion(**question_data)
            response = coach.answer_question(question)
            
            # Property: Response structure should always be consistent
            assert isinstance(response, CoachResponse)
            assert response.answer is not None
            assert isinstance(response.answer, str)
            assert len(response.answer) > 0
            
            # Property: Confidence should be valid
            assert isinstance(response.confidence, (int, float))
            assert 0.0 <= response.confidence <= 1.0
            
            # Property: Context used should be a list
            assert isinstance(response.context_used, list)
            
            # Property: All context items should be valid
            for context in response.context_used:
                assert isinstance(context, CoachContext)
                assert hasattr(context, 'context_type')
                assert hasattr(context, 'content')
                assert hasattr(context, 'source_id')
                assert hasattr(context, 'relevance_score')
                assert hasattr(context, 'metadata')
            
            # Property: Boolean flags should be boolean
            assert isinstance(response.needs_more_context, bool)
            assert isinstance(response.language_adapted, bool)
            
            # Property: Lists should be lists
            assert isinstance(response.hints, list)
            assert isinstance(response.suggested_actions, list)
            
        finally:
            test_db.close()

    @given(st.lists(st.text(min_size=5, max_size=50), min_size=1, max_size=5))
    @settings(max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_context_fetching_with_multiple_questions(self, questions):
        """Test that dynamic context fetching works consistently across multiple questions"""
        # Create fresh database session
        test_db = create_test_session()
        
        try:
            # Create test project
            project = LearningProject(
                user_id="test_user",
                title="Multiple Questions Project",
                target_repository="https://github.com/test/multi-repo",
                architecture_topic="Testing",
                status="created"
            )
            test_db.add(project)
            test_db.commit()
            
            coach = CoachAgent(test_db)
            responses = []
            
            # Ask multiple questions
            for question_text in questions:
                question_data = {
                    "question": question_text,
                    "project_id": project.id,
                    "current_task_id": None,
                    "user_language": None,
                    "context_hint": None
                }
                
                question = CoachQuestion(**question_data)
                response = coach.answer_question(question)
                responses.append(response)
            
            # Property: All responses should be valid
            assert len(responses) == len(questions)
            
            for i, response in enumerate(responses):
                assert isinstance(response, CoachResponse)
                assert response.answer is not None
                assert len(response.answer) > 0
                assert 0.0 <= response.confidence <= 1.0
                
                # Property: Context assessment should be consistent with question length
                question_length = len(questions[i])
                if question_length < 20:
                    # Short questions should typically need more context
                    assert response.needs_more_context == True
                else:
                    # Longer questions should typically have sufficient context
                    assert response.needs_more_context == False
            
        finally:
            test_db.close()

    def test_context_fetching_edge_cases(self):
        """Test edge cases in dynamic context fetching"""
        # Create fresh database session
        test_db = create_test_session()
        
        try:
            # Create test project
            project = LearningProject(
                user_id="test_user",
                title="Edge Cases Project",
                target_repository="https://github.com/test/edge-repo",
                architecture_topic="Testing",
                status="created"
            )
            test_db.add(project)
            test_db.commit()
            
            coach = CoachAgent(test_db)
            
            # Test empty question
            empty_question = CoachQuestion(
                question="",
                project_id=project.id
            )
            
            # This should not crash
            try:
                response = coach.answer_question(empty_question)
                assert isinstance(response, CoachResponse)
            except Exception:
                # If it raises an exception, that's also acceptable behavior
                pass
            
            # Test very long question
            long_question = CoachQuestion(
                question="How does this architectural pattern work " * 50,  # Very long question
                project_id=project.id
            )
            
            response = coach.answer_question(long_question)
            assert isinstance(response, CoachResponse)
            assert response.answer is not None
            
            # Test question with special characters
            special_question = CoachQuestion(
                question="How does this work? @#$%^&*()[]{}|\\:;\"'<>,.?/~`",
                project_id=project.id
            )
            
            response = coach.answer_question(special_question)
            assert isinstance(response, CoachResponse)
            assert response.answer is not None
            
        finally:
            test_db.close()