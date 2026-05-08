"""
Import SmartAsk runtime resources from a portable JSON bundle.

Examples:
  python scripts/import_runtime_config.py --input runtime_config.json --dry-run
  python scripts/import_runtime_config.py --input runtime_config.json --mode merge
  python scripts/import_runtime_config.py --input runtime_config.json --mode replace --overwrite-configs
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

from runtime_migration import import_runtime_bundle, load_bundle_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Import SmartAsk runtime resources.")
    parser.add_argument("--input", "-i", required=True, help="Runtime bundle JSON path.")
    parser.add_argument("--mode", choices=["merge", "replace"], default="merge")
    parser.add_argument("--overwrite-configs", action="store_true", help="Overwrite existing JSON config files.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing.")
    parser.add_argument("--no-backup", action="store_true", help="Skip automatic rollback bundle before import.")
    args = parser.parse_args()

    bundle = load_bundle_file(args.input)
    result = import_runtime_bundle(
        bundle,
        mode=args.mode,
        overwrite_configs=args.overwrite_configs,
        dry_run=args.dry_run,
        auto_backup=not args.no_backup,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
