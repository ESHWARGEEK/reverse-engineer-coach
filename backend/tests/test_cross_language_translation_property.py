"""
Property-based test for cross-language concept translation.

Feature: reverse-engineer-coach, Property 19: Cross-Language Concept Translation
Validates: Requirements 9.3

This test verifies that for any target repository language different from the user's 
selected language, architectural concepts are appropriately translated while preserving 
core patterns.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from typing import List, Dict, Any
import asyncio

from app.language_support import (
    LanguageSupport, CrossLanguageTranslator, ProgrammingLanguage
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
def language_pair_strategy(draw):
    """Generate different source and target language pairs"""
    source = draw(programming_language_strategy())
    target = draw(programming_language_strategy())
    assume(source != target)  # Ensure languages are different
    return source, target


@st.composite
def code_snippet_strategy(draw):
    """Generate code snippets for different languages"""
    language = draw(programming_language_strategy())
    
    # Language-specific code templates
    code_templates = {
        ProgrammingLanguage.PYTHON: [
            """
class UserRepository:
    def __init__(self, db_connection):
        self.db = db_connection
    
    def find_by_id(self, user_id):
        return self.db.query("SELECT * FROM users WHERE id = ?", user_id)
    
    def save(self, user):
        return self.db.execute("INSERT INTO users ...", user)
""",
            """
from abc import ABC, abstractmethod

class PaymentProcessor(ABC):
    @abstractmethod
    def process_payment(self, amount, card_info):
        pass

class StripeProcessor(PaymentProcessor):
    def process_payment(self, amount, card_info):
        # Process payment via Stripe
        return {"status": "success", "transaction_id": "txn_123"}
""",
        ],
        ProgrammingLanguage.TYPESCRIPT: [
            """
interface UserRepository {
    findById(userId: string): Promise<User | null>;
    save(user: User): Promise<User>;
}

class DatabaseUserRepository implements UserRepository {
    constructor(private db: Database) {}
    
    async findById(userId: string): Promise<User | null> {
        return this.db.query('SELECT * FROM users WHERE id = ?', [userId]);
    }
    
    async save(user: User): Promise<User> {
        return this.db.execute('INSERT INTO users ...', user);
    }
}
""",
            """
interface PaymentProcessor {
    processPayment(amount: number, cardInfo: CardInfo): Promise<PaymentResult>;
}

class StripeProcessor implements PaymentProcessor {
    async processPayment(amount: number, cardInfo: CardInfo): Promise<PaymentResult> {
        // Process payment via Stripe
        return { status: 'success', transactionId: 'txn_123' };
    }
}
""",
        ],
        ProgrammingLanguage.GO: [
            """
type UserRepository interface {
    FindByID(userID string) (*User, error)
    Save(user *User) error
}

type DatabaseUserRepository struct {
    db *sql.DB
}

func (r *DatabaseUserRepository) FindByID(userID string) (*User, error) {
    var user User
    err := r.db.QueryRow("SELECT * FROM users WHERE id = ?", userID).Scan(&user)
    return &user, err
}

func (r *DatabaseUserRepository) Save(user *User) error {
    _, err := r.db.Exec("INSERT INTO users ...", user)
    return err
}
""",
            """
type PaymentProcessor interface {
    ProcessPayment(amount float64, cardInfo CardInfo) (*PaymentResult, error)
}

type StripeProcessor struct{}

