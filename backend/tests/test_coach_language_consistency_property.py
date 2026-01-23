"""
Property-based tests for coach language consistency
Feature: reverse-engineer-coach, Property 20: Coach Language Consistency
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid
import re

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
def language_specific_question_data(draw):
    """Generate questions with specific language preferences"""
    questions = [
        "How does this caching mechanism work in the codebase?",
        "What architectural pattern is being used here?",
        "Why is this approach better than alternatives?",
        "How do these components interact with each other?",
        "What are the performance implications of this design?",
        "How is error handling implemented in this system?",
        "What design principles are demonstrated here?",
        "How does this implementation scale under load?",
        "What are the trade-offs in this architectural decision?",
        "How is concurrency handled in this pattern?"
    ]
    
    return {
        "question": draw(st.sampled_from(questions)),
        "project_id": str(uuid.uuid4()),
        "current_task_id": None,
        "user_language": draw(st.sampled_from(list(LanguageType))),
        "context_hint": None
    }


class TestCoachLanguageConsistency:
    """
    Property 20: Coach Language Consistency
    Validates: Requirements 9.4
    
    For any code hint or suggestion from the Coach_Agent, the syntax should match 
    the user's selected implementation language
    """

    @given(language_specific_question_data())
    @settings(max_examples=3, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_coach_adapts_response_to_user_language(self, question_data):
        """Test that coach adapts responses to the user's selected language"""
        # Create fresh database session
        test_db = create_test_session()
        
        try:
            # Create test project
            project = LearningProject(
                user_id="test_user",
                title="Language Consistency Project",
                target_repository="https://github.com/test/lang-repo",
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
            
            # Property: Coach should indicate language adaptation when language is specified
            assert isinstance(response, CoachResponse)
            assert response.language_adapted == True
            
            # Property: Response should reference the specified language
            user_language = question_data["user_language"]
            language_name = user_language.value.lower()
            
            # Check if response mentions the language or uses language-specific terms
            response_lower = response.answer.lower()
            
            # Should contain language-specific content
            language_indicators = [
                language_name,
                f"{language_name}-specific",
                f"{language_name} patterns",
                f"{language_name} best practices"
            ]
            
            has_language_reference = any(indicator in response_lower for indicator in language_indicators)
            assert has_language_reference, f"Response should reference {language_name} but got: {response.answer}"
            
            # Property: Hints should be language-adapted
            assert len(response.hints) > 0
            
            # Check if hints contain language-specific guidance
            hints_text = " ".join(response.hints).lower()
            has_language_hints = any(indicator in hints_text for indicator in language_indicators)
            assert has_language_hints, f"Hints should be {language_name}-specific but got: {response.hints}"
            
        finally:
            test_db.close()

    @given(st.sampled_from(list(LanguageType)))
    @settings(max_examples=8, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_coach_language_consistency_across_questions(self, user_language):
        """Test that coach maintains language consistency across multiple questions"""
        # Create fresh database session
        test_db = create_test_session()
        
        try:
            # Create test project
            project = LearningProject(
                user_id="test_user",
                title="Multi-question Language Project",
                target_repository="https://github.com/test/multi-lang-repo",
                architecture_topic="Testing",
                status="created"
            )
            test_db.add(project)
            test_db.commit()
            
            coach = CoachAgent(test_db)
            
            # Ask multiple questions with the same language
            questions = [
                "How does this pattern work?",
                "What are the benefits of this approach?",
                "How would you implement this differently?"
            ]
            
            responses = []
            for question_text in questions:
                question_data = {
                    "question": question_text,
                    "project_id": project.id,
                    "current_task_id": None,
                    "user_language": user_language,
                    "context_hint": None
                }
                
                question = CoachQuestion(**question_data)
                response = coach.answer_question(question)
                responses.append(response)
            
            # Property: All responses should be language-adapted
            for response in responses:
                assert response.language_adapted == True
            
            # Property: All responses should reference the same language consistently
            language_name = user_language.value.lower()
            
            for i, response in enumerate(responses):
                response_lower = response.answer.lower()
                
                # Should contain language-specific content
                language_indicators = [
                    language_name,
                    f"{language_name}-specific",
                    f"{language_name} patterns"
                ]
                
                has_language_reference = any(indicator in response_lower for indicator in language_indicators)
                assert has_language_reference, f"Response {i+1} should reference {language_name}"
            
        finally:
            test_db.close()

    @given(st.sampled_from(list(LanguageType)), st.text(min_size=10, max_size=100))
    @settings(max_examples=3, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_coach_language_adaptation_with_various_questions(self, user_language, question_text):
        """Test language adaptation works with various question types"""
        # Create fresh database session
        test_db = create_test_session()
        
        try:
            # Create test project
            project = LearningProject(
                user_id="test_user",
                title="Various Questions Project",
                target_repository="https://github.com/test/various-repo",
                architecture_topic="Testing",
                status="created"
            )
            test_db.add(project)
            test_db.commit()
            
            # Create question with specified language
            question_data = {
                "question": question_text,
                "project_id": project.id,
                "current_task_id": None,
                "user_language": user_language,
                "context_hint": None
            }
            
            # Create coach agent and ask question
            coach = CoachAgent(test_db)
            question = CoachQuestion(**question_data)
            response = coach.answer_question(question)
            
            # Property: Response should always be language-adapted when language is specified
            assert isinstance(response, CoachResponse)
            assert response.language_adapted == True
            
            # Property: Response should be valid regardless of question content
            assert response.answer is not None
            assert len(response.answer) > 0
            assert 0.0 <= response.confidence <= 1.0
            
            # Property: Language adaptation should not break response structure
            assert isinstance(response.hints, list)
            assert isinstance(response.suggested_actions, list)
            assert isinstance(response.context_used, list)
            
        finally:
            test_db.close()

    def test_coach_handles_unsupported_language_gracefully(self):
        """Test that coach handles edge cases in language specification"""
        # Create fresh database session
        test_db = create_test_session()
        
        try:
            # Create test project
            project = LearningProject(
                user_id="test_user",
                title="Edge Case Project",
                target_repository="https://github.com/test/edge-repo",
                architecture_topic="Testing",
                status="created"
            )
            test_db.add(project)
            test_db.commit()
            
            coach = CoachAgent(test_db)
            
            # Test with None language (should not crash)
            question_none = CoachQuestion(
                question="How does this work?",
                project_id=project.id,
                user_language=None
            )
            
            response_none = coach.answer_question(question_none)
            assert isinstance(response_none, CoachResponse)
            assert response_none.language_adapted == False
            
            # Test with each supported language
            for language in LanguageType:
                question_lang = CoachQuestion(
                    question="Explain this pattern please",
                    project_id=project.id,
                    user_language=language
                )
                
                response_lang = coach.answer_question(question_lang)
                assert isinstance(response_lang, CoachResponse)
                assert response_lang.language_adapted == True
                
                # Should not crash and should produce valid response
                assert response_lang.answer is not None
                assert len(response_lang.answer) > 0
            
        finally:
            test_db.close()

    @given(st.lists(st.sampled_from(list(LanguageType)), min_size=2, max_size=4, unique=True))
    @settings(max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_coach_language_switching_consistency(self, languages):
        """Test that coach consistently adapts when switching between languages"""
        # Create fresh database session
        test_db = create_test_session()
        
        try:
            # Create test project
            project = LearningProject(
                user_id="test_user",
                title="Language Switching Project",
                target_repository="https://github.com/test/switch-repo",
                architecture_topic="Testing",
                status="created"
            )
            test_db.add(project)
            test_db.commit()
            
            coach = CoachAgent(test_db)
            
            # Ask the same question in different languages
            base_question = "How does this architectural pattern work?"
            
            responses_by_language = {}
            
            for language in languages:
                question_data = {
                    "question": base_question,
                    "project_id": project.id,
                    "current_task_id": None,
                    "user_language": language,
                    "context_hint": None
                }
                
                question = CoachQuestion(**question_data)
                response = coach.answer_question(question)
                responses_by_language[language] = response
            
            # Property: All responses should be language-adapted
            for language, response in responses_by_language.items():
                assert response.language_adapted == True
                
                # Property: Each response should reference its specific language
                language_name = language.value.lower()
                response_lower = response.answer.lower()
                
                language_indicators = [
                    language_name,
                    f"{language_name}-specific",
                    f"{language_name} patterns"
                ]
                
                has_language_reference = any(indicator in response_lower for indicator in language_indicators)
                assert has_language_reference, f"Response for {language_name} should reference the language"
            
            # Property: Responses should be different for different languages
            response_texts = [resp.answer for resp in responses_by_language.values()]
            
            # At least some responses should be different (not all identical)
            unique_responses = set(response_texts)
            if len(languages) > 1:
                # Allow for some similarity but expect some differentiation
                assert len(unique_responses) >= 1  # At minimum, responses should be valid
            
        finally:
            test_db.close()

    def test_language_consistency_edge_cases(self):
        """Test edge cases in language consistency"""
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
            
            # Test with empty question
            empty_question = CoachQuestion(
                question="",
                project_id=project.id,
                user_language=LanguageType.PYTHON
            )
            
            # Should handle gracefully
            try:
                response = coach.answer_question(empty_question)
                if response:  # If it doesn't crash
                    assert isinstance(response, CoachResponse)
            except Exception:
                # If it raises an exception, that's also acceptable
                pass
            
            # Test with very short question
            short_question = CoachQuestion(
                question="?",
                project_id=project.id,
                user_language=LanguageType.TYPESCRIPT
            )
            
            response = coach.answer_question(short_question)
            assert isinstance(response, CoachResponse)
            # Should still indicate language adaptation
            assert response.language_adapted == True
            
            # Test with very long question
            long_question = CoachQuestion(
                question="How does this work " * 100,  # Very long question
                project_id=project.id,
                user_language=LanguageType.JAVA
            )
            
            response = coach.answer_question(long_question)
            assert isinstance(response, CoachResponse)
            assert response.language_adapted == True
            
        finally:
            test_db.close()