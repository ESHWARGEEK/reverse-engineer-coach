import importlib.util
import sys

# Load the module directly
spec = importlib.util.spec_from_file_location("global_error_handler", "app/middleware/global_error_handler.py")
module = importlib.util.module_from_spec(spec)
sys.modules["global_error_handler"] = module
spec.loader.exec_module(module)

print("Module loaded successfully")
print("Available attributes:", [attr for attr in dir(module) if not attr.startswith('_')])
print("setup_global_error_handling available:", hasattr(module, 'setup_global_error_handling'))

if hasattr(module, 'setup_global_error_handling'):
    print("Function type:", type(module.setup_global_error_handling))
else:
    print("Function not found!")
    
    # Let's check the source
    import inspect
    try:
        source = inspect.getsource(module)
        print("Module source length:", len(source))
        if 'setup_global_error_handling' in source:
            print("Function name found in source")
        else:
            print("Function name NOT found in source")
    except Exception as e:
        print("Could not get source:", e)