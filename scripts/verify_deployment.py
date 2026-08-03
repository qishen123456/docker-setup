"""Compatibility shim for ``python scripts/verify_deployment.py``."""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
DEPLOY_SCRIPT = os.path.join(HERE, "deploy", "verify_deployment.py")

spec = importlib.util.spec_from_file_location("verify_deployment", DEPLOY_SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

if __name__ == "__main__":
    sys.exit(mod.main())
