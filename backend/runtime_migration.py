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
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Tuple

from psycopg2.extras import Json, RealDictCursor

from bookshelf_repository import BookshelfRepository
from config_manager import get_default_datasource
from system_log_store import SYSTEM_LOG_SCHEMA_SQL


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
CONFIG_DIR = os.getenv("SMARTASK_CONFIG_DIR") or os.path.join(BASE_DIR, "config")
BACKUP_DIR = os.getenv("SMARTASK_RUNTIME_BACKUP_DIR") or os.path.join(BASE_DIR, "backups", "runtime")
RUNTIME_LOG_RETENTION_DAYS = int(os.getenv("SMARTASK_RUNTIME_LOG_RETENTION_DAYS", "7") or "7")

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
    "advanced_capabilities.json",
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
    "advanced_capabilities.json": "进阶问数能力配置",
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
    "bs_dataset_transforms",
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
DATASET_REFERENCE_TABLES = {
    "bs_dataset_synonyms",
    "bs_dataset_transforms",
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
}

NATURAL_KEY_COLUMNS = {
    "bs_datasets": ["dataset_name"],
    "bs_dataset_synonyms": ["dataset_id", "normalized_synonym"],
    "bs_dataset_transforms": ["dataset_id", "target_name"],
    "bs_lld_documents": ["dataset_id", "title"],
    "bs_data_dictionary_items": ["dataset_id", "table_name", "column_name", "jsonb_key"],
    "bs_schema_definitions": ["dataset_id", "table_name"],
    "bs_golden_sql_samples": ["dataset_id", "question"],
    "bs_agent_prompt_fragments": ["dataset_id", "agent_no", "prompt_key"],
    "bs_common_questions": ["dataset_id", "question_text"],
    "bs_regression_cases": ["dataset_id", "case_type", "question_text"],
    "bs_dataset_external_configs": ["dataset_id", "config_type", "config_key"],
    "bs_dataset_report_config": ["dataset_id"],
}

DEDUP_ORDER_BY = {
    "bs_golden_sql_samples": "is_active DESC, quality_score DESC NULLS LAST, updated_at DESC NULLS LAST, id ASC",
    "bs_common_questions": "is_active DESC, sort_order ASC, updated_at DESC NULLS LAST, id ASC",
    "bs_regression_cases": "is_active DESC, sort_order ASC, updated_at DESC NULLS LAST, id ASC",
}


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


def _safe_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_line(value: Any, limit: int = 240) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text.splitlines()[0][:limit]


def _incoming_dataset_ids(tables: Dict[str, Any]) -> set[int]:
    result: set[int] = set()
    for row in tables.get("bs_datasets") or []:
        if not isinstance(row, dict):
            continue
        dataset_id = _safe_int(row.get("id"))
        if dataset_id is not None:
            result.add(dataset_id)
    return result


def _existing_table_ids(cur, table_name: str) -> set[int]:
    cur.execute(f"SELECT id FROM {table_name};")
    return {
        int(row["id"])
        for row in cur.fetchall()
        if row.get("id") is not None
    }


def _effective_dataset_ids_for_import(cur, tables: Dict[str, Any], mode: str) -> set[int]:
    incoming = _incoming_dataset_ids(tables)
    if mode == "replace":
        return incoming
    return _existing_table_ids(cur, "bs_datasets") | incoming


def _skip_detail(kind: str, reason: str, **extra) -> Dict[str, Any]:
    return {
        "kind": kind,
        "reason": reason,
        **{key: value for key, value in extra.items() if value is not None and value != ""},
    }


def _filter_dataset_keyed_dict(
    mapping: Any,
    valid_dataset_ids: set[int],
    dataset_id_map: Dict[int, int] | None = None,
    *,
    file: str,
    section: str,
    skipped: List[Dict[str, Any]],
) -> Any:
    if not isinstance(mapping, dict):
        return mapping
    clean = {}
    for raw_key, value in mapping.items():
        dataset_id = _safe_int(raw_key)
        if isinstance(value, dict):
            dataset_id = _safe_int(value.get("dataset_id")) or dataset_id
        if dataset_id is not None and dataset_id_map and dataset_id in dataset_id_map:
            dataset_id = dataset_id_map[dataset_id]
        if dataset_id is None:
            skipped.append(_skip_detail("config_ref", "无法识别数据集 ID，已跳过", file=file, section=section, key=str(raw_key)))
            continue
        if dataset_id not in valid_dataset_ids:
            skipped.append(
                _skip_detail(
                    "config_ref",
                    "引用的数据集在当前环境和导入包中不存在，已跳过",
                    file=file,
                    section=section,
                    dataset_id=dataset_id,
                    key=str(raw_key),
                )
            )
            continue
        if isinstance(value, dict):
            value = {**value, "dataset_id": dataset_id}
        clean[str(dataset_id)] = value
    return clean


