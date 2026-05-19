"""
Runtime configuration export/import service.

This module packages the mutable SmartAsk resources that should survive code
deployments: JSON configs plus Bookshelf metadata stored in PostgreSQL. Imports
are intentionally conservative: dry-run is supported, and non-dry-run imports
create a rollback bundle before any write.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List

from psycopg2.extras import Json, RealDictCursor

from bookshelf_repository import BookshelfRepository
from config_manager import get_default_datasource
from system_log_store import SYSTEM_LOG_SCHEMA_SQL


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
CONFIG_DIR = os.getenv("SMARTASK_CONFIG_DIR") or os.path.join(BASE_DIR, "config")
BACKUP_DIR = os.getenv("SMARTASK_RUNTIME_BACKUP_DIR") or os.path.join(BASE_DIR, "backups", "runtime")

RUNTIME_CONFIG_FILES = [
    "datasources.json",
    "ai_settings.json",
    "feishu_sync.json",
    "sql_prompts.json",
    "app_config.json",
    "employee_permissions.json",
    "data_permissions.json",
    "rbac_permissions.json",
    "organization_trees.json",
    "feature_flags.json",
    "ask_flow.json",
    "query_history.json",
    "smartask_report_history.json",
]

CONFIG_FILE_LABELS = {
    "datasources.json": "数据源配置",
    "ai_settings.json": "模型服务配置",
    "feishu_sync.json": "飞书同步配置",
    "sql_prompts.json": "SQL 提示词",
    "app_config.json": "应用配置",
    "employee_permissions.json": "员工权限",
    "data_permissions.json": "数据集权限",
    "rbac_permissions.json": "功能权限/RBAC",
    "organization_trees.json": "组织树",
    "feature_flags.json": "功能开关",
    "ask_flow.json": "问数流程配置",
    "query_history.json": "问数历史",
    "smartask_report_history.json": "问数报告历史",
}

EXCLUDED_CONFIG_FILES = {
    "auth_tokens.json",
    "datasources.local.json",
    "feishu_sync.local.json",
}

BOOKSHELF_TABLES = [
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

SYSTEM_TABLES = [
    "system_event_logs",
]

RUNTIME_TABLES = [*BOOKSHELF_TABLES, *SYSTEM_TABLES]

DELETE_ORDER = list(reversed(RUNTIME_TABLES))


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _safe_config_filename(filename: str) -> str | None:
    filename = os.path.basename(str(filename or "").strip())
    if not filename.endswith(".json") or filename in EXCLUDED_CONFIG_FILES:
        return None
    return filename


def _read_json_file(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_json_file(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=_json_default)


def _log_file_sources() -> List[Dict[str, str]]:
    return [
        {
            "root": BASE_DIR,
            "directory": os.path.join(BASE_DIR, "logs"),
            "relative_dir": "logs",
            "prefix": "feishu_sync_",
            "suffix": ".log",
        },
        {
            "root": BASE_DIR,
            "directory": os.path.join(CURRENT_DIR, "logs"),
            "relative_dir": "backend/logs",
            "prefix": "system_event_logs",
            "suffix": ".jsonl",
        },
    ]


def _collect_log_files() -> Dict[str, str]:
    files: Dict[str, str] = {}
    for source in _log_file_sources():
        directory = source["directory"]
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            if not name.startswith(source["prefix"]) or not name.endswith(source["suffix"]):
                continue
            path = os.path.join(directory, name)
            if not os.path.isfile(path):
                continue
            rel_path = f"{source['relative_dir']}/{name}".replace("\\", "/")
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    files[rel_path] = fh.read()
            except Exception as exc:
                files[rel_path] = f"__error__:{exc}"
    return files


def _safe_log_file_path(relative_path: str) -> str | None:
    normalized = str(relative_path or "").replace("\\", "/").strip().lstrip("/")
    if normalized.startswith("../") or "/../" in normalized:
        return None
    allowed_prefixes = ("logs/feishu_sync_", "backend/logs/system_event_logs")
    allowed_suffixes = (".log", ".jsonl")
    if not normalized.startswith(allowed_prefixes) or not normalized.endswith(allowed_suffixes):
        return None
    target = os.path.abspath(os.path.join(BASE_DIR, *normalized.split("/")))
    base = os.path.abspath(BASE_DIR)
    if os.path.commonpath([base, target]) != base:
        return None
    return target


def _line_count(text: Any) -> int:
    if not isinstance(text, str) or not text:
        return 0
    return len([line for line in text.splitlines() if line.strip()])


def _byte_size(text: Any) -> int:
    if not isinstance(text, str) or not text:
        return 0
    return len(text.encode("utf-8"))


def _json_size(payload: Any) -> int:
    try:
        return _byte_size(json.dumps(payload, ensure_ascii=False, default=_json_default))
    except Exception:
        return 0


def _runtime_config_summary(configs: Dict[str, Any]) -> List[Dict[str, Any]]:
    details: List[Dict[str, Any]] = []
    for filename in RUNTIME_CONFIG_FILES:
        if filename not in configs:
            continue
        payload = configs.get(filename)
        count = 1
        description = "配置已包含"
        if isinstance(payload, dict):
            if filename == "employee_permissions.json":
                employees = payload.get("employees") if isinstance(payload.get("employees"), list) else []
                enabled = sum(1 for item in employees if isinstance(item, dict) and item.get("enabled") is not False)
                count = len(employees)
                description = f"{enabled} 个启用员工"
            elif filename == "organization_trees.json":
                tree_types = payload.get("tree_types") if isinstance(payload.get("tree_types"), list) else []
                nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []
                enabled_nodes = sum(1 for item in nodes if isinstance(item, dict) and item.get("enabled") is not False)
                count = len(nodes)
                description = f"{len(tree_types)} 个树类型，{enabled_nodes} 个启用节点"
            elif filename == "data_permissions.json":
                rules = payload.get("rules") if isinstance(payload.get("rules"), dict) else {}
                org_tree_rules = sum(1 for item in rules.values() if isinstance(item, dict) and item.get("mode") == "org_tree")
                count = len(rules)
                description = f"{org_tree_rules} 条组织树规则"
            elif filename == "rbac_permissions.json":
                roles = payload.get("roles") if isinstance(payload.get("roles"), list) else []
                groups = payload.get("groups") if isinstance(payload.get("groups"), list) else []
                count = len(roles)
                description = f"{len(roles)} 个角色，{len(groups)} 个权限组"
            elif filename == "feature_flags.json":
                features = payload.get("features") if isinstance(payload.get("features"), dict) else {}
                count = len(features)
                description = "功能显示/操作开关"
            elif filename == "ask_flow.json":
                count = 1
                description = "问数流程编排与界面展示配置"
            elif filename in {"query_history.json", "smartask_report_history.json"}:
                count = len(payload)
                description = "按用户隔离的历史记录"
            else:
                count = len(payload)
        elif isinstance(payload, list):
            count = len(payload)
        details.append(
            {
                "file": filename,
                "label": CONFIG_FILE_LABELS.get(filename, filename),
                "count": count,
                "description": description,
                "size": _json_size(payload),
            }
        )
    return details


def _permission_resource_counts(configs: Dict[str, Any]) -> Dict[str, Any]:
    employees_payload = configs.get("employee_permissions.json") or {}
    employees = employees_payload.get("employees") if isinstance(employees_payload, dict) else []
    employees = employees if isinstance(employees, list) else []

    org_payload = configs.get("organization_trees.json") or {}
    tree_types = org_payload.get("tree_types") if isinstance(org_payload, dict) and isinstance(org_payload.get("tree_types"), list) else []
    org_nodes = org_payload.get("nodes") if isinstance(org_payload, dict) and isinstance(org_payload.get("nodes"), list) else []

    data_payload = configs.get("data_permissions.json") or {}
    data_rules = data_payload.get("rules") if isinstance(data_payload, dict) and isinstance(data_payload.get("rules"), dict) else {}

    rbac_payload = configs.get("rbac_permissions.json") or {}
    roles = rbac_payload.get("roles") if isinstance(rbac_payload, dict) and isinstance(rbac_payload.get("roles"), list) else []
    groups = rbac_payload.get("groups") if isinstance(rbac_payload, dict) and isinstance(rbac_payload.get("groups"), list) else []

    return {
        "employees": len(employees),
        "enabled_employees": sum(1 for item in employees if isinstance(item, dict) and item.get("enabled") is not False),
        "admin_employees": sum(1 for item in employees if isinstance(item, dict) and item.get("role") in {"admin", "business_admin"}),
        "organization_tree_types": len(tree_types),
        "organization_nodes": len(org_nodes),
        "enabled_organization_nodes": sum(1 for item in org_nodes if isinstance(item, dict) and item.get("enabled") is not False),
        "data_permission_rules": len(data_rules),
        "org_tree_data_permission_rules": sum(1 for item in data_rules.values() if isinstance(item, dict) and item.get("mode") == "org_tree"),
        "rbac_roles": len(roles),
        "rbac_groups": len(groups),
    }


def _merge_log_text(existing: str, incoming: str) -> str:
    existing_lines = existing.splitlines()
    seen = set(existing_lines)
    merged = list(existing_lines)
    for line in incoming.splitlines():
        if line in seen:
            continue
        merged.append(line)
        seen.add(line)
    return "\n".join(merged) + ("\n" if merged else "")


def _write_log_files(log_files: Dict[str, Any], mode: str) -> List[str]:
    written: List[str] = []
    for rel_path, content in (log_files or {}).items():
        if not isinstance(content, str) or content.startswith("__error__:"):
            continue
        target_path = _safe_log_file_path(rel_path)
        if not target_path:
            continue
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        if mode == "replace" or not os.path.exists(target_path):
            output = content if content.endswith("\n") or not content else content + "\n"
        else:
            with open(target_path, "r", encoding="utf-8") as fh:
                output = _merge_log_text(fh.read(), content)
        with open(target_path, "w", encoding="utf-8") as fh:
            fh.write(output)
        written.append(str(rel_path))
    return written


def _ensure_optional_tables(cur) -> None:
    cur.execute(SYSTEM_LOG_SCHEMA_SQL)
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
            id BIGSERIAL PRIMARY KEY,
            dataset_id BIGINT NOT NULL,
            config_json JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(dataset_id)
        );
        """
    )
    cur.execute("ALTER TABLE bs_schema_definitions ADD COLUMN IF NOT EXISTS source_id BIGINT;")


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


