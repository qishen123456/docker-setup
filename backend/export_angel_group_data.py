"""
Export angel_group_data rows into a portable JSON bundle.

Usage:
  python backend/export_angel_group_data.py
  python backend/export_angel_group_data.py backend/imports/angel_group_data_bundle.json
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict

from psycopg2.extras import RealDictCursor

from bookshelf_repository import BookshelfRepository


DEFAULT_OUTPUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "imports",
    "angel_group_data_bundle.json",
)


def _json_default(value: Any):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def export_bundle(output_path: str) -> Dict[str, Any]:
    repo = BookshelfRepository()
    rows = []

    with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, record_id, fields, sync_time, created_time, updated_time
            FROM angel_group_data
            ORDER BY id ASC;
            """
        )
        rows = [dict(item) for item in cur.fetchall()]

    bundle = {
        "version": 1,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "table": "angel_group_data",
        "row_count": len(rows),
        "rows": rows,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, ensure_ascii=False, indent=2, default=_json_default)

    return {
        "ok": True,
        "output_path": output_path,
        "row_count": len(rows),
    }


def main():
    output_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT
    result = export_bundle(output_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
