"""
Import runtime JSON config bundle into the live config/ directory.

Default behaviour (idempotent / non-destructive):
    - Files that already exist in config/ are KEPT (so user edits survive).
    - Files that are missing are written from the bundle.

Set force_overwrite=True (or env SMARTASK_BOOTSTRAP_FORCE_CONFIG=1) to overwrite
all captured files.

Usage:
    python backend/import_runtime_config.py /path/to/runtime_config_bundle.json
    python backend/import_runtime_config.py /path/to/bundle.json --force
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
CONFIG_DIR = os.getenv("SMARTASK_CONFIG_DIR") or os.path.join(BASE_DIR, "config")


def import_bundle(bundle_path: str, force_overwrite: bool = False) -> Dict[str, Any]:
    if not os.path.exists(bundle_path):
        raise FileNotFoundError(f"Bundle not found: {bundle_path}")

    with open(bundle_path, "r", encoding="utf-8") as fh:
        bundle = json.load(fh)

    configs = bundle.get("configs") or {}
    if not isinstance(configs, dict):
        raise ValueError("Invalid bundle: 'configs' must be an object")

    os.makedirs(CONFIG_DIR, exist_ok=True)

    written: List[str] = []
    skipped_existing: List[str] = []
    errored: List[Dict[str, str]] = []

    for filename, payload in configs.items():
        if not isinstance(filename, str) or not filename.endswith(".json"):
            continue
        if isinstance(payload, dict) and "__error__" in payload:
            continue

        target_path = os.path.join(CONFIG_DIR, filename)
        if os.path.exists(target_path) and not force_overwrite:
            skipped_existing.append(filename)
            continue

        try:
            with open(target_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            written.append(filename)
        except Exception as exc:
            errored.append({"file": filename, "error": str(exc)})

    return {
        "ok": True,
        "bundle_path": bundle_path,
        "force_overwrite": force_overwrite,
        "written_files": written,
        "skipped_existing_files": skipped_existing,
        "errors": errored,
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python import_runtime_config.py /path/to/runtime_config_bundle.json [--force]")

    bundle_path = sys.argv[1]
    force = "--force" in sys.argv[2:] or os.getenv("SMARTASK_BOOTSTRAP_FORCE_CONFIG", "").lower() in {"1", "true", "yes"}

    result = import_bundle(bundle_path, force_overwrite=force)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
