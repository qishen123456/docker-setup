"""
One-shot full backup: bookshelf metadata + runtime config + business data.

Output:
    backups/<timestamp>/bookshelf_bundle.json
    backups/<timestamp>/runtime_config_bundle.json
    backups/<timestamp>/angel_group_data_bundle.json

This script is meant to be run from project root, either on the host (for the
non-Docker dev workflow) or inside the backend container:
    docker compose exec backend python /app/backend/../scripts/backup_all.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict


HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


def _run(name: str, fn) -> Dict[str, Any]:
    print(f"[backup] >>> {name}")
    try:
        result = fn()
        print(f"[backup] <<< {name} OK")
        return {"ok": True, "result": result}
    except Exception as exc:
        print(f"[backup] <<< {name} FAILED: {exc}")
        return {"ok": False, "error": str(exc)}


def main() -> int:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(PROJECT_ROOT, "backups", timestamp)
    os.makedirs(out_dir, exist_ok=True)

    results: Dict[str, Any] = {"timestamp": timestamp, "output_dir": out_dir}

    # 1. Bookshelf metadata
    def _export_bookshelf():
        from export_bookshelf_bundle import export_bundle as _exp

        return _exp(os.path.join(out_dir, "bookshelf_bundle.json"))

    results["bookshelf"] = _run("export_bookshelf_bundle", _export_bookshelf)

    # 2. Runtime config
    def _export_runtime():
        from runtime_migration import export_runtime_bundle, summarize_bundle

        bundle = export_runtime_bundle(os.path.join(out_dir, "runtime_config_bundle.json"))
        return {"ok": True, "output_path": os.path.join(out_dir, "runtime_config_bundle.json"), "summary": summarize_bundle(bundle)}

    results["runtime_config"] = _run("export_runtime_config", _export_runtime)

    # 3. Business data
    def _export_angel():
        from export_angel_group_data import export_bundle as _exp

        return _exp(os.path.join(out_dir, "angel_group_data_bundle.json"))

    results["angel_group_data"] = _run("export_angel_group_data", _export_angel)

    # Write a manifest
    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2, default=str)

    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))

    overall_ok = all(v.get("ok") for v in results.values() if isinstance(v, dict))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
