"""
LLM Provider Interface for The Reverse Engineer Coach.

Provides integration with OpenAI and Anthropic LLMs for specification generation,
code simplification, and educational content creation.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class LLMResponse:
    """Response from LLM provider"""
    content: str
    provider: LLMProvider
    model: str
    tokens_used: int
    success: bool
    error_message: Optional[str] = None


@dataclass
class SpecificationPrompt:
    """Prompt for specification generation"""
    repository_info: Dict[str, Any]
    structural_elements: List[Dict[str, Any]]
    pattern_analysis: List[Dict[str, Any]]
    target_audience: str = "mid-level software engineers"
    learning_objectives: List[str] = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @abstractmethod
    async def generate_specification(self, prompt: SpecificationPrompt) -> LLMResponse:
        """Generate a learning specification from repository analysis"""
        pass
    
    @abstractmethod
    async def simplify_code_explanation(self, code: str, patterns: List[str], 
                                      language: str) -> LLMResponse:
        """Generate simplified explanation of code focusing on architectural patterns"""
        pass
    
    @abstractmethod
    async def generate_learning_tasks(self, specification: str, 
                                    difficulty_level: str) -> LLMResponse:
        """Generate progressive learning tasks from specification"""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider implementation"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        api_key = api_key or settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        super().__init__(api_key, model)
        self.base_url = "https://api.openai.com/v1"
    
    async def _make_request(self, messages: List[Dict[str, str]], 
                          max_tokens: int = 4000) -> LLMResponse:
        """Make request to OpenAI API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                tokens_used = data["usage"]["total_tokens"]
                
                return LLMResponse(
                    content=content,
                    provider=LLMProvider.OPENAI,
                    model=self.model,
                    tokens_used=tokens_used,
                    success=True
                )
            else:
                error_msg = f"OpenAI API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return LLMResponse(
                    content="",
                    provider=LLMProvider.OPENAI,
                    model=self.model,
                    tokens_used=0,
                    success=False,
                    error_message=error_msg
                )
                
        except Exception as e:
            error_msg = f"OpenAI request failed: {str(e)}"
            logger.error(error_msg)
            return LLMResponse(
                content="",
                provider=LLMProvider.OPENAI,
                model=self.model,
                tokens_used=0,
                success=False,
                error_message=error_msg
            )
    
    async def generate_specification(self, prompt: SpecificationPrompt) -> LLMResponse:
        """Generate learning specification using OpenAI"""
        system_prompt = """You are an expert software architect and technical educator. Your task is to create comprehensive learning specifications that transform complex production systems into structured educational content.

Focus on:
1. Identifying core architectural patterns and their educational value
2. Creating progressive learning paths from beginner to advanced concepts
3. Simplifying complex systems while preserving essential architectural insights
4. Generating practical, hands-on learning objectives

Output should be in Markdown format with clear sections for:
- Learning Objectives
- Architectural Patterns Overview
- Core Concepts
- Implementation Guidance
- Progressive Exercises"""

        user_prompt = f"""
Create a comprehensive learning specification for the following repository analysis:

**Repository Information:**
- Name: {prompt.repository_info.get('name', 'Unknown')}
- Description: {prompt.repository_info.get('description', 'No description')}
- Primary Language: {prompt.repository_info.get('language', 'Unknown')}
- Complexity Score: {prompt.repository_info.get('complexity_score', 0.0)}

**Identified Architectural Patterns:**
{json.dumps(prompt.pattern_analysis, indent=2)}

**Key Structural Elements:**
{json.dumps(prompt.structural_elements[:5], indent=2)}  # Limit to top 5 elements

**Target Audience:** {prompt.target_audience}

**Learning Objectives:** {prompt.learning_objectives or ['Understand core architectural patterns', 'Implement simplified versions', 'Apply patterns to new contexts']}

Generate a detailed learning specification that helps developers understand and implement these architectural patterns through hands-on practice.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return await self._make_request(messages, max_tokens=4000)
    
    async def simplify_code_explanation(self, code: str, patterns: List[str], 
                                      language: str) -> LLMResponse:
        """Generate simplified code explanation"""
        system_prompt = """You are a technical educator specializing in code simplification and architectural pattern explanation. Your task is to explain complex code in simple terms while highlighting architectural patterns.

Focus on:
1. Identifying the core architectural purpose of the code
2. Explaining patterns in simple, educational terms
3. Removing implementation complexity while preserving learning value
4. Providing clear, actionable insights for learners"""

        user_prompt = f"""
Explain the following {language} code, focusing on the architectural patterns: {', '.join(patterns)}

```{language}
{code}
```

Provide:
1. A simplified explanation of what this code does architecturally
2. How it implements the identified patterns: {', '.join(patterns)}
3. Key learning points for developers
4. Simplified version focusing on the core pattern (if applicable)

