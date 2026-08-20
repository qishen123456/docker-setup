"""
Export Bookshelf metadata tables into a portable JSON bundle.

Usage:
  py -3.11 backend/export_bookshelf_bundle.py
  py -3.11 backend/export_bookshelf_bundle.py backend/imports/bookshelf_bundle.json
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List

from psycopg2.extras import RealDictCursor

from bookshelf_repository import BookshelfRepository


TABLES = [
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

DEFAULT_OUTPUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "imports",
    "bookshelf_bundle.json",
)


def _ensure_optional_tables(cur):
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


def _json_default(value: Any):
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def export_bundle(output_path: str) -> Dict[str, Any]:
    repo = BookshelfRepository()
    repo.ensure_schema()

    bundle: Dict[str, Any] = {
        "version": 1,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "tables": {},
    }

    with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        _ensure_optional_tables(cur)
        for table in TABLES:
            cur.execute(f"SELECT * FROM {table} ORDER BY id ASC;")
            bundle["tables"][table] = [dict(row) for row in cur.fetchall()]

        # --- 新增：导出激活的视图（由 bs_dataset_transforms 定义）为 bs_schema_definitions 条目 ---
        cur.execute("SELECT dataset_id, target_name, target_type, source_table, transform_sql FROM bs_dataset_transforms WHERE is_active = TRUE AND target_type = 'view';")
        view_rows = cur.fetchall()
        for vr in view_rows:
            dataset_id, target_name, _, source_table, transform_sql = vr
            ddl = f"CREATE OR REPLACE VIEW {target_name} AS\n{transform_sql.replace('{{source_table}}', source_table)}"
            bundle["tables"].setdefault("bs_schema_definitions", []).append({
                "dataset_id": dataset_id,
                "table_name": target_name,
                "ddl_sql": ddl,
                "description": "auto-generated view from dataset transform",
                "is_active": True,
                "source_id": None,
            })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, ensure_ascii=False, indent=2, default=_json_default)

    return {
        "ok": True,
        "output_path": output_path,
        "table_counts": {name: len(rows) for name, rows in bundle["tables"].items()},
    }


def main():
    output_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT
    result = export_bundle(output_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
