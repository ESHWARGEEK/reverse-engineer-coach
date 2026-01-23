#!/usr/bin/env python3

# Debug script to find the issue in coach_agent.py

import sys
import traceback

try:
    print("Importing required modules...")
    
    import logging
    from typing import Dict, List, Optional, Any, Tuple
    from dataclasses import dataclass, field
    from enum import Enum
    from sqlalchemy.orm import Session

    from app.models import ReferenceSnippet, Task, LearningProject, ProjectFile
    from app.repositories import (
        RepositoryFactory, TaskReferenceSnippetRepository, 
        ReferenceSnippetRepository, ProjectFileRepository
    )
    from app.llm_provider import BaseLLMProvider, LLMProviderFactory, LLMResponse
    from app.types import ArchitecturalPattern

    print("All imports successful, now executing coach_agent.py...")
    
    # Read and execute the file line by line to find the error
    with open('app/coach_agent.py', 'r') as f:
        content = f.read()
    
    # Execute the content
    exec(content)
    
    print("File executed successfully!")
    print("Checking for CoachAgent in globals...")
    
    if 'CoachAgent' in globals():
        print("✓ CoachAgent found in globals")
    else:
        print("✗ CoachAgent NOT found in globals")
        print("Available classes:")
        global_items = list(globals().items())
        for name, obj in global_items:
            if isinstance(obj, type) and not name.startswith('_'):
                print(f"  - {name}")

except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()