Keep the explanation educational and accessible to mid-level developers.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return await self._make_request(messages, max_tokens=2000)
    
    async def generate_learning_tasks(self, specification: str, 
                                    difficulty_level: str = "intermediate") -> LLMResponse:
        """Generate progressive learning tasks"""
        system_prompt = """You are an expert curriculum designer for software engineering education. Create progressive, hands-on learning tasks that build practical skills.

Tasks should be:
1. Incremental and build upon each other
2. Practical and implementable
3. Focused on architectural understanding
4. Include clear success criteria
5. Appropriate for the specified difficulty level

Format as a numbered list with clear descriptions and expected outcomes."""

        user_prompt = f"""
Based on the following learning specification, create a series of progressive learning tasks for {difficulty_level} level developers:

{specification}

Generate 5-8 tasks that:
1. Start with understanding and analysis
2. Progress to implementation
3. Include testing and validation
4. End with extension and application

Each task should include:
- Clear objective
- Specific deliverables
- Success criteria
- Estimated time commitment
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return await self._make_request(messages, max_tokens=3000)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider implementation"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-sonnet-20240229"):
        api_key = api_key or settings.ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("Anthropic API key is required")
        
        super().__init__(api_key, model)
        self.base_url = "https://api.anthropic.com/v1"
    
    async def _make_request(self, messages: List[Dict[str, str]], 
                          max_tokens: int = 4000) -> LLMResponse:
        """Make request to Anthropic API"""
        try:
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            # Convert messages format for Anthropic
            system_message = ""
            user_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    user_messages.append(msg)
            
            payload = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": user_messages,
                "system": system_message
            }
            
            response = await self.client.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["content"][0]["text"]
                tokens_used = data["usage"]["input_tokens"] + data["usage"]["output_tokens"]
                
                return LLMResponse(
                    content=content,
                    provider=LLMProvider.ANTHROPIC,
                    model=self.model,
                    tokens_used=tokens_used,
                    success=True
                )
            else:
                error_msg = f"Anthropic API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return LLMResponse(
                    content="",
                    provider=LLMProvider.ANTHROPIC,
                    model=self.model,
                    tokens_used=0,
                    success=False,
                    error_message=error_msg
                )
                
        except Exception as e:
            error_msg = f"Anthropic request failed: {str(e)}"
            logger.error(error_msg)
            return LLMResponse(
                content="",
                provider=LLMProvider.ANTHROPIC,
                model=self.model,
                tokens_used=0,
                success=False,
                error_message=error_msg
            )
    
    async def generate_specification(self, prompt: SpecificationPrompt) -> LLMResponse:
        """Generate learning specification using Anthropic Claude"""
        # Similar implementation to OpenAI but adapted for Claude's format
        system_prompt = """You are an expert software architect and technical educator. Create comprehensive learning specifications that transform complex production systems into structured educational content.

Focus on architectural patterns, progressive learning paths, and practical implementation guidance."""

        user_prompt = f"""
Create a learning specification for this repository analysis:

Repository: {prompt.repository_info.get('name', 'Unknown')}
Language: {prompt.repository_info.get('language', 'Unknown')}
Patterns: {[p.get('pattern', '') for p in prompt.pattern_analysis]}

Target: {prompt.target_audience}

Generate detailed Markdown specification with learning objectives, architectural insights, and implementation guidance.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return await self._make_request(messages, max_tokens=4000)
    
    async def simplify_code_explanation(self, code: str, patterns: List[str], 
                                      language: str) -> LLMResponse:
        """Generate simplified code explanation using Claude"""
        system_prompt = """Explain code focusing on architectural patterns in educational terms."""
        
        user_prompt = f"""
Explain this {language} code implementing patterns: {', '.join(patterns)}

```{language}
{code}
```

Provide simplified explanation and key learning points.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return await self._make_request(messages, max_tokens=2000)
    
    async def generate_learning_tasks(self, specification: str, 
                                    difficulty_level: str = "intermediate") -> LLMResponse:
        """Generate progressive learning tasks using Claude"""
        system_prompt = """Create progressive learning tasks for software engineering education."""
        
        user_prompt = f"""
Create {difficulty_level} level learning tasks from this specification:

{specification}

Generate 5-8 progressive tasks with objectives, deliverables, and success criteria.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return await self._make_request(messages, max_tokens=3000)


