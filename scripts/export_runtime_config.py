"""
Export SmartAsk runtime resources into a portable JSON bundle.

Examples:
  python scripts/export_runtime_config.py --output runtime_config.json
  python scripts/export_runtime_config.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from runtime_migration import export_runtime_bundle, summarize_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Export SmartAsk runtime resources.")
    parser.add_argument("--output", "-o", default=os.path.join(ROOT_DIR, "runtime_config_bundle.json"))
    args = parser.parse_args()

    bundle = export_runtime_bundle(args.output)
    print(json.dumps({"ok": True, "output": args.output, "summary": summarize_bundle(bundle)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