def _prepare_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return Json(value)
    return value


def _normalize_row(table_name: str, row: Dict[str, Any], fallback_source_id: int) -> Dict[str, Any]:
    item = dict(row)
    if table_name in {"bs_datasets", "bs_schema_definitions"}:
        item["source_id"] = int(item.get("source_id") or fallback_source_id)
    return item


def _reset_sequence(cur, table_name: str) -> None:
    cur.execute("SELECT pg_get_serial_sequence(%s, 'id') AS seq_name;", (table_name,))
    row = cur.fetchone()
    seq_name = row["seq_name"] if row else None
    if not seq_name:
        return
    cur.execute(f"SELECT COALESCE(MAX(id), 0) AS max_id FROM {table_name};")
    max_id = int((cur.fetchone() or {}).get("max_id") or 0)
    cur.execute("SELECT setval(%s, %s, %s);", (seq_name, max_id if max_id > 0 else 1, max_id > 0))


def _upsert_rows(cur, table_name: str, rows: Iterable[Dict[str, Any]], fallback_source_id: int) -> int:
    inserted = 0
    available_columns = set(_get_table_columns(cur, table_name))
    natural_conflicts = {
        "bs_dataset_report_config": ["dataset_id"],
        "bs_dataset_external_configs": ["dataset_id", "config_type", "config_key"],
    }
    for raw_row in rows:
        row = _normalize_row(table_name, raw_row, fallback_source_id)
        row = {key: value for key, value in row.items() if key in available_columns}
        if not row:
            continue

        columns = list(row.keys())
        placeholders = ", ".join(["%s"] * len(columns))
        conflict_columns = natural_conflicts.get(table_name)
        if not conflict_columns or not all(column in columns for column in conflict_columns):
            conflict_columns = ["id"] if "id" in columns else []
        update_columns = [column for column in columns if column not in set(conflict_columns + ["id"])]
        values = [_prepare_value(row[column]) for column in columns]
        sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        if conflict_columns and update_columns:
            assignments = ", ".join([f"{column} = EXCLUDED.{column}" for column in update_columns])
            sql += f" ON CONFLICT ({', '.join(conflict_columns)}) DO UPDATE SET {assignments}"
        elif conflict_columns:
            sql += f" ON CONFLICT ({', '.join(conflict_columns)}) DO NOTHING"
        sql += ";"
        cur.execute(sql, values)
        inserted += 1
    return inserted


