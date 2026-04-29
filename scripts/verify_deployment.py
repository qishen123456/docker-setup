"""
Thin shim: scripts/verify_deployment.py — calls backend/verify_deployment.py.

Kept for compatibility with `python scripts/verify_deployment.py`.
"""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

spec = importlib.util.spec_from_file_location(
    "verify_deployment",
    os.path.join(BACKEND_DIR, "verify_deployment.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

if __name__ == "__main__":
    sys.exit(mod.main())