class LLMProviderFactory:
    """Factory for creating LLM provider instances"""
    
    @staticmethod
    def create_provider(provider_type: LLMProvider, 
                       api_key: Optional[str] = None,
                       model: Optional[str] = None) -> BaseLLMProvider:
        """Create LLM provider instance"""
        if provider_type == LLMProvider.OPENAI:
            model = model or "gpt-4"
            return OpenAIProvider(api_key, model)
        elif provider_type == LLMProvider.ANTHROPIC:
            model = model or "claude-3-sonnet-20240229"
            return AnthropicProvider(api_key, model)
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")
    
    @staticmethod
    def get_default_provider() -> BaseLLMProvider:
        """Get default LLM provider based on available API keys"""
        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            return LLMProviderFactory.create_provider(LLMProvider.OPENAI)
        elif hasattr(settings, 'ANTHROPIC_API_KEY') and settings.ANTHROPIC_API_KEY:
            return LLMProviderFactory.create_provider(LLMProvider.ANTHROPIC)
        else:
            # Return a mock provider for testing
            return MockLLMProvider()


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for testing and development"""
    
    def __init__(self):
        # Don't call super().__init__ to avoid requiring API key
        self.model = "mock-model"
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    async def generate_specification(self, prompt: SpecificationPrompt) -> LLMResponse:
        """Generate mock specification"""
        mock_content = f"""# Learning Specification: {prompt.repository_info.get('name', 'Repository')}

## Learning Objectives
- Understand core architectural patterns
- Implement simplified versions of key components
- Apply patterns to new contexts

## Architectural Patterns Overview
The repository demonstrates several key patterns:
{', '.join([p.get('pattern', 'Unknown') for p in prompt.pattern_analysis[:3]])}

## Core Concepts
1. **Pattern Recognition**: Identify architectural patterns in production code
2. **Code Simplification**: Extract essential logic from complex implementations
3. **Progressive Implementation**: Build understanding through incremental development

## Implementation Guidance
Start with the most fundamental patterns and gradually build complexity.
Focus on understanding the 'why' behind each architectural decision.

## Progressive Exercises
1. Analyze existing pattern implementations
2. Create simplified versions
3. Extend with additional features
4. Apply to new problem domains
"""
        
        return LLMResponse(
            content=mock_content,
            provider=LLMProvider.OPENAI,  # Mock as OpenAI
            model=self.model,
            tokens_used=500,
            success=True
        )
    
    async def simplify_code_explanation(self, code: str, patterns: List[str], 
                                      language: str) -> LLMResponse:
        """Generate mock code explanation"""
        mock_content = f"""## Code Explanation ({language})

This code implements the following architectural patterns: {', '.join(patterns)}

### Core Purpose
The code demonstrates how to structure components for maintainability and extensibility.

### Key Learning Points
1. **Separation of Concerns**: Each component has a single responsibility
2. **Interface Design**: Clear contracts between components
3. **Pattern Implementation**: Follows established architectural patterns

### Simplified Version
Focus on the core logic and pattern implementation, removing production complexity like logging and error handling.
"""
        
        return LLMResponse(
            content=mock_content,
            provider=LLMProvider.OPENAI,
            model=self.model,
            tokens_used=200,
            success=True
        )
    
    async def generate_learning_tasks(self, specification: str, 
                                    difficulty_level: str = "intermediate") -> LLMResponse:
        """Generate mock learning tasks"""
        mock_content = f"""# Learning Tasks ({difficulty_level} level)

## Task 1: Pattern Analysis
**Objective**: Identify and document architectural patterns
**Deliverable**: Pattern analysis document
**Success Criteria**: Correctly identify at least 3 patterns
**Time**: 2 hours

## Task 2: Code Simplification
**Objective**: Create simplified versions of key components
**Deliverable**: Simplified code implementations
**Success Criteria**: Preserve core functionality while reducing complexity
**Time**: 4 hours

## Task 3: Implementation
**Objective**: Implement core patterns from scratch
**Deliverable**: Working implementation
**Success Criteria**: Passes all functional tests
**Time**: 6 hours

## Task 4: Extension
**Objective**: Extend implementation with additional features
**Deliverable**: Enhanced version with new capabilities
**Success Criteria**: Maintains architectural integrity
**Time**: 4 hours

## Task 5: Application
**Objective**: Apply learned patterns to new problem domain
**Deliverable**: New implementation using same patterns
**Success Criteria**: Demonstrates pattern understanding
**Time**: 8 hours
"""
        
        return LLMResponse(
            content=mock_content,
            provider=LLMProvider.OPENAI,
            model=self.model,
            tokens_used=300,
            success=True
        )


# Convenience functions
async def create_llm_provider(provider_type: Optional[LLMProvider] = None) -> BaseLLMProvider:
    """Create LLM provider instance"""
    if provider_type:
        return LLMProviderFactory.create_provider(provider_type)
    else:
        return LLMProviderFactory.get_default_provider()

# Factory function for dependency injection
def get_llm_provider() -> BaseLLMProvider:
    """Get LLM provider instance for dependency injection"""
    try:
        # Try to create OpenAI provider first
        return LLMProviderFactory.create_provider(LLMProvider.OPENAI)
    except Exception:
        # Fallback to mock provider for development
        return MockLLMProvider()