def _sanitize_config_payload(
    filename: str,
    payload: Any,
    valid_dataset_ids: set[int],
    dataset_id_map: Dict[int, int] | None = None,
) -> tuple[Any, List[Dict[str, Any]]]:
    result = deepcopy(payload)
    skipped: List[Dict[str, Any]] = []
    if filename == "data_permissions.json" and isinstance(result, dict):
        rules = result.get("rules")
        if isinstance(rules, dict):
            result["rules"] = _filter_dataset_keyed_dict(
                rules,
                valid_dataset_ids,
                dataset_id_map,
                file=filename,
                section="rules",
                skipped=skipped,
            )
        elif isinstance(rules, list):
            clean_rules = []
            for index, item in enumerate(rules):
                dataset_id = _safe_int(item.get("dataset_id") if isinstance(item, dict) else None)
                if dataset_id is not None and dataset_id_map and dataset_id in dataset_id_map:
                    dataset_id = dataset_id_map[dataset_id]
                if dataset_id is None or dataset_id not in valid_dataset_ids:
                    skipped.append(
                        _skip_detail(
                            "config_ref",
                            "数据集权限规则未匹配到有效数据集，已跳过",
                            file=filename,
                            section="rules",
                            index=index + 1,
                            dataset_id=dataset_id,
                        )
                    )
                    continue
                clean_rules.append({**item, "dataset_id": dataset_id})
            result["rules"] = clean_rules
    elif filename == "ask_flow.json" and isinstance(result, dict):
        policies = result.get("datasetPolicies")
        if isinstance(policies, dict):
            result["datasetPolicies"] = _filter_dataset_keyed_dict(
                policies,
                valid_dataset_ids,
                dataset_id_map,
                file=filename,
                section="datasetPolicies",
                skipped=skipped,
            )
    elif filename == "rbac_permissions.json" and isinstance(result, dict):
        for role in result.get("roles") or []:
            if not isinstance(role, dict) or not isinstance(role.get("resource_permissions"), dict):
                continue
            clean_permissions = {}
            for raw_key, level in role["resource_permissions"].items():
                if str(raw_key) == "*":
                    clean_permissions[str(raw_key)] = level
                    continue
                dataset_id = _safe_int(raw_key)
                if dataset_id is not None and dataset_id_map and dataset_id in dataset_id_map:
                    dataset_id = dataset_id_map[dataset_id]
                if dataset_id is None or dataset_id not in valid_dataset_ids:
                    skipped.append(
                        _skip_detail(
                            "config_ref",
                            "角色资源权限引用的数据集不存在，已跳过",
                            file=filename,
                            section=f"roles.{role.get('id') or role.get('code') or ''}.resource_permissions",
                            dataset_id=dataset_id,
                            key=str(raw_key),
                        )
                    )
                    continue
                clean_permissions[str(dataset_id)] = level
            role["resource_permissions"] = clean_permissions
    return result, skipped


def _preview_table_skips(
    tables: Dict[str, Any],
    valid_dataset_ids: set[int],
    dataset_id_map: Dict[int, int] | None = None,
) -> List[Dict[str, Any]]:
    skipped: List[Dict[str, Any]] = []
    for table_name in RUNTIME_TABLES:
        for index, row in enumerate(tables.get(table_name) or []):
            if not isinstance(row, dict):
                skipped.append(_skip_detail("table_row", "记录不是对象，导入时会跳过", table=table_name, index=index + 1))
                continue
            if table_name in DATASET_REFERENCE_TABLES:
                dataset_id = _safe_int(row.get("dataset_id"))
                if dataset_id is not None and dataset_id_map and dataset_id in dataset_id_map:
                    dataset_id = dataset_id_map[dataset_id]
                if dataset_id is None or dataset_id not in valid_dataset_ids:
                    skipped.append(
                        _skip_detail(
                            "table_row",
                            "记录引用的数据集不存在，导入时会跳过",
                            table=table_name,
                            index=index + 1,
                            id=row.get("id"),
                            dataset_id=dataset_id,
                        )
                    )
    return skipped


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


