"""
Import angel_group_data rows from a portable JSON bundle.

Usage:
  python import_angel_group_data.py /app/backend/imports/angel_group_data_bundle.json
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict

from psycopg2.extras import Json, RealDictCursor

from bookshelf_repository import BookshelfRepository


def _ensure_table(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS angel_group_data (
            id BIGSERIAL PRIMARY KEY,
            record_id TEXT UNIQUE,
            fields JSONB NOT NULL DEFAULT '{}'::jsonb,
            sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_angel_group_data_fields
        ON angel_group_data USING GIN (fields);
        """
    )


def _reset_sequence(cur):
    cur.execute(
        """
        SELECT pg_get_serial_sequence('angel_group_data', 'id') AS seq_name;
        """
    )
    row = cur.fetchone() or {}
    seq_name = row.get("seq_name")
    if not seq_name:
        return
    cur.execute("SELECT COALESCE(MAX(id), 0) AS max_id FROM angel_group_data;")
    max_id = int((cur.fetchone() or {}).get("max_id") or 0)
    cur.execute("SELECT setval(%s, %s, %s);", (seq_name, max_id if max_id > 0 else 1, max_id > 0))


def import_bundle(bundle_path: str) -> Dict[str, Any]:
    if not os.path.exists(bundle_path):
        raise FileNotFoundError(f"Bundle not found: {bundle_path}")

    with open(bundle_path, "r", encoding="utf-8") as fh:
        bundle = json.load(fh)

    rows = bundle.get("rows") or []
    repo = BookshelfRepository()
    imported = 0

    with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        _ensure_table(cur)
        cur.execute("TRUNCATE TABLE angel_group_data RESTART IDENTITY;")

        for row in rows:
            cur.execute(
                """
                INSERT INTO angel_group_data (id, record_id, fields, sync_time, created_time, updated_time)
                VALUES (%s, %s, %s, %s, %s, %s);
                """,
                (
                    row.get("id"),
                    row.get("record_id"),
                    Json(row.get("fields") or {}),
                    row.get("sync_time"),
                    row.get("created_time"),
                    row.get("updated_time"),
                ),
            )
            imported += 1

        _reset_sequence(cur)
        conn.commit()

    return {
        "ok": True,
        "bundle_path": bundle_path,
        "row_count": imported,
    }


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python import_angel_group_data.py /path/to/angel_group_data_bundle.json")
    result = import_bundle(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
