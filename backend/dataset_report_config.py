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
                config = json.loads(val) if isinstance(val, str) else val
                return merge_with_default_config(config)
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


def merge_with_default_config(config: dict | None) -> dict:
    """Merge a saved config with the latest default shape.

    Existing deployments may have only column mapping + metrics. Newer logic also
    needs SQL projection contracts and analysis dimensions, so older configs should
    inherit those defaults without forcing users to recreate them.
    """
    default = get_default_config()
    if not isinstance(config, dict):
        return default
    merged = {**default, **config}
    if isinstance(default.get("sqlOutputContract"), dict) or isinstance(config.get("sqlOutputContract"), dict):
        merged["sqlOutputContract"] = {
            **(default.get("sqlOutputContract") or {}),
            **(config.get("sqlOutputContract") or {}),
        }
    if isinstance(default.get("sourceFields"), dict) or isinstance(config.get("sourceFields"), dict):
        merged["sourceFields"] = {
            **(default.get("sourceFields") or {}),
            **(config.get("sourceFields") or {}),
        }
    if isinstance(default.get("intentPolicies"), dict) or isinstance(config.get("intentPolicies"), dict):
        merged_policies = dict(default.get("intentPolicies") or {})
        for policy_key, policy_value in (config.get("intentPolicies") or {}).items():
            if isinstance(policy_value, dict) and isinstance(merged_policies.get(policy_key), dict):
                merged_policies[policy_key] = {**merged_policies[policy_key], **policy_value}
            else:
                merged_policies[policy_key] = policy_value
        merged["intentPolicies"] = merged_policies
    return merged


def get_default_config() -> dict:
    """Return the syyb default config.

    This config has two jobs:
      1. Tell Agent2 how raw source fields should be projected into standard report columns.
      2. Tell Agent4/frontend how rows with those standard columns should be interpreted.

    The source table does not need to physically contain 节点名称/上级名称/层级/条线;
    Agent2 should create them in SQL according to sqlOutputContract and analysisDimensions.
    """
    return {
        "nameColumn": "节点名称",
        "parentColumn": "上级名称",
        "trackColumn": "条线",
        "levelColumn": "层级",
        "businessContext": "商用事业部 2026 年经营分析。源数据来自 angel_group_data.fields JSONB，组织层级和父子关系由 SQL 投影生成，而不是源表物理列。",
        "sourceFields": {
            "organization": ["分公司", "代表处", "业务代表"],
            "time": ["当前年"],
            "metrics": ["总任务（金额）", "年度开单金额"],
        },
        "sqlOutputContract": {
            "requiredColumns": ["条线", "层级", "节点名称", "上级名称"],
            "metricColumns": ["总任务金额", "年度开单金额", "达成率", "剩余任务金额"],
            "notes": [
                "源表没有 节点名称/上级名称/层级/条线 时，必须在 SQL 中用 SELECT 别名生成这些标准列。",
                "区域链路按 商用事业部 -> 分公司 -> 代表处 -> 业务代表 输出。",
                "行业链路按 商用事业部 -> 业务部 -> 业务代表 输出。",
                "统计上级节点时必须做层级隔离，不能把下级明细行重复累加到上级汇总行。",
                "如用户查询某个分公司，应同时返回该分公司、其代表处、以及代表处下业务代表，方便前端动态下钻。",
            ],
        },
        "analysisDimensions": [
            {
                "key": "regional_chain",
                "label": "区域管理链条",
                "path": ["商用事业部", "分公司", "代表处", "业务代表"],
                "sourceFields": ["分公司", "代表处", "业务代表"],
                "trackValue": "区域条线",
                "purpose": "分析各区域市场覆盖深度、分公司/代表处任务完成、业务代表风险和优秀样本。",
            },
            {
                "key": "industry_chain",
                "label": "行业管理链条",
                "path": ["商用事业部", "业务部", "业务代表"],
                "sourceFields": ["分公司", "业务代表"],
                "trackValue": "行业条线",
                "purpose": "分析餐饮、工业医疗、公共办公等行业线专业产出和个人产能。",
            },
        ],
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
        "riskThreshold": 10,
        "officeRiskThreshold": 10,
        "officeBenchmarkThreshold": 15,
        "personRiskThreshold": 10,
        "personBenchmarkThreshold": 20,
        "signalRules": [
            {"key": "rate", "op": ">=", "value": 15, "tone": "good", "label": "标杆"},
            {"key": "rate", "op": ">=", "value": 10, "tone": "warn", "label": "中等"},
            {"key": "rate", "op": "<", "value": 10, "tone": "danger", "label": "风险"},
        ],
        "intentPolicies": {
            "ranking": {
                "enabled": True,
                "triggers": ["排名", "排行", "Top", "前", "后", "最高", "最低", "最好", "最差", "倒数", "垫底"],
                "defaultTopN": 3,
                "maxTopN": 20,
                "defaultMetricKey": "rate",
                "defaultDirection": "desc",
                "negativeTriggers": ["最低", "最差", "后", "倒数", "垫底", "落后"],
                "targetLevelAliases": {
                    "分公司": ["分公司"],
                    "代表处": ["代表处"],
                    "业务部": ["业务部", "行业部"],
                    "业务代表": ["业务代表", "业务员", "个人"],
                    "城市公司": ["城市公司", "城市分公司"],
                },
                "outputMode": "topn_only",
            }
        },
        "sections": ["core", "group", "risk", "strategy"],
        "reportTitle": "业绩分析报告",
        "agentReportGuidance": "报告结构由 SQL 标准列、场景识别和动态树决定。分公司场景必须先横向比较分公司，再纵向下钻直接下级代表处；业务代表只作为代表处后的证据层，不直接替代代表处管理判断。Agent4 不维护组织树，只基于指标、风险节点、优秀节点和 analysisDimensions 输出核心结论、亮点分析、问题诊断和改进建议；金额使用统一格式化口径，完成率按绿/黄/红灯解释，多维图表按本轮 queryIntent.sort_metric_column 优先排序。管理层摘要要少罗列、多综合：核心结论不复读 TopN 全量名单，排名类只点名前3和榜首关键指标；重点发现提炼榜首、榜内差距、风险提醒和管理动作。",
    }