def export_runtime_bundle(output_path: str | None = None) -> Dict[str, Any]:
    repo = BookshelfRepository()
    repo.ensure_schema()

    bundle: Dict[str, Any] = {
        "version": 2,
        "type": "smartask_runtime_bundle",
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "configs": {},
        "bookshelf": {"tables": {}},
        "log_files": {},
        "manifest": {
            "config_files": list(RUNTIME_CONFIG_FILES),
            "bookshelf_tables": list(BOOKSHELF_TABLES),
            "system_tables": list(SYSTEM_TABLES),
            "runtime_tables": list(RUNTIME_TABLES),
            "excluded_files": sorted(EXCLUDED_CONFIG_FILES),
        },
    }

    for filename in RUNTIME_CONFIG_FILES:
        path = os.path.join(CONFIG_DIR, filename)
        if not os.path.exists(path):
            continue
        try:
            bundle["configs"][filename] = _read_json_file(path)
        except Exception as exc:
            bundle["configs"][filename] = {"__error__": str(exc)}

    with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        _ensure_optional_tables(cur)
        for table in RUNTIME_TABLES:
            cur.execute(f"SELECT * FROM {table} ORDER BY id ASC;")
            bundle["bookshelf"]["tables"][table] = [dict(row) for row in cur.fetchall()]

    bundle["log_files"] = _collect_log_files()
    bundle["manifest"]["log_files"] = list(bundle["log_files"].keys())

    if output_path:
        _write_json_file(output_path, bundle)

    return bundle


