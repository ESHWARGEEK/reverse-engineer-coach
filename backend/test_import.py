#!/usr/bin/env python3
"""Test import of global error handler"""

try:
    print("Importing global error handler...")
    import app.middleware.global_error_handler as geh
    print("Module imported successfully")
    
    print("Available attributes:")
    for attr in dir(geh):
        if not attr.startswith('_'):
            print(f"  - {attr}")
    
    print(f"setup_global_error_handling available: {'setup_global_error_handling' in dir(geh)}")
    
    if hasattr(geh, 'setup_global_error_handling'):
        print("Function found!")
    else:
        print("Function not found!")
        
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()