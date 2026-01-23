#!/usr/bin/env python3

# Test script to isolate coach_agent import issues

print("Testing coach_agent imports...")

try:
    print("Step 1: Testing basic imports...")
    import logging
    from typing import Dict, List, Optional, Any, Tuple
    from dataclasses import dataclass, field
    from enum import Enum
    from sqlalchemy.orm import Session
    print("✓ Basic imports successful")
    
    print("Step 2: Testing app imports...")
    from app.models import ReferenceSnippet, Task, LearningProject, ProjectFile, ChatHistory
    print("✓ Models import successful")
    
    from app.repositories import (
        RepositoryFactory, TaskReferenceSnippetRepository, 
        ReferenceSnippetRepository, ProjectFileRepository
    )
    print("✓ Repositories import successful")
    
    from app.llm_provider import BaseLLMProvider, LLMProviderFactory, LLMResponse
    print("✓ LLM provider import successful")
    
    from app.types import ArchitecturalPattern
    print("✓ Types import successful")
    
    print("Step 3: Testing coach_agent module...")
    import app.coach_agent
    print("✓ Coach agent module imported")
    
    print("Available attributes in coach_agent:")
    attrs = [attr for attr in dir(app.coach_agent) if not attr.startswith('_')]
    for attr in attrs:
        print(f"  - {attr}")
    
    if hasattr(app.coach_agent, 'CoachAgent'):
        print("✓ CoachAgent class found")
    else:
        print("✗ CoachAgent class NOT found")
        
    print("Step 4: Testing direct class import...")
    from app.coach_agent import CoachAgent
    print("✓ CoachAgent imported successfully")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()