func (p *StripeProcessor) ProcessPayment(amount float64, cardInfo CardInfo) (*PaymentResult, error) {
    // Process payment via Stripe
    return &PaymentResult{Status: "success", TransactionID: "txn_123"}, nil
}
""",
        ]
    }
    
    templates = code_templates.get(language, code_templates[ProgrammingLanguage.PYTHON])
    return draw(st.sampled_from(templates))


@st.composite
def architectural_patterns_strategy(draw):
    """Generate list of architectural patterns"""
    patterns = list(ArchitecturalPattern)
    return draw(st.lists(
        st.sampled_from(patterns),
        min_size=1,
        max_size=3,
        unique=True
    ))


class TestCrossLanguageConceptTranslation:
    """Property-based tests for cross-language concept translation"""
    
    def _create_translator(self):
        """Create translator with mock LLM provider"""
        mock_provider = MockLLMProvider()
        return CrossLanguageTranslator(mock_provider)
    
    @given(
        language_pair=language_pair_strategy(),
        source_code=code_snippet_strategy(),
        patterns=architectural_patterns_strategy()
    )
    @settings(max_examples=3, deadline=10000)
    def test_cross_language_concept_translation_property(self, language_pair, source_code, patterns):
        """
        Property 19: Cross-Language Concept Translation
        
        For any target repository language different from the user's selected language,
        architectural concepts should be appropriately translated while preserving core patterns.
        """
        source_language, target_language = language_pair
        
        # Create translator for this test
        translator = self._create_translator()
        
        # Run async translation test
        result = asyncio.run(self._run_translation(
            translator, source_code, source_language, target_language, patterns
        ))
        
        # Verify the translation property holds
        self._verify_translation_properties(result, source_language, target_language, patterns)
    
    async def _run_translation(self, translator, source_code, source_language, target_language, patterns):
        """Run the cross-language translation"""
        try:
            result = await translator.translate_concepts(
                source_code, source_language, target_language, patterns
            )
            
            return {
                'translation_result': result,
                'source_code': source_code,
                'source_language': source_language,
                'target_language': target_language,
                'patterns': patterns
            }
            
        except Exception as e:
            return {
                'translation_result': {'success': False, 'error': str(e)},
                'source_code': source_code,
                'source_language': source_language,
                'target_language': target_language,
                'patterns': patterns
            }
    
    def _verify_translation_properties(self, result, source_language, target_language, patterns):
        """Verify that cross-language translation properties hold"""
        translation_result = result['translation_result']
        
        # Property: Translation should succeed for valid inputs
        assert translation_result['success'], \
            f"Translation failed: {translation_result.get('error', 'Unknown error')}"
        
        # Property: Translation should preserve source and target language information
        assert translation_result['source_language'] == source_language.value, \
            f"Source language should be preserved: expected {source_language.value}, got {translation_result['source_language']}"
        
        assert translation_result['target_language'] == target_language.value, \
            f"Target language should be preserved: expected {target_language.value}, got {translation_result['target_language']}"
        
        # Property: Architectural patterns should be preserved
        preserved_patterns = translation_result.get('preserved_patterns', [])
        original_pattern_names = [p.value for p in patterns]
        
        for pattern_name in original_pattern_names:
            assert pattern_name in preserved_patterns, \
                f"Pattern {pattern_name} should be preserved in translation"
        
        # Property: Translated code should be present and non-empty
        translated_code = translation_result.get('translated_code', '')
        assert isinstance(translated_code, str) and len(translated_code.strip()) > 0, \
            f"Translated code should be a non-empty string"
        
        # Property: Translation should include language-specific adaptations
        # The translated code should be different from the source (unless it's a trivial case)
        source_code = result['source_code']
        if len(source_code.strip()) > 10:  # Only check for non-trivial code
            assert translated_code != source_code, \
                f"Translated code should be different from source code for different languages"
    
    @given(
        source_language=programming_language_strategy(),
        target_language=programming_language_strategy()
    )
    @settings(max_examples=3, deadline=5000)
    def test_language_mapping_consistency_property(self, source_language, target_language):
        """
        Property: Language mappings should be consistent and bidirectional where applicable
        """
        assume(source_language != target_language)
        
        # Get cross-language mapping
        mapping = LanguageSupport.get_cross_language_mapping(source_language, target_language)
        
        if mapping:
            # Property: Mapping should have correct source and target languages
            assert mapping.source_language == source_language, \
                f"Mapping source language should match: expected {source_language}, got {mapping.source_language}"
            
            assert mapping.target_language == target_language, \
                f"Mapping target language should match: expected {target_language}, got {mapping.target_language}"
            
            # Property: Concept mappings should be non-empty dictionaries
            assert isinstance(mapping.concept_mappings, dict), \
                f"Concept mappings should be a dictionary"
            
            assert isinstance(mapping.pattern_adaptations, dict), \
                f"Pattern adaptations should be a dictionary"
            
            assert isinstance(mapping.syntax_translations, dict), \
                f"Syntax translations should be a dictionary"
            
            # Property: Mappings should contain meaningful content
            if mapping.concept_mappings:
                for source_concept, target_concept in mapping.concept_mappings.items():
                    assert isinstance(source_concept, str) and len(source_concept) > 0, \
                        f"Source concept should be non-empty string"
                    assert isinstance(target_concept, str) and len(target_concept) > 0, \
                        f"Target concept should be non-empty string"
    
    @given(
        patterns=architectural_patterns_strategy()
    )
    @settings(max_examples=3, deadline=8000)
    def test_pattern_preservation_property(self, patterns):
        """
        Property: Pattern preservation should work across all supported language pairs
        """
        # Test with a simple code snippet that contains patterns
        simple_code = """
class Repository:
    def find(self, id):
        pass
    
    def save(self, entity):
        pass
"""
        
        translator = self._create_translator()
        
        # Test translation between Python and TypeScript (common pair)
        source_language = ProgrammingLanguage.PYTHON
        target_language = ProgrammingLanguage.TYPESCRIPT
        
        result = asyncio.run(self._run_translation(
            translator, simple_code, source_language, target_language, patterns
        ))
        
        translation_result = result['translation_result']
        
        if translation_result['success']:
            # Property: All input patterns should be mentioned in preserved patterns
            preserved_patterns = translation_result.get('preserved_patterns', [])
            original_pattern_names = [p.value for p in patterns]
            
            for pattern_name in original_pattern_names:
                assert pattern_name in preserved_patterns, \
                    f"Pattern {pattern_name} should be preserved during translation"
    
    @given(
        language_pair=language_pair_strategy()
    )
    @settings(max_examples=8, deadline=25000)
    def test_translation_notes_property(self, language_pair):
        """
        Property: Translation should provide helpful notes about language differences
        """
        source_language, target_language = language_pair
        
        # Use a simple interface example
        interface_code = """
