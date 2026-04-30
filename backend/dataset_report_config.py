"""
Dataset Report Configuration — CRUD for bs_dataset_report_config.

Each dataset can optionally have a report configuration that drives:
  - Agent4 output format (metrics / levels / sections)
  - Frontend report rendering (column mapping / tree inference / signal rules)
"""

import json
import logging
import os
import sys

import psycopg2
from psycopg2.extras import Json, RealDictCursor

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from config_manager import get_default_datasource

logger = logging.getLogger(__name__)


def _get_connection():
    ds = get_default_datasource()
    if not ds:
        raise RuntimeError("No default datasource configured")
    return psycopg2.connect(
        host=ds.get("host", "localhost"),
        port=int(ds.get("port", 5432) or 5432),
        database=ds.get("database_name", "postgres"),
        user=ds.get("username", "postgres"),
        password=ds.get("password", ""),
        connect_timeout=8,
    )


def ensure_table():
    """Create table if not exists (idempotent)."""
    sql_path = os.path.join(CURRENT_DIR, "migrations", "20260430_report_config.sql")
    if not os.path.exists(sql_path):
        logger.warning("Migration file not found: %s", sql_path)
        return
    try:
        with _get_connection() as conn, conn.cursor() as cur:
            # Only run the CREATE TABLE part (skip INSERT which may fail if bs_datasets doesn't exist yet)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bs_dataset_report_config (
                    id          BIGSERIAL PRIMARY KEY,
                    dataset_id  BIGINT NOT NULL,
                    config_json JSONB NOT NULL DEFAULT '{}',
                    created_at  TIMESTAMPTZ DEFAULT NOW(),
                    updated_at  TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(dataset_id)
                );
            """)
            conn.commit()
    except Exception as exc:
        logger.warning("Failed to ensure report_config table: %s", exc)


def get_config(dataset_id: int) -> dict | None:
    """Get report config for a dataset. Returns None if not configured."""
    try:
        with _get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT config_json FROM bs_dataset_report_config WHERE dataset_id = %s",
                (dataset_id,),
            )
            row = cur.fetchone()
            if row:
                val = row["config_json"]
                return json.loads(val) if isinstance(val, str) else val
            return None
    except Exception as exc:
        logger.warning("Failed to get report config for dataset %s: %s", dataset_id, exc)
        return None


def upsert_config(dataset_id: int, config_json: dict) -> bool:
    """Insert or update report config for a dataset."""
    try:
        with _get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO bs_dataset_report_config (dataset_id, config_json, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (dataset_id) DO UPDATE
                  SET config_json = EXCLUDED.config_json, updated_at = NOW()
                """,
                (dataset_id, Json(config_json)),
            )
            conn.commit()
            return True
    except Exception as exc:
        logger.error("Failed to upsert report config for dataset %s: %s", dataset_id, exc)
        return False


def delete_config(dataset_id: int) -> bool:
    """Delete report config for a dataset."""
    try:
        with _get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM bs_dataset_report_config WHERE dataset_id = %s",
                (dataset_id,),
            )
            conn.commit()
            return cur.rowcount > 0
    except Exception as exc:
        logger.error("Failed to delete report config for dataset %s: %s", dataset_id, exc)
        return False


def get_default_config() -> dict:
    """Return the syyb default config (equivalent to the current hardcoded constants)."""
    return {
        "nameColumn": "节点名称",
        "parentColumn": "上级名称",
        "trackColumn": "条线",
        "levelColumn": "层级",
        "metrics": [
            {"key": "task", "label": "总任务金额", "column": "总任务金额", "format": "amount"},
            {"key": "actual", "label": "年度开单金额", "column": "年度开单金额", "format": "amount"},
            {"key": "rate", "label": "达成率", "column": "达成率", "format": "percent"},
            {"key": "remain", "label": "剩余任务金额", "column": "剩余任务金额", "format": "amount"},
        ],
        "levels": [
            {"name": "机构层", "values": ["代表处", "分公司", "业务部"]},
            {"name": "个人层", "values": ["业务代表", "业务员", "业务"]},
        ],
        "trackValues": {"org": "区域条线", "personal": "行业条线"},
        "riskThreshold": 80,
        "signalRules": [
            {"key": "rate", "op": ">=", "value": 100, "tone": "good", "label": "绿灯"},
            {"key": "rate", "op": ">=", "value": 80, "tone": "warn", "label": "黄灯"},
            {"key": "rate", "op": "<", "value": 80, "tone": "danger", "label": "红灯"},
        ],
        "sections": ["core", "group", "risk", "strategy"],
        "reportTitle": "经营分析报告",
    }