def summarize_bundle(bundle: Dict[str, Any]) -> Dict[str, Any]:
    configs = bundle.get("configs") or {}
    tables = (bundle.get("bookshelf") or {}).get("tables") or bundle.get("tables") or {}
    log_files = bundle.get("log_files") or {}
    dataset_rows = tables.get("bs_datasets") or []
    active_dataset_count = sum(1 for row in dataset_rows if isinstance(row, dict) and row.get("is_active") is not False)
    inactive_dataset_count = sum(1 for row in dataset_rows if isinstance(row, dict) and row.get("is_active") is False)
    return {
        "type": bundle.get("type") or "unknown",
        "version": bundle.get("version"),
        "exported_at": bundle.get("exported_at"),
        "config_counts": {name: 1 for name in configs.keys()},
        "config_details": _runtime_config_summary(configs),
        "permission_counts": _permission_resource_counts(configs),
        "table_counts": {name: len(rows or []) for name, rows in tables.items()},
        "dataset_counts": {
            "active": active_dataset_count,
            "inactive": inactive_dataset_count,
            "total": len(dataset_rows or []),
        },
        "config_files": list(configs.keys()),
        "log_file_counts": {name: _line_count(content) for name, content in log_files.items()},
        "log_file_total": sum(_line_count(content) for content in log_files.values()),
        "log_file_sizes": {name: _byte_size(content) for name, content in log_files.items()},
        "log_file_size_total": sum(_byte_size(content) for content in log_files.values()),
    }


def create_runtime_backup(reason: str = "manual") -> Dict[str, Any]:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    output_path = os.path.join(BACKUP_DIR, f"runtime_backup_{_timestamp()}.json")
    bundle = export_runtime_bundle(output_path)
    return {
        "ok": True,
        "reason": reason,
        "path": output_path,
        "summary": summarize_bundle(bundle),
    }


def list_runtime_backups(limit: int = 20) -> List[Dict[str, Any]]:
    if not os.path.isdir(BACKUP_DIR):
        return []
    files = []
    for name in os.listdir(BACKUP_DIR):
        if not name.endswith(".json"):
            continue
        path = os.path.join(BACKUP_DIR, name)
        stat = os.stat(path)
        files.append(
            {
                "filename": name,
                "path": path,
                "size": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            }
        )
    return sorted(files, key=lambda item: item["modified_at"], reverse=True)[:limit]


