"""
Import Bookshelf metadata bundle into PostgreSQL.

Usage:
  python import_bookshelf_bundle.py /app/backend/imports/bookshelf_bundle.json
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Iterable, List

from psycopg2.extras import Json, RealDictCursor

from bookshelf_repository import BookshelfRepository
from config_manager import get_default_datasource


IMPORT_ORDER = [
    "bs_datasets",
    "bs_dataset_synonyms",
    "bs_lld_documents",
    "bs_data_dictionary_items",
    "bs_schema_definitions",
    "bs_table_relations",
    "bs_golden_sql_samples",
    "bs_agent_prompt_fragments",
    "bs_common_questions",
    "bs_regression_cases",
    "bs_dataset_external_configs",
    "bs_dataset_report_config",
]

DELETE_ORDER = list(reversed(IMPORT_ORDER))


def _ensure_optional_tables(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bs_common_questions (
            id BIGSERIAL PRIMARY KEY,
            dataset_id BIGINT NOT NULL REFERENCES bs_datasets(id) ON DELETE CASCADE,
            question_text TEXT NOT NULL,
            sort_order INT NOT NULL DEFAULT 100,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bs_dataset_external_configs (
            id BIGSERIAL PRIMARY KEY,
            dataset_id BIGINT NOT NULL REFERENCES bs_datasets(id) ON DELETE CASCADE,
            config_type VARCHAR(64) NOT NULL,
            config_key VARCHAR(128) NOT NULL,
            config_value JSONB NOT NULL DEFAULT '{}'::jsonb,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(dataset_id, config_type, config_key)
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bs_regression_cases (
            id BIGSERIAL PRIMARY KEY,
            dataset_id BIGINT NOT NULL REFERENCES bs_datasets(id) ON DELETE CASCADE,
            case_type VARCHAR(32) NOT NULL DEFAULT 'summary',
            question_text TEXT NOT NULL,
            expected_focus TEXT NOT NULL DEFAULT '',
            expected_intent VARCHAR(32) NOT NULL DEFAULT 'generate_sql',
            sort_order INT NOT NULL DEFAULT 100,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bs_dataset_report_config (
            id          BIGSERIAL PRIMARY KEY,
            dataset_id  BIGINT NOT NULL,
            config_json JSONB NOT NULL DEFAULT '{}',
            created_at  TIMESTAMPTZ DEFAULT NOW(),
            updated_at  TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(dataset_id)
        );
        """
    )
    cur.execute(
        """
        ALTER TABLE bs_schema_definitions
        ADD COLUMN IF NOT EXISTS source_id BIGINT;
        """
    )


def _normalize_row(table_name: str, row: Dict[str, Any], fallback_source_id: int) -> Dict[str, Any]:
    item = dict(row)
    if table_name in {"bs_datasets", "bs_schema_definitions"}:
        item["source_id"] = int(item.get("source_id") or fallback_source_id)
    return item


def _prepare_value(value: Any):
    if isinstance(value, (dict, list)):
        return Json(value)
    return value


def _get_table_columns(cur, table_name: str) -> List[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position;
        """,
        (table_name,),
    )
    return [str(row["column_name"]) for row in cur.fetchall()]


def _insert_rows(cur, table_name: str, rows: Iterable[Dict[str, Any]], fallback_source_id: int):
    inserted = 0
    available_columns = set(_get_table_columns(cur, table_name))
    for raw_row in rows:
        row = _normalize_row(table_name, raw_row, fallback_source_id)
        row = {key: value for key, value in row.items() if key in available_columns}
        if not row:
            continue
        columns = list(row.keys())
        placeholders = ", ".join(["%s"] * len(columns))
        sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders});"
        values = [_prepare_value(row[column]) for column in columns]
        cur.execute(sql, values)
        inserted += 1
    return inserted


def _reset_sequence(cur, table_name: str):
    cur.execute(
        """
        SELECT pg_get_serial_sequence(%s, 'id') AS seq_name;
        """,
        (table_name,),
    )
    row = cur.fetchone()
    seq_name = row["seq_name"] if row else None
    if not seq_name:
        return
    cur.execute(f"SELECT COALESCE(MAX(id), 0) AS max_id FROM {table_name};")
    max_id = int((cur.fetchone() or {}).get("max_id") or 0)
    cur.execute("SELECT setval(%s, %s, %s);", (seq_name, max_id if max_id > 0 else 1, max_id > 0))


def import_bundle(bundle_path: str) -> Dict[str, Any]:
    if not os.path.exists(bundle_path):
        raise FileNotFoundError(f"Bundle not found: {bundle_path}")

    with open(bundle_path, "r", encoding="utf-8") as fh:
        bundle = json.load(fh)

    tables = bundle.get("tables") or {}

    repo = BookshelfRepository()
    repo.ensure_schema()
    fallback_source = get_default_datasource() or {}
    fallback_source_id = int(fallback_source.get("id") or 1)

    imported_counts: Dict[str, int] = {}

    with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        _ensure_optional_tables(cur)

        for table_name in DELETE_ORDER:
            cur.execute(f"DELETE FROM {table_name};")

        for table_name in IMPORT_ORDER:
            rows = tables.get(table_name) or []
            imported_counts[table_name] = _insert_rows(cur, table_name, rows, fallback_source_id)

        for table_name in IMPORT_ORDER:
            _reset_sequence(cur, table_name)

        conn.commit()

    return {
        "ok": True,
        "bundle_path": bundle_path,
        "fallback_source_id": fallback_source_id,
        "imported_counts": imported_counts,
    }


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python import_bookshelf_bundle.py /path/to/bookshelf_bundle.json")
    result = import_bundle(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
