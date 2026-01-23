"""
Simple AI Coach Agent for testing
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.orm import Session


class ContextType(Enum):
    """Types of context available to the coach"""
    REFERENCE_SNIPPET = "reference_snippet"
    PROJECT_FILE = "project_file"
    TASK_INSTRUCTION = "task_instruction"
    ARCHITECTURAL_PATTERN = "architectural_pattern"


class LanguageType(Enum):
    """Supported programming languages for coaching"""
    TYPESCRIPT = "typescript"
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    CPP = "cpp"
    CSHARP = "csharp"


@dataclass
class CoachContext:
    """Context information for coach responses"""
    context_type: ContextType
    content: str
    source_id: str
    relevance_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoachQuestion:
    """User question with context"""
    question: str
    project_id: str
    current_task_id: Optional[str] = None
    user_language: Optional[LanguageType] = None
    context_hint: Optional[str] = None


@dataclass
class CoachResponse:
    """Coach agent response"""
    answer: str
    confidence: float  # 0.0 to 1.0
    context_used: List[CoachContext]
    hints: List[str] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    needs_more_context: bool = False
    language_adapted: bool = False


class CoachAgent:
    """Enhanced coach agent with user-specific credentials support"""
    
    def __init__(self, db: Session, user_id: Optional[str] = None):
        self.db = db
        self.user_id = user_id
    
    def answer_question(self, question: CoachQuestion) -> CoachResponse:
        """Answer a user question with contextual information and user-specific personalization"""
        
        # Simple implementation with user-specific context
        needs_more_context = len(question.question) < 20  # Simple heuristic
        
        # Apply user-specific language preferences if available
        effective_language = question.user_language
        if self.user_id and not effective_language:
            effective_language = self._get_user_preferred_language()
        
        # Simulate language adaptation
        language_adapted = effective_language is not None
        answer_text = "This is a personalized response with user-specific context handling"
        
        if language_adapted:
            # Simulate language-specific response
            lang_name = effective_language.value
            answer_text = f"This is a {lang_name}-specific response adapted for your preferences"
        
        # Add user context to response
        user_context = self._get_user_context()
        if user_context:
            answer_text += f" (Personalized for {user_context.get('language', 'your')} development)"
        
        # Simulate dynamic context fetching
        context_used = []
        if not needs_more_context:
            # Simulate having found some context
            context_used = [
                CoachContext(
                    context_type=ContextType.REFERENCE_SNIPPET,
                    content="Sample code context with user-specific relevance",
                    source_id="test-snippet-1",
                    relevance_score=0.8,
                    metadata={"github_url": "https://github.com/test/repo#L1"}
                )
            ]
        
        # Generate user-specific hints
        hints = self._generate_user_specific_hints(question, effective_language)
        
        # Generate user-specific suggested actions
        suggested_actions = self._generate_user_specific_suggested_actions(question)
        
        return CoachResponse(
            answer=answer_text,
            confidence=0.8 if not needs_more_context else 0.4,
            context_used=context_used,
            hints=hints,
            suggested_actions=suggested_actions,
            needs_more_context=needs_more_context,
            language_adapted=language_adapted
        )
    
    def _get_user_preferred_language(self) -> Optional[LanguageType]:
        """Get user's preferred programming language"""
        if not self.user_id:
            return None
            
        try:
            from app.models import User
            user = self.db.query(User).filter(User.id == self.user_id).first()
            if user and user.preferred_language:
                return LanguageType(user.preferred_language.lower())
        except (ValueError, Exception):
            pass
        
        return None
    
    def _get_user_context(self) -> Optional[Dict[str, Any]]:
        """Get user context for personalization"""
        if not self.user_id:
            return None
            
        try:
            from app.models import User
            user = self.db.query(User).filter(User.id == self.user_id).first()
            if not user:
                return None
                
            return {
                'language': user.preferred_language,
                'frameworks': user.preferred_frameworks or [],
                'ai_provider': user.preferred_ai_provider,
                'experience_level': 'Intermediate'
            }
        except Exception:
            return None
    
    def _generate_user_specific_hints(self, question: CoachQuestion, language: Optional[LanguageType]) -> List[str]:
        """Generate hints tailored to the user"""
        hints = ["Consider the architectural patterns in the reference code"]
        
        if language:
            lang_name = language.value
            hints = [
                f"Look for {lang_name}-specific patterns in the code",
                f"Consider {lang_name} best practices and conventions"
            ]
        
        # Add user-specific hints based on preferences
        user_context = self._get_user_context()
        if user_context and user_context.get('frameworks'):
            frameworks = user_context['frameworks']
            if frameworks:
                hints.append(f"Consider how this applies to {', '.join(frameworks[:2])}")
        
        return hints[:3]
    
    def _generate_user_specific_suggested_actions(self, question: CoachQuestion) -> List[str]:
        """Generate suggested actions tailored to the user"""
        actions = ["Examine the reference code examples"]
        
        # Get user preferences for personalized suggestions
        user_context = self._get_user_context()
        preferred_language = user_context.get('language') if user_context else None
        
        if preferred_language:
            actions.append(f"Look for {preferred_language} implementations of similar patterns")
            actions.append(f"Practice the pattern in {preferred_language} first")
        else:
            actions.extend([
                "Continue working on your current task step by step",
                "Look for similar patterns in other reference examples"
            ])
        
        return actions[:3]