def _runtime_log_cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=max(RUNTIME_LOG_RETENTION_DAYS, 0))


def _is_recent_log_file(path: str, cutoff: datetime) -> bool:
    try:
        modified_at = datetime.fromtimestamp(os.path.getmtime(path), timezone.utc)
        return modified_at >= cutoff
    except OSError:
        return False


def _collect_log_files(cutoff: datetime | None = None) -> Dict[str, str]:
    files: Dict[str, str] = {}
    cutoff = cutoff or _runtime_log_cutoff()
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
            if not _is_recent_log_file(path, cutoff):
                continue
            rel_path = f"{source['relative_dir']}/{name}".replace("\\", "/")
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    files[rel_path] = fh.read()
            except Exception as exc:
                files[rel_path] = f"__error__:{exc}"
    return files


def _count_log_file_lines(path: str) -> int:
    count = 0
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    count += 1
    except Exception:
        return 0
    return count


def _collect_log_file_stats(cutoff: datetime | None = None) -> Dict[str, Dict[str, int]]:
    stats: Dict[str, Dict[str, int]] = {}
    cutoff = cutoff or _runtime_log_cutoff()
    for source in _log_file_sources():
        directory = source["directory"]
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            if not name.startswith(source["prefix"]) or not name.endswith(source["suffix"]):
                continue
            path = os.path.join(directory, name)
            if not os.path.isfile(path) or not _is_recent_log_file(path, cutoff):
                continue
            rel_path = f"{source['relative_dir']}/{name}".replace("\\", "/")
            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0
            stats[rel_path] = {
                "lines": _count_log_file_lines(path),
                "size": size,
            }
    return stats


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
            elif filename == "advanced_capabilities.json":
                skills = payload.get("skills") if isinstance(payload.get("skills"), list) else []
                enabled = sum(1 for item in skills if isinstance(item, dict) and item.get("enabled") is not False)
                count = len(skills) or 1
                description = f"{enabled} 个启用进阶 Skill/工具"
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


def _write_log_files(log_files: Dict[str, Any], mode: str, skipped_log_files: List[Dict[str, Any]] | None = None) -> List[str]:
    written: List[str] = []
    for rel_path, content in (log_files or {}).items():
        if not isinstance(content, str) or content.startswith("__error__:"):
            if skipped_log_files is not None:
                skipped_log_files.append(_skip_detail("log_file", "日志内容无效，已跳过", file=str(rel_path)))
            continue
        target_path = _safe_log_file_path(rel_path)
        if not target_path:
            if skipped_log_files is not None:
                skipped_log_files.append(_skip_detail("log_file", "日志路径不在允许范围内，已跳过", file=str(rel_path)))
            continue
        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            if mode == "replace" or not os.path.exists(target_path):
                output = content if content.endswith("\n") or not content else content + "\n"
            else:
                with open(target_path, "r", encoding="utf-8") as fh:
                    output = _merge_log_text(fh.read(), content)
            with open(target_path, "w", encoding="utf-8") as fh:
                fh.write(output)
            written.append(str(rel_path))
        except Exception as exc:
            if skipped_log_files is not None:
                skipped_log_files.append(_skip_detail("log_file", "日志文件写入失败，已跳过", file=str(rel_path), error=_first_line(exc)))
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


def _normalize_row(
    table_name: str,
    row: Dict[str, Any],
    fallback_source_id: int,
    dataset_id_map: Dict[int, int] | None = None,
) -> Dict[str, Any]:
    item = dict(row)
    if table_name in {"bs_datasets", "bs_schema_definitions"}:
        item["source_id"] = int(item.get("source_id") or fallback_source_id)
    if table_name == "bs_dataset_synonyms":
        if not item.get("normalized_synonym"):
            item["normalized_synonym"] = "".join(str(item.get("synonym") or "").split()).lower()
    if table_name in DATASET_REFERENCE_TABLES and "dataset_id" in item:
        dataset_id = _safe_int(item.get("dataset_id"))
        if dataset_id is not None and dataset_id_map and dataset_id in dataset_id_map:
            item["dataset_id"] = dataset_id_map[dataset_id]
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


