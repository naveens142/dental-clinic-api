#!/usr/bin/env python
"""
Startup wrapper for Render deployment.
Ensures proper Python path setup before uvicorn starts.
"""
import os
import sys

# Set up the project root path
project_root = os.path.dirname(os.path.abspath(__file__))

# Force project root to be first in sys.path
if project_root in sys.path:
    sys.path.remove(project_root)
sys.path.insert(0, project_root)

print(f"[START.PY] Project root: {project_root}")
print(f"[START.PY] sys.path[0]: {sys.path[0]}")
print(f"[START.PY] Current directory: {os.getcwd()}")

# Verify critical directories exist
print(f"[START.PY] Checking directory structure...")
for dirname in ['models', 'routers', 'utils']:
    dir_path = os.path.join(project_root, dirname)
    init_file = os.path.join(dir_path, '__init__.py')
    print(f"  - {dirname}/ exists: {os.path.isdir(dir_path)}")
    print(f"  - {dirname}/__init__.py exists: {os.path.isfile(init_file)}")

# List all Python files in project root
print(f"[START.PY] Files in project root:")
for item in sorted(os.listdir(project_root)):
    if item.endswith('.py') or os.path.isdir(os.path.join(project_root, item)):
        print(f"  - {item}")

# Now start uvicorn with the app
if __name__ == "__main__":
    import uvicorn
    print(f"[START.PY] Starting uvicorn...")
    
    # Get host and port from environment or use defaults
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "10000"))
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        access_log=True,
    )