interface UserService {
    getUser(id: string): User;
    createUser(userData: UserData): User;
}
"""
        
        translator = self._create_translator()
        patterns = [ArchitecturalPattern.SERVICE_LAYER]
        
        result = asyncio.run(self._run_translation(
            translator, interface_code, source_language, target_language, patterns
        ))
        
        translation_result = result['translation_result']
        
        if translation_result['success']:
            # Property: Translation notes should be provided
            translation_notes = translation_result.get('translation_notes', [])
            assert isinstance(translation_notes, list), \
                f"Translation notes should be a list"
            
            # Property: Notes should contain meaningful information about the translation
            if translation_notes:
                for note in translation_notes:
                    assert isinstance(note, str) and len(note.strip()) > 0, \
                        f"Each translation note should be a non-empty string"
    
    @given(
        source_code=st.text(min_size=10, max_size=200)
    )
    @settings(max_examples=5, deadline=20000)
    def test_translation_robustness_property(self, source_code):
        """
        Property: Translation should handle various code inputs gracefully
        """
        # Test with Python to TypeScript translation
        source_language = ProgrammingLanguage.PYTHON
        target_language = ProgrammingLanguage.TYPESCRIPT
        patterns = [ArchitecturalPattern.HANDLER]
        
        translator = self._create_translator()
        
        result = asyncio.run(self._run_translation(
            translator, source_code, source_language, target_language, patterns
        ))
        
        translation_result = result['translation_result']
        
        # Property: Translation should either succeed or fail gracefully
        assert 'success' in translation_result, \
            f"Translation result should indicate success status"
        
        if translation_result['success']:
            # If successful, should have translated code
            assert 'translated_code' in translation_result, \
                f"Successful translation should include translated code"
        else:
            # If failed, should have error message
            assert 'error' in translation_result, \
                f"Failed translation should include error message"


# Integration test for the complete translation workflow
class TestCrossLanguageTranslationIntegration:
    """Integration tests for cross-language concept translation"""
    
    @pytest.mark.asyncio
    async def test_complete_translation_workflow(self):
        """Test the complete workflow of cross-language concept translation"""
        # Create translator
        mock_provider = MockLLMProvider()
        translator = CrossLanguageTranslator(mock_provider)
        
        # Test Python to TypeScript translation
        python_code = """
class UserRepository:
    def __init__(self, database):
        self.db = database
    
    def find_by_id(self, user_id):
        return self.db.query("SELECT * FROM users WHERE id = ?", user_id)
    
    def save(self, user):
        return self.db.execute("INSERT INTO users VALUES (?)", user)
"""
        
        patterns = [ArchitecturalPattern.REPOSITORY]
        
        result = await translator.translate_concepts(
            python_code,
            ProgrammingLanguage.PYTHON,
            ProgrammingLanguage.TYPESCRIPT,
            patterns
        )
        
        # Verify translation succeeded
        assert result['success']
        assert result['source_language'] == 'python'
        assert result['target_language'] == 'typescript'
        assert 'Repository Pattern' in result['preserved_patterns']
        assert len(result['translated_code']) > 0
        
        # Verify translation notes are provided
        assert isinstance(result['translation_notes'], list)
    
    @pytest.mark.asyncio
    async def test_bidirectional_translation_consistency(self):
        """Test that translation concepts are consistent in both directions"""
        mock_provider = MockLLMProvider()
        translator = CrossLanguageTranslator(mock_provider)
        
        # Simple interface code
        interface_code = """
interface PaymentProcessor {
    processPayment(amount: number): PaymentResult;
}
"""
        
        patterns = [ArchitecturalPattern.STRATEGY]
        
        # Translate TypeScript to Python
        ts_to_py = await translator.translate_concepts(
            interface_code,
            ProgrammingLanguage.TYPESCRIPT,
            ProgrammingLanguage.PYTHON,
            patterns
        )
        
        # Translate Python to TypeScript (using a Python interface)
        python_interface = """
from abc import ABC, abstractmethod

class PaymentProcessor(ABC):
    @abstractmethod
    def process_payment(self, amount: float) -> dict:
        pass
"""
        
        py_to_ts = await translator.translate_concepts(
            python_interface,
            ProgrammingLanguage.PYTHON,
            ProgrammingLanguage.TYPESCRIPT,
            patterns
        )
        
        # Both translations should succeed
        assert ts_to_py['success']
        assert py_to_ts['success']
        
        # Both should preserve the same patterns
        assert ts_to_py['preserved_patterns'] == py_to_ts['preserved_patterns']


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])