def _natural_key_columns(table_name: str, available_columns: set[str]) -> List[str]:
    columns = NATURAL_KEY_COLUMNS.get(table_name) or []
    return [column for column in columns if column in available_columns]


def _dedupe_table_by_natural_key(cur, table_name: str, available_columns: set[str]) -> int:
    key_columns = _natural_key_columns(table_name, available_columns)
    if not key_columns:
        return 0
    partition = ", ".join(key_columns)
    ordering = DEDUP_ORDER_BY.get(table_name)
    if not ordering:
        ordering_parts = []
        if "is_active" in available_columns:
            ordering_parts.append("is_active DESC NULLS LAST")
        if "updated_at" in available_columns:
            ordering_parts.append("updated_at DESC NULLS LAST")
        ordering_parts.append("id ASC")
        ordering = ", ".join(ordering_parts)
    cur.execute(
        f"""
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (PARTITION BY {partition} ORDER BY {ordering}) AS rn
            FROM {table_name}
        )
        DELETE FROM {table_name}
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1);
        """
    )
    return int(cur.rowcount or 0)


def _existing_natural_key_id(cur, table_name: str, row: Dict[str, Any], key_columns: List[str]) -> int | None:
    if not key_columns or any(column not in row for column in key_columns):
        return None
    where_clause = " AND ".join([f"{column} IS NOT DISTINCT FROM %s" for column in key_columns])
    values = [row.get(column) for column in key_columns]
    cur.execute(
        f"SELECT id FROM {table_name} WHERE {where_clause} ORDER BY id ASC LIMIT 1;",
        values,
    )
    existing = cur.fetchone()
    if not existing:
        return None
    return _safe_int(existing.get("id") if isinstance(existing, dict) else existing[0])


def _build_dataset_id_map(cur, dataset_rows: Iterable[Dict[str, Any]], fallback_source_id: int, mode: str) -> Dict[int, int]:
    if mode == "replace":
        return {}
    result: Dict[int, int] = {}
    for raw_row in dataset_rows or []:
        if not isinstance(raw_row, dict):
            continue
        incoming_id = _safe_int(raw_row.get("id"))
        if incoming_id is None:
            continue
        name = str(raw_row.get("dataset_name") or "").strip()
        code = str(raw_row.get("dataset_code") or "").strip()
        existing_id = None
        if name:
            cur.execute("SELECT id FROM bs_datasets WHERE dataset_name = %s LIMIT 1;", (name,))
            r = cur.fetchone()
            if r:
                existing_id = _safe_int(r.get("id") if isinstance(r, dict) else r[0])
        if existing_id is None and code:
            cur.execute("SELECT id FROM bs_datasets WHERE dataset_code = %s LIMIT 1;", (code,))
            r = cur.fetchone()
            if r:
                existing_id = _safe_int(r.get("id") if isinstance(r, dict) else r[0])
        if existing_id is not None:
            result[incoming_id] = existing_id
        else:
            result[incoming_id] = incoming_id
    return result


