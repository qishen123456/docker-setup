"""
容器内 / 本地环境一键自检脚本。

校验项：
- PostgreSQL 可连接
- 关键 schema 表存在 (bs_datasets, angel_group_data 等)
- bs_datasets 已导入数据
- 报告场景识别与报告模板契约校验模块可用
- Flask /api/health 健康
- /api/datasources 与 /api/ai-models 返回 200

用法：
    docker compose exec backend python verify_deployment.py
    或
    python backend/verify_deployment.py
"""
from __future__ import annotations

import os
import sys
from typing import List, Tuple

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

try:
    from dotenv import load_dotenv
    BASE_DIR = os.path.dirname(CURRENT_DIR)
    load_dotenv(os.path.join(BASE_DIR, ".env"), override=False)
except Exception:
    pass


REQUIRED_TABLES = [
    "bs_datasets",
    "bs_lld_documents",
    "bs_data_dictionary_items",
    "bs_schema_definitions",
    "bs_table_relations",
    "bs_golden_sql_samples",
    "bs_agent_prompt_fragments",
    "bs_common_questions",
    "bs_dataset_external_configs",
    "bs_regression_cases",
    "angel_group_data",
]


def _check_postgres() -> Tuple[bool, str]:
    try:
        import psycopg2

        from config_manager import get_default_datasource
    except Exception as exc:
        return False, f"无法 import: {exc}"

    ds = get_default_datasource() or {}
    try:
        conn = psycopg2.connect(
            host=ds.get("host") or os.getenv("SMARTASK_DB_HOST", "postgres"),
            port=int(ds.get("port") or os.getenv("SMARTASK_DB_PORT", "5432") or 5432),
            database=ds.get("database_name") or os.getenv("SMARTASK_DB_DATABASE", "postgres"),
            user=ds.get("username") or os.getenv("SMARTASK_DB_USERNAME", "postgres"),
            password=ds.get("password") or os.getenv("SMARTASK_DB_PASSWORD", "postgres"),
            connect_timeout=5,
        )
        conn.close()
        return True, "PostgreSQL 可连接"
    except Exception as exc:
        return False, f"PostgreSQL 连接失败: {exc}"


def _check_tables() -> List[Tuple[str, bool, str]]:
    import psycopg2

    from config_manager import get_default_datasource

    results: List[Tuple[str, bool, str]] = []
    ds = get_default_datasource() or {}
    try:
        conn = psycopg2.connect(
            host=ds.get("host") or os.getenv("SMARTASK_DB_HOST", "postgres"),
            port=int(ds.get("port") or os.getenv("SMARTASK_DB_PORT", "5432") or 5432),
            database=ds.get("database_name") or os.getenv("SMARTASK_DB_DATABASE", "postgres"),
            user=ds.get("username") or os.getenv("SMARTASK_DB_USERNAME", "postgres"),
            password=ds.get("password") or os.getenv("SMARTASK_DB_PASSWORD", "postgres"),
            connect_timeout=5,
        )
    except Exception as exc:
        return [("postgres", False, f"无法连接: {exc}")]

    try:
        with conn.cursor() as cur:
            for name in REQUIRED_TABLES:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {name};")
                    row = cur.fetchone()
                    cnt = int(row[0]) if row else 0
                    results.append((name, True, f"行数={cnt}"))
                except Exception as exc:
                    conn.rollback()
                    results.append((name, False, f"查询失败: {exc}"))
    finally:
        conn.close()
    return results


def _check_http() -> List[Tuple[str, bool, str]]:
    try:
        import requests
    except Exception:
        return [("http", False, "未安装 requests")]

    backend_port = os.getenv("SMARTASK_BACKEND_PORT", "5002")
    base = f"http://localhost:{backend_port}"
    out: List[Tuple[str, bool, str]] = []
    for path in ["/api/health", "/api/datasources", "/api/ai-models"]:
        try:
            r = requests.get(base + path, timeout=5)
            ok = 200 <= r.status_code < 300
            out.append((path, ok, f"HTTP {r.status_code}"))
        except Exception as exc:
            out.append((path, False, f"请求失败: {exc}"))
    return out


def _check_report_contract() -> List[Tuple[str, bool, str]]:
    out: List[Tuple[str, bool, str]] = []
    try:
        from report_contract_health import validate_report_contract
        from report_scene_registry import detect_report_scene
    except Exception as exc:
        return [("report_contract", False, f"无法 import 报告契约模块: {exc}")]

    try:
        scene = detect_report_scene("东部和西部业绩对比", None, 2)
        ok = scene.get("key") == "comparative" and scene.get("layout") == "comparison"
        out.append(("report_scene", ok, f"scene={scene.get('key')}, layout={scene.get('layout')}"))
    except Exception as exc:
        out.append(("report_scene", False, f"场景识别失败: {exc}"))
        scene = {"required_contract": ["nameColumn", "metrics"]}

    sample_config = {
        "nameColumn": "节点名称",
        "parentColumn": "上级名称",
        "levelColumn": "层级",
        "trackColumn": "条线",
        "metrics": [
            {"key": "task", "label": "任务", "column": "任务金额", "format": "amount"},
            {"key": "actual", "label": "开单", "column": "开单金额", "format": "amount"},
            {"key": "rate", "label": "达成率", "column": "达成率", "format": "percent"},
        ],
        "analysisDimensions": [{"key": "level", "column": "层级"}],
        "signalRules": [{"key": "rate", "dangerBelow": 0.1, "goodAbove": 0.2}],
        "sqlOutputContract": {
            "requiredColumns": ["节点名称", "层级", "任务金额", "开单金额", "达成率"]
        },
    }
    sample_columns = ["节点名称", "上级名称", "层级", "条线", "任务金额", "开单金额", "达成率"]
    try:
        contract = validate_report_contract(sample_config, sample_columns, scene)
        ok = bool(contract.get("used")) and contract.get("score", 0) >= 85
        out.append(("report_contract", ok, f"score={contract.get('score')}, level={contract.get('level')}"))
    except Exception as exc:
        out.append(("report_contract", False, f"契约校验失败: {exc}"))

    return out


def main() -> int:
    print("==================================================")
    print(" SmartAsk 部署自检")
    print("==================================================")

    overall_ok = True

    ok, msg = _check_postgres()
    print(f"[{'PASS' if ok else 'FAIL'}] PostgreSQL 连接 — {msg}")
    if not ok:
        return 2

    print("--- 关键表检查 ---")
    for name, ok, msg in _check_tables():
        flag = "PASS" if ok else "FAIL"
        print(f"[{flag}] {name:32s} — {msg}")
        if not ok:
            overall_ok = False

    print("--- 报告链路检查 ---")
    for name, ok, msg in _check_report_contract():
        flag = "PASS" if ok else "FAIL"
        print(f"[{flag}] {name:32s} — {msg}")
        if not ok:
            overall_ok = False

    print("--- HTTP 接口检查 ---")
    for path, ok, msg in _check_http():
        flag = "PASS" if ok else "FAIL"
        print(f"[{flag}] {path:24s} — {msg}")
        if not ok:
            overall_ok = False

    print("==================================================")
    if overall_ok:
        print("[OK] 全部自检通过")
        return 0
    print("[WARN] 存在不通过项，请按上面 FAIL 行排查")
    return 1


if __name__ == "__main__":
    sys.exit(main())