def preview_runtime_import(bundle: Dict[str, Any], overwrite_configs: bool = False, mode: str = "merge") -> Dict[str, Any]:
    configs = bundle.get("configs") or {}
    tables = (bundle.get("bookshelf") or {}).get("tables") or bundle.get("tables") or {}
    log_files = bundle.get("log_files") or {}

    config_plan = []
    for raw_name, payload in configs.items():
        filename = _safe_config_filename(raw_name)
        if not filename or (isinstance(payload, dict) and "__error__" in payload):
            continue
        target_path = os.path.join(CONFIG_DIR, filename)
        exists = os.path.exists(target_path)
        action = "overwrite" if exists and overwrite_configs else ("skip_existing" if exists else "create")
        config_plan.append({"file": filename, "exists": exists, "action": action})

    repo = BookshelfRepository()
    repo.ensure_schema()
    table_plan = {}
    with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        _ensure_optional_tables(cur)
        for table_name in RUNTIME_TABLES:
            incoming_rows = tables.get(table_name) or []
            cur.execute(f"SELECT COUNT(*) AS count FROM {table_name};")
            existing_count = int((cur.fetchone() or {}).get("count") or 0)
            incoming_ids = [row.get("id") for row in incoming_rows if isinstance(row, dict) and row.get("id") is not None]
            overlap = 0
            if incoming_ids:
                cur.execute(f"SELECT COUNT(*) AS count FROM {table_name} WHERE id = ANY(%s);", (incoming_ids,))
                overlap = int((cur.fetchone() or {}).get("count") or 0)
            table_plan[table_name] = {
                "incoming": len(incoming_rows),
                "existing": existing_count,
                "id_overlaps": overlap,
                "action": "replace" if mode == "replace" else "merge",
            }

    log_file_plan = []
    for rel_path, content in log_files.items():
        target_path = _safe_log_file_path(rel_path)
        if not target_path or not isinstance(content, str) or content.startswith("__error__:"):
            continue
        existing_text = ""
        if os.path.exists(target_path):
            try:
                with open(target_path, "r", encoding="utf-8") as fh:
                    existing_text = fh.read()
            except Exception:
                existing_text = ""
        log_file_plan.append(
            {
                "file": rel_path,
                "incoming_lines": _line_count(content),
                "existing_lines": _line_count(existing_text),
                "incoming_size": _byte_size(content),
                "existing_size": _byte_size(existing_text),
                "action": "replace" if mode == "replace" else ("merge" if os.path.exists(target_path) else "create"),
            }
        )

    return {
        "ok": True,
        "dry_run": True,
        "mode": mode,
        "overwrite_configs": overwrite_configs,
        "summary": summarize_bundle(bundle),
        "config_plan": config_plan,
        "table_plan": table_plan,
        "log_file_plan": log_file_plan,
        "warnings": [
            "replace 模式会先清空书架运行态表，再写入导入包。"
        ] if mode == "replace" else [],
    }


def import_runtime_bundle(
    bundle: Dict[str, Any],
    *,
    mode: str = "merge",
    overwrite_configs: bool = False,
    dry_run: bool = False,
    auto_backup: bool = True,
) -> Dict[str, Any]:
    mode = mode if mode in {"merge", "replace"} else "merge"
    preview = preview_runtime_import(bundle, overwrite_configs=overwrite_configs, mode=mode)
    if dry_run:
        return preview

    backup = create_runtime_backup("before_runtime_import") if auto_backup else None
    configs = bundle.get("configs") or {}
    tables = (bundle.get("bookshelf") or {}).get("tables") or bundle.get("tables") or {}
    log_files = bundle.get("log_files") or {}

    written_configs: List[str] = []
    skipped_configs: List[str] = []

    for raw_name, payload in configs.items():
        filename = _safe_config_filename(raw_name)
        if not filename or (isinstance(payload, dict) and "__error__" in payload):
            continue
        target_path = os.path.join(CONFIG_DIR, filename)
        if os.path.exists(target_path) and not overwrite_configs:
            skipped_configs.append(filename)
            continue
        _write_json_file(target_path, payload)
        written_configs.append(filename)

    repo = BookshelfRepository()
    repo.ensure_schema()
    fallback_source = get_default_datasource() or {}
    fallback_source_id = int(fallback_source.get("id") or 1)
    imported_counts: Dict[str, int] = {}

    with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        _ensure_optional_tables(cur)
        if mode == "replace":
            for table_name in DELETE_ORDER:
                cur.execute(f"DELETE FROM {table_name};")

        for table_name in RUNTIME_TABLES:
            rows = tables.get(table_name) or []
            imported_counts[table_name] = _upsert_rows(cur, table_name, rows, fallback_source_id)

        for table_name in RUNTIME_TABLES:
            _reset_sequence(cur, table_name)
        conn.commit()

    written_log_files = _write_log_files(log_files, mode)

    return {
        "ok": True,
        "dry_run": False,
        "mode": mode,
        "overwrite_configs": overwrite_configs,
        "backup": backup,
        "written_configs": written_configs,
        "skipped_configs": skipped_configs,
        "imported_counts": imported_counts,
        "written_log_files": written_log_files,
        "preview": preview,
    }


def load_bundle_file(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Bundle not found: {path}")
    payload = _read_json_file(path)
    if not isinstance(payload, dict):
        raise ValueError("Invalid runtime bundle: root must be an object")
    return payload