def _upsert_rows(
    cur,
    table_name: str,
    rows: Iterable[Dict[str, Any]],
    fallback_source_id: int,
    skipped_rows: List[Dict[str, Any]] | None = None,
    dataset_id_map: Dict[int, int] | None = None,
) -> int:
    inserted = 0
    available_columns = set(_get_table_columns(cur, table_name))
    natural_key_columns = _natural_key_columns(table_name, available_columns)
    _dedupe_table_by_natural_key(cur, table_name, available_columns)
    for index, raw_row in enumerate(rows or []):
        if not isinstance(raw_row, dict):
            if skipped_rows is not None:
                skipped_rows.append(_skip_detail("table_row", "记录不是对象，已跳过", table=table_name, index=index + 1))
            continue
        try:
            row = _normalize_row(table_name, raw_row, fallback_source_id, dataset_id_map)
        except Exception as exc:
            if skipped_rows is not None:
                skipped_rows.append(
                    _skip_detail(
                        "table_row",
                        "记录清洗失败，已跳过",
                        table=table_name,
                        index=index + 1,
                        id=raw_row.get("id"),
                        error=_first_line(exc),
                    )
                )
            continue
        row = {key: value for key, value in row.items() if key in available_columns}
        if not row:
            if skipped_rows is not None:
                skipped_rows.append(
                    _skip_detail("table_row", "记录没有可写入字段，已跳过", table=table_name, index=index + 1, id=raw_row.get("id"))
                )
            continue
        existing_id = _existing_natural_key_id(cur, table_name, row, natural_key_columns)
        if existing_id is not None and "id" in available_columns:
            row["id"] = existing_id
        elif natural_key_columns:
            # 增量新记录：移除旧ID，使用数据库自增主键，防止覆盖同ID的其他已有记录
            row.pop("id", None)

        columns = list(row.keys())
        placeholders = ", ".join(["%s"] * len(columns))
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
        cur.execute("SAVEPOINT smartask_runtime_import_row;")
        try:
            cur.execute(sql, values)
            affected = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
            cur.execute("RELEASE SAVEPOINT smartask_runtime_import_row;")
            inserted += affected
        except Exception as exc:
            cur.execute("ROLLBACK TO SAVEPOINT smartask_runtime_import_row;")
            cur.execute("RELEASE SAVEPOINT smartask_runtime_import_row;")
            if skipped_rows is not None:
                skipped_rows.append(
                    _skip_detail(
                        "table_row",
                        "记录与当前环境不匹配，已跳过",
                        table=table_name,
                        index=index + 1,
                        id=raw_row.get("id"),
                        dataset_id=raw_row.get("dataset_id"),
                        error=_first_line(exc),
                    )
                )
    return inserted


def export_runtime_bundle(output_path: str | None = None) -> Dict[str, Any]:
    repo = BookshelfRepository()
    repo.ensure_schema()
    log_cutoff = _runtime_log_cutoff()

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
            "log_retention_days": RUNTIME_LOG_RETENTION_DAYS,
            "log_cutoff": log_cutoff.isoformat(),
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
            if table == "system_event_logs":
                cur.execute(
                    "SELECT * FROM system_event_logs WHERE created_at >= %s ORDER BY id ASC;",
                    (log_cutoff,),
                )
            else:
                cur.execute(f"SELECT * FROM {table} ORDER BY id ASC;")
            bundle["bookshelf"]["tables"][table] = [dict(row) for row in cur.fetchall()]

    bundle["log_files"] = _collect_log_files(log_cutoff)
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


