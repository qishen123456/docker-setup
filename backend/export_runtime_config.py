"""
Export runtime JSON configs to a single portable bundle.

Files captured (existing only, missing files are simply skipped):
    config/datasources.json
    config/ai_settings.json
    config/feishu_sync.json
    config/sql_prompts.json
    config/app_config.json

Sensitive fields (`password_b64`, `api_key_b64`, `app_secret`) are kept AS-IS
because they are already obfuscated/encrypted by config_manager.

Usage:
    python backend/export_runtime_config.py
    python backend/export_runtime_config.py /path/to/output.json
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
CONFIG_DIR = os.getenv("SMARTASK_CONFIG_DIR") or os.path.join(BASE_DIR, "config")

DEFAULT_OUTPUT = os.path.join(CURRENT_DIR, "imports", "runtime_config_bundle.json")

CAPTURED_FILES = [
    "datasources.json",
    "ai_settings.json",
    "feishu_sync.json",
    "sql_prompts.json",
    "app_config.json",
    "employee_permissions.json",
]


def export_bundle(output_path: str = DEFAULT_OUTPUT) -> Dict[str, Any]:
    bundle: Dict[str, Any] = {
        "version": 1,
        "type": "runtime_config",
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "configs": {},
    }

    for filename in CAPTURED_FILES:
        path = os.path.join(CONFIG_DIR, filename)
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                bundle["configs"][filename] = json.load(fh)
        except Exception as exc:
            bundle["configs"][filename] = {"__error__": str(exc)}

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, ensure_ascii=False, indent=2)

    return {
        "ok": True,
        "output_path": output_path,
        "captured": [name for name in bundle["configs"] if "__error__" not in (bundle["configs"][name] or {})],
        "skipped": [name for name in CAPTURED_FILES if name not in bundle["configs"]],
    }


def main() -> None:
    output_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT
    result = export_bundle(output_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
