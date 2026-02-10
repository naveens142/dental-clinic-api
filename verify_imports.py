#!/usr/bin/env python
"""
Import verification script for dental-clinic-api.
Tests that all critical modules can be imported successfully.
"""

import sys
import os

print("=" * 60)
print("DENTAL CLINIC API - IMPORT VERIFICATION")
print("=" * 60)
print(f"Python: {sys.version}")
print(f"Working directory: {os.getcwd()}")
print(f"sys.path[0]: {sys.path[0]}")
print("=" * 60)

# Test imports
tests = [
    ("main module", lambda: __import__("main")),
    ("routers.api", lambda: __import__("routers.api")),
    ("models.schemas", lambda: __import__("models.schemas")),
    ("utils.helpers", lambda: __import__("utils.helpers")),
    ("database_service", lambda: __import__("database_service")),
    ("jwt_utils", lambda: __import__("jwt_utils")),
]

passed = 0
failed = 0

for name, import_fn in tests:
    try:
        import_fn()
        print(f"✓ {name}")
        passed += 1
    except Exception as e:
        print(f"✗ {name}: {type(e).__name__}: {e}")
        failed += 1

print("=" * 60)
print(f"Results: {passed} passed, {failed} failed")
print("=" * 60)

if failed > 0:
    sys.exit(1)
else:
    print("All imports successful!")
    sys.exit(0)