def summarize_runtime_state() -> Dict[str, Any]:
    repo = BookshelfRepository()
    repo.ensure_schema()
    log_cutoff = _runtime_log_cutoff()
    configs: Dict[str, Any] = {}
    for filename in RUNTIME_CONFIG_FILES:
        path = os.path.join(CONFIG_DIR, filename)
        if not os.path.exists(path):
            continue
        try:
            configs[filename] = _read_json_file(path)
        except Exception as exc:
            configs[filename] = {"__error__": str(exc)}

    table_counts: Dict[str, int] = {}
    dataset_counts = {"active": 0, "inactive": 0, "total": 0}
    with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        _ensure_optional_tables(cur)
        for table in RUNTIME_TABLES:
            try:
                if table == "system_event_logs":
                    cur.execute("SELECT COUNT(*) AS count FROM system_event_logs WHERE created_at >= %s;", (log_cutoff,))
                else:
                    cur.execute(f"SELECT COUNT(*) AS count FROM {table};")
                table_counts[table] = int((cur.fetchone() or {}).get("count") or 0)
            except Exception:
                table_counts[table] = 0
        try:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE is_active IS NOT FALSE) AS active,
                    COUNT(*) FILTER (WHERE is_active IS FALSE) AS inactive
                FROM bs_datasets;
                """
            )
            row = cur.fetchone() or {}
            dataset_counts = {
                "active": int(row.get("active") or 0),
                "inactive": int(row.get("inactive") or 0),
                "total": int(row.get("total") or 0),
            }
        except Exception:
            dataset_counts = {
                "active": table_counts.get("bs_datasets", 0),
                "inactive": 0,
                "total": table_counts.get("bs_datasets", 0),
            }

    log_stats = _collect_log_file_stats(log_cutoff)
    return {
        "type": "smartask_runtime_bundle",
        "version": 2,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "config_counts": {name: 1 for name in configs.keys()},
        "config_details": _runtime_config_summary(configs),
        "permission_counts": _permission_resource_counts(configs),
        "table_counts": table_counts,
        "dataset_counts": dataset_counts,
        "config_files": list(configs.keys()),
        "log_file_counts": {name: item["lines"] for name, item in log_stats.items()},
        "log_file_total": sum(item["lines"] for item in log_stats.values()),
        "log_file_sizes": {name: item["size"] for name, item in log_stats.items()},
        "log_file_size_total": sum(item["size"] for item in log_stats.values()),
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
    skipped_config_items: List[Dict[str, Any]] = []
    for raw_name, payload in configs.items():
        filename = _safe_config_filename(raw_name)
        if not filename or (isinstance(payload, dict) and "__error__" in payload):
            skipped_config_items.append(_skip_detail("config_file", "配置文件无效或不在允许范围内，已跳过", file=str(raw_name)))
            continue

    repo = BookshelfRepository()
    repo.ensure_schema()
    table_plan = {}
    skipped_table_rows_preview: List[Dict[str, Any]] = []
    with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        _ensure_optional_tables(cur)
        fallback_source = get_default_datasource() or {}
        fallback_source_id = int(fallback_source.get("id") or 1)
        dataset_id_map = _build_dataset_id_map(cur, tables.get("bs_datasets") or [], fallback_source_id, mode)
        valid_dataset_ids = _existing_table_ids(cur, "bs_datasets") | _incoming_dataset_ids(tables)
        if dataset_id_map:
            valid_dataset_ids |= set(dataset_id_map.values()) | set(dataset_id_map.keys())
        for raw_name, payload in configs.items():
            filename = _safe_config_filename(raw_name)
            if not filename or (isinstance(payload, dict) and "__error__" in payload):
                continue
            _, config_skips = _sanitize_config_payload(filename, payload, valid_dataset_ids, dataset_id_map)
            skipped_config_items.extend(config_skips)
            target_path = os.path.join(CONFIG_DIR, filename)
            exists = os.path.exists(target_path)
            if not exists:
                action = "create"
                detail_text = "全新创建"
            elif overwrite_configs:
                action = "overwrite"
                detail_text = "全量覆盖"
            else:
                action = "merge"
                # 计算预估增量项
                existing_data = _read_json_file(target_path)
                _, changes = _deep_merge_config(filename, existing_data, payload)
                detail_text = f"智能合并 (新增/更新 {changes} 项)" if changes > 0 else "已有且一致"

            config_plan.append({
                "file": filename,
                "exists": exists,
                "action": action,
                "detail_text": detail_text,
                "skipped_items": len(config_skips),
            })
        skipped_table_rows_preview = _preview_table_skips(tables, valid_dataset_ids, dataset_id_map)
        skipped_by_table: Dict[str, int] = {}
        for item in skipped_table_rows_preview:
            table = item.get("table")
            if table:
                skipped_by_table[str(table)] = skipped_by_table.get(str(table), 0) + 1
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
                "skippable": skipped_by_table.get(table_name, 0),
            }

    log_file_plan = []
    skipped_log_files: List[Dict[str, Any]] = []
    for rel_path, content in log_files.items():
        target_path = _safe_log_file_path(rel_path)
        if not target_path or not isinstance(content, str) or content.startswith("__error__:"):
            skipped_log_files.append(_skip_detail("log_file", "日志文件路径或内容无效，已跳过", file=str(rel_path)))
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

    warnings = []
    if mode == "replace":
        warnings.append("replace 模式会先清空书架运行态表，再写入导入包。")
    skipped_existing_configs = [item["file"] for item in config_plan if item.get("action") == "skip_existing"]
    if skipped_existing_configs:
        warnings.append(
            "以下 JSON 配置已存在且不会覆盖，如需让配置生效请打开“覆盖已有 JSON 配置”："
            + "、".join(skipped_existing_configs)
        )
    skipped_total = len(skipped_config_items) + len(skipped_table_rows_preview) + len(skipped_log_files)
    if skipped_total:
        warnings.append(f"检测到 {skipped_total} 个无法匹配或无效资源，正式导入时将自动跳过。")

    return {
        "ok": True,
        "dry_run": True,
        "mode": mode,
        "overwrite_configs": overwrite_configs,
        "summary": summarize_bundle(bundle),
        "config_plan": config_plan,
        "table_plan": table_plan,
        "log_file_plan": log_file_plan,
        "skipped_config_items": skipped_config_items,
        "skipped_table_rows_preview": skipped_table_rows_preview,
        "skipped_log_files": skipped_log_files,
        "warnings": warnings,
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
    skipped_config_items: List[Dict[str, Any]] = []
    skipped_table_rows: List[Dict[str, Any]] = []
    skipped_log_files: List[Dict[str, Any]] = []

    repo = BookshelfRepository()
    repo.ensure_schema()
    fallback_source = get_default_datasource() or {}
    fallback_source_id = int(fallback_source.get("id") or 1)
    imported_counts: Dict[str, int] = {}
    final_dataset_ids: set[int] = set()

    with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        _ensure_optional_tables(cur)
        if mode == "replace":
            for table_name in DELETE_ORDER:
                cur.execute(f"DELETE FROM {table_name};")
        dataset_id_map = _build_dataset_id_map(cur, tables.get("bs_datasets") or [], fallback_source_id, mode)

        for table_name in RUNTIME_TABLES:
            rows = tables.get(table_name) or []
            cur.execute("SAVEPOINT smartask_runtime_import_table;")
            try:
                imported_counts[table_name] = _upsert_rows(
                    cur,
                    table_name,
                    rows,
                    fallback_source_id,
                    skipped_table_rows,
                    dataset_id_map,
                )
                cur.execute("RELEASE SAVEPOINT smartask_runtime_import_table;")
            except Exception as exc:
                cur.execute("ROLLBACK TO SAVEPOINT smartask_runtime_import_table;")
                cur.execute("RELEASE SAVEPOINT smartask_runtime_import_table;")
                imported_counts[table_name] = 0
                skipped_table_rows.append(
                    _skip_detail(
                        "table",
                        "整表与当前环境不匹配，已跳过",
                        table=table_name,
                        error=_first_line(exc),
                    )
                )

        for table_name in RUNTIME_TABLES:
            _reset_sequence(cur, table_name)
        final_dataset_ids = _existing_table_ids(cur, "bs_datasets")
        conn.commit()

    for raw_name, payload in configs.items():
        filename = _safe_config_filename(raw_name)
        if not filename or (isinstance(payload, dict) and "__error__" in payload):
            skipped_configs.append(str(raw_name))
            skipped_config_items.append(_skip_detail("config_file", "配置文件无效或不在允许范围内，已跳过", file=str(raw_name)))
            continue
        sanitized_payload, config_skips = _sanitize_config_payload(filename, payload, final_dataset_ids, dataset_id_map)
        skipped_config_items.extend(config_skips)
        target_path = os.path.join(CONFIG_DIR, filename)

        try:
            if os.path.exists(target_path) and not overwrite_configs:
                # 执行智能增量合并
                existing_data = _read_json_file(target_path)
                merged_data, changes = _deep_merge_config(filename, existing_data, sanitized_payload)
                if changes > 0:
                    _write_json_file(target_path, merged_data)
                    written_configs.append(f"{filename} (智能合并 {changes} 项)")
                else:
                    skipped_configs.append(filename)
            else:
                _write_json_file(target_path, sanitized_payload)
                written_configs.append(filename)
        except Exception as exc:
            skipped_configs.append(filename)
            skipped_config_items.append(
                _skip_detail("config_file", "配置文件写入失败，已跳过", file=filename, error=_first_line(exc))
            )

    written_log_files = _write_log_files(log_files, mode, skipped_log_files)

    return {
        "ok": True,
        "dry_run": False,
        "mode": mode,
        "overwrite_configs": overwrite_configs,
        "backup": backup,
        "written_configs": written_configs,
        "skipped_configs": skipped_configs,
        "skipped_config_items": skipped_config_items,
        "imported_counts": imported_counts,
        "skipped_table_rows": skipped_table_rows,
        "written_log_files": written_log_files,
        "skipped_log_files": skipped_log_files,
        "preview": preview,
    }


def _deep_merge_config(filename: str, existing_data: Any, incoming_data: Any) -> Tuple[Any, int]:
    """
    智能合并已有配置与导入包中的新配置，返回 (合并后的数据, 新增/更新的项数)
    """
    if not isinstance(existing_data, dict) or not isinstance(incoming_data, dict):
        return incoming_data, 1

    # 1. AI 模型配置 (ai_settings.json)
    if filename == "ai_settings.json":
        merged = deepcopy(existing_data)
        existing_models = merged.get("models") or []
        incoming_models = incoming_data.get("models") or []
        existing_map = {}
        for idx, m in enumerate(existing_models):
            if isinstance(m, dict):
                key = str(m.get("model") or m.get("name") or "").strip().lower()
                if key:
                    existing_map[key] = idx

        changes = 0
        has_new_default = any(m.get("is_default") for m in incoming_models if isinstance(m, dict))
        if has_new_default:
            for m in existing_models:
                if isinstance(m, dict):
                    m["is_default"] = False

        for inc_m in incoming_models:
            if not isinstance(inc_m, dict):
                continue
            key = str(inc_m.get("model") or inc_m.get("name") or "").strip().lower()
            if key and key in existing_map:
                # 更新已有模型配置
                idx = existing_map[key]
                existing_models[idx].update(inc_m)
                changes += 1
            else:
                # 追加新模型，分配新自增 ID
                max_id = max([int(m.get("id") or 0) for m in existing_models if isinstance(m, dict)] or [0])
                new_m = deepcopy(inc_m)
                new_m["id"] = max_id + 1
                existing_models.append(new_m)
                if key:
                    existing_map[key] = len(existing_models) - 1
                changes += 1

        merged["models"] = existing_models
        for k, v in incoming_data.items():
            if k != "models" and k not in merged:
                merged[k] = v
        return merged, changes

    # 2. 飞书同步配置 (feishu_sync.json)
    if filename == "feishu_sync.json":
        merged = deepcopy(existing_data)
        existing_list = merged.get("sync_configs") or []
        incoming_list = incoming_data.get("sync_configs") or []
        existing_keys = {
            str(item.get("name") or item.get("target_table") or "").strip()
            for item in existing_list if isinstance(item, dict)
        }
        changes = 0
        for item in incoming_list:
            if not isinstance(item, dict):
                continue
            key = str(item.get("name") or item.get("target_table") or "").strip()
            if key and key not in existing_keys:
                max_id = max([int(s.get("id") or 0) for s in existing_list if isinstance(s, dict)] or [0])
                new_s = deepcopy(item)
                new_s["id"] = max_id + 1
                existing_list.append(new_s)
                existing_keys.add(key)
                changes += 1
        merged["sync_configs"] = existing_list
        return merged, changes

    # 3. 数据源配置 (datasources.json)
    if filename == "datasources.json":
        merged = deepcopy(existing_data)
        existing_list = merged.get("datasources") or []
        incoming_list = incoming_data.get("datasources") or []
        existing_names = {str(item.get("name") or "").strip() for item in existing_list if isinstance(item, dict)}
        changes = 0
        for item in incoming_list:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if name and name not in existing_names:
                max_id = max([int(s.get("id") or 0) for s in existing_list if isinstance(s, dict)] or [0])
                new_ds = deepcopy(item)
                new_ds["id"] = max_id + 1
                existing_list.append(new_ds)
                existing_names.add(name)
                changes += 1
        merged["datasources"] = existing_list
        return merged, changes

    # 4. 其他 JSON 字典 (通用递归合并)
    merged = deepcopy(existing_data)
    changes = 0
    for k, v in incoming_data.items():
        if k not in merged:
            merged[k] = v
            changes += 1
        elif isinstance(merged[k], dict) and isinstance(v, dict):
            sub_merged, sub_c = _deep_merge_config(filename, merged[k], v)
            merged[k] = sub_merged
            changes += sub_c
    return merged, changes


def load_bundle_file(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Bundle not found: {path}")
    payload = _read_json_file(path)
    if not isinstance(payload, dict):
        raise ValueError("Invalid runtime bundle: root must be an object")
    return payload
