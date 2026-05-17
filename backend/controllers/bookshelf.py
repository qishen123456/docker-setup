"""
Bookshelf management controller (dataset-isolated knowledge + prompts + golden SQL).
"""

from flask import Blueprint, jsonify, request
import os
import random
import re
import sys
import sqlite3
import time
from typing import Any, Dict, List

import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bookshelf_repository import BookshelfConfigurationError, BookshelfRepository
from config_manager import get_default_datasource, get_datasource_by_id, read_json
import dataset_report_config as report_config_store
from datasource_router import router as datasource_router
from dataset_copilot import CopilotError, DatasetCopilot
from auth_store import get_current_user
from data_permission_store import dataset_access_summary, dataset_scope_hit_for_user, filter_dataset_rows_for_user, load_data_permissions
from feature_flags import feature_available
from system_log_store import log_event, request_snapshot


bookshelf_bp = Blueprint("bookshelf", __name__)
repo = BookshelfRepository()


def _dataset_permissions_for_row(row: Dict[str, Any], user: Dict[str, Any], permissions: Dict[str, Any]) -> Dict[str, Any]:
    dataset_id = int(row.get("id") or row.get("dataset_id") or 0)
    access = dataset_access_summary(user, dataset_id, permissions)
    is_super = (user or {}).get("role") == "super_admin"
    has_edit_feature = feature_available("dataset_save", user)
    return {
        **row,
        **access,
        "can_edit": bool(is_super or (access["dataset_scope_hit"] and has_edit_feature)),
        "can_delete": bool(is_super or (access["dataset_scope_hit"] and feature_available("dataset_delete", user))),
    }


def _can_modify_dataset(dataset_id: int, feature_key: str = "dataset_save") -> bool:
    user = get_current_user()
    if user.get("role") == "super_admin":
        return True
    return bool(feature_available(feature_key, user) and dataset_scope_hit_for_user(user, dataset_id))


def _can_modify_common_questions(user: Dict[str, Any], dataset_id: int) -> bool:
    if user.get("role") == "super_admin":
        return True
    if not dataset_scope_hit_for_user(user, dataset_id):
        return False
    return any(
        feature_available(key, user)
        for key in ("dataset_question_create", "dataset_question_update", "dataset_question_delete")
    )


def _require_dataset_modify(dataset_id: int, feature_key: str = "dataset_save"):
    if _can_modify_dataset(dataset_id, feature_key):
        return None
    return jsonify({"error": "当前账号没有该数据集的编辑权限，或未命中员工组织范围。"}), 403


def _is_read_only_sql(sql_text: str) -> bool:
    normalized = re.sub(r"/\*.*?\*/", " ", str(sql_text or ""), flags=re.S)
    normalized = re.sub(r"--.*?$", " ", normalized, flags=re.M).strip().lower()
    if not normalized:
        return False
    if not (normalized.startswith("select") or normalized.startswith("with")):
        return False
    blocked = [
        " insert ", " update ", " delete ", " drop ", " truncate ", " alter ",
        " create ", " replace ", " grant ", " revoke ", " merge ", " call ",
        " execute ", " vacuum ", " analyze ", " copy ",
    ]
    padded = f" {normalized} "
    return not any(token in padded for token in blocked)


def _wrap_preview_sql(sql_text: str, limit: int) -> str:
    sql = str(sql_text or "").strip()
    if sql.endswith(";"):
        sql = sql[:-1].strip()
    if ";" in sql:
        raise ValueError("SQL 测试只允许单条只读查询。")
    return f"SELECT * FROM (\n{sql}\n) AS __dataset_sql_preview LIMIT {limit}"


def _normalize_synonym(value: str) -> str:
    return (value or "").strip().lower()


def _parse_json_like(value: Any, default: Any):
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    return default


def _optional_int(value: Any):
    text = str(value if value is not None else "").strip()
    if not text:
        return None
    return int(text)


def _dataset_question_tag(dataset_name: str, dataset_code: str = "") -> str:
    text = str(dataset_name or dataset_code or "数据集").strip()
    text = re.sub(r"[（(].*?[）)]", "", text)
    text = re.sub(r"(数据集|任务达成分析|年度|标准版|测试)", "", text).strip(" -_")
    return (text or str(dataset_name or dataset_code or "数据集").strip() or "数据集")[:6]


def _shape_common_question(row: Dict[str, Any]) -> Dict[str, Any]:
    dataset_name = str(row.get("dataset_name") or "")
    dataset_code = str(row.get("dataset_code") or "")
    return {
        "id": row.get("id"),
        "question_text": row.get("question_text"),
        "sort_order": row.get("sort_order"),
        "dataset_id": row.get("dataset_id"),
        "dataset_name": dataset_name,
        "dataset_code": dataset_code,
        "dataset_tag": _dataset_question_tag(dataset_name, dataset_code),
        "business_domain": row.get("business_domain") or "",
    }


def _pick_random_common_questions(rows: List[Dict[str, Any]], size: int = 4) -> List[Dict[str, Any]]:
    grouped: Dict[int, List[Dict[str, Any]]] = {}
    for row in rows:
        question = str(row.get("question_text") or "").strip()
        dataset_id = row.get("dataset_id")
        if not question or dataset_id is None:
            continue
        grouped.setdefault(int(dataset_id), []).append(row)

    dataset_ids = [dataset_id for dataset_id, items in grouped.items() if items]
    if not dataset_ids:
        return []

    random.shuffle(dataset_ids)
    max_dataset_count = min(3, len(dataset_ids), size)
    min_dataset_count = 2 if len(dataset_ids) >= 2 and size >= 2 else 1
    target_dataset_count = random.randint(min_dataset_count, max_dataset_count)
    selected_dataset_ids = dataset_ids[:target_dataset_count]

    picked: List[Dict[str, Any]] = []
    picked_texts = set()
    per_dataset_counts: Dict[int, int] = {dataset_id: 0 for dataset_id in selected_dataset_ids}

    def try_pick(dataset_id: int) -> bool:
        candidates = grouped.get(dataset_id) or []
        random.shuffle(candidates)
        for item in candidates:
            text = str(item.get("question_text") or "").strip()
            if not text or text in picked_texts:
                continue
            if per_dataset_counts.get(dataset_id, 0) >= 2:
                return False
            picked.append(item)
            picked_texts.add(text)
            per_dataset_counts[dataset_id] = per_dataset_counts.get(dataset_id, 0) + 1
            return True
        return False

    for dataset_id in selected_dataset_ids:
        if len(picked) >= size:
            break
        try_pick(dataset_id)

    while len(picked) < size:
        changed = False
        for dataset_id in selected_dataset_ids:
            if len(picked) >= size:
                break
            if per_dataset_counts.get(dataset_id, 0) >= 2:
                continue
            changed = try_pick(dataset_id) or changed
        if not changed:
            break

    if len(picked) < size and len(selected_dataset_ids) < 3:
        for dataset_id in dataset_ids[target_dataset_count:]:
            if len(picked) >= size or len(selected_dataset_ids) >= 3:
                break
            selected_dataset_ids.append(dataset_id)
            per_dataset_counts[dataset_id] = 0
            try_pick(dataset_id)

    return picked[:size]


def _slugify_dataset_code(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "").strip()).strip("_").lower()
    if not text:
        text = f"ai_dataset_{int(time.time())}"
    if not re.match(r"^[A-Za-z_]", text):
        text = f"dataset_{text}"
    return text[:96]


def _infer_dataset_meta_from_prompt(doc_text: str, payload: Dict[str, Any]) -> Dict[str, str]:
    text = str(doc_text or "")

    def first_match(patterns: List[str]) -> str:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.I | re.M)
            if match:
                return str(match.group(1) or "").strip(" ：:-\t\r\n`'\"")
        return ""

    table_name = first_match([
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z0-9_\".]+)",
        r"表名[：:\s]+([A-Za-z0-9_.]+)",
        r"数据源表[：:\s]+`?([A-Za-z0-9_.]+)`?",
    ])
    table_comment = first_match([
        r"COMMENT\s+ON\s+TABLE\s+[A-Za-z0-9_\".]+\s+IS\s+'([^']+)'",
        r"COMMENT\s+ON\s+TABLE\s+[A-Za-z0-9_\".]+\s+IS\s+\"([^\"]+)\"",
    ])
    dataset_name = str(payload.get("dataset_name") or "").strip() or first_match([
        r"数据集名称[：:\s]+(.+)",
        r"数据集[：:\s]+(.+)",
        r"^#\s+(.+?)(?:数据集|任务|分析|LLD|设计文档).*$",
    ])
    if not dataset_name:
        dataset_name = table_comment or (f"{table_name} 智能问数数据集" if table_name else f"AI生成数据集 {time.strftime('%Y%m%d%H%M%S')}")
    dataset_name = re.sub(r"[#`*_]+", "", dataset_name).strip()[:80]

    business_domain = str(payload.get("business_domain") or "").strip() or first_match([
        r"业务域[：:\s]+(.+)",
        r"适用范围[：:\s]+(.+)",
    ])
    if not business_domain:
        business_domain = dataset_name

    dataset_code = str(payload.get("dataset_code") or "").strip()
    if not dataset_code:
        dataset_code = _slugify_dataset_code(table_name or dataset_name)

    return {
        "dataset_code": dataset_code,
        "dataset_name": dataset_name,
        "business_domain": business_domain[:120],
        "description": str(payload.get("description") or f"由大段提示词自动生成：{dataset_name}")[:240],
    }


def _build_style_reference(style_dataset_id: Any) -> str:
    try:
        dataset_id = int(style_dataset_id or 0)
    except (TypeError, ValueError):
        return ""
    if dataset_id <= 0:
        return ""
    try:
        context = repo.get_dataset_context(dataset_id, "", top_k_samples=8)
    except Exception:
        return ""
    dataset = context.get("dataset") or {}
    lld = context.get("lld_document") or {}
    prompts = context.get("agent_prompts") or {}
    samples = context.get("golden_sql_samples") or []
    schema = context.get("schema_definition") or []
    dictionary = context.get("data_dictionary") or []
    prompt_lines: List[str] = []
    for agent_no, rows in prompts.items():
        for item in rows[:2]:
            prompt_lines.append(f"Agent{agent_no}: {str(item.get('prompt_content') or '')[:1200]}")
    sample_lines = [
        f"Q: {item.get('question')}\nSQL:\n{str(item.get('sql_text') or '')[:1600]}"
        for item in samples[:4]
    ]
    schema_lines = [
        f"表 {item.get('table_name')}:\n{str(item.get('ddl_sql') or '')[:1400]}"
        for item in schema[:3]
    ]
    dictionary_lines = [
        f"{item.get('table_name')}.{item.get('column_name')} jsonb={item.get('jsonb_key') or '-'} => {item.get('semantic_name')}"
        for item in dictionary[:30]
    ]
    return "\n\n".join([
        "## 参考数据集样式（只参考结构，不复制业务实体）",
        f"数据集：{dataset.get('dataset_name')} / {dataset.get('dataset_code')}",
        f"LLD 摘要：{str(lld.get('content') or '')[:1800]}",
        "DDL 风格：\n" + "\n\n".join(schema_lines),
        "字段字典风格：\n" + "\n".join(dictionary_lines),
        "Golden SQL 风格：\n" + "\n\n".join(sample_lines),
        "Agent Prompt 风格：\n" + "\n\n".join(prompt_lines),
    ]).strip()


def _validate_full_payload(payload: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    lld_documents = payload.get("lld_documents") or []
    data_dictionary = payload.get("data_dictionary") or []
    schema_definition = payload.get("schema_definition") or []
    golden_sql_samples = payload.get("golden_sql_samples") or []
    agent_prompts = payload.get("agent_prompts") or []

    valid_lld = [item for item in lld_documents if str(item.get("content") or "").strip()]
    valid_schema = [item for item in schema_definition if str(item.get("table_name") or "").strip() and str(item.get("ddl_sql") or "").strip()]
    valid_dictionary = [
        item for item in data_dictionary
        if str(item.get("table_name") or "").strip()
        and str(item.get("column_name") or "").strip()
        and str(item.get("semantic_name") or "").strip()
    ]
    valid_golden = [
        item for item in golden_sql_samples
        if str(item.get("question") or "").strip() and str(item.get("sql_text") or "").strip()
    ]

    prompt_agents = {
        int(item.get("agent_no") or 0)
        for item in agent_prompts
        if int(item.get("agent_no") or 0) in (1, 2, 3, 4) and str(item.get("prompt_content") or "").strip()
    }
    missing_agents = [str(agent_no) for agent_no in (1, 2, 3, 4) if agent_no not in prompt_agents]

    if not valid_lld:
        errors.append("请至少维护一份有效的 LLD 文档。")
    if not valid_schema:
        errors.append("请至少维护一张带 DDL 的表定义。")
    if valid_schema and not valid_dictionary:
        errors.append("当前已有 DDL，但数据字典为空，请至少补充一批字段语义。")
    if len(valid_golden) < 3:
        errors.append("请至少维护 3 条有效的 Golden SQL 样本后再保存。")
    if missing_agents:
        errors.append(f"Agent 提示片段缺失：Agent {', '.join(missing_agents)}。")

    seen_pairs = set()
    duplicate_count = 0
    for item in valid_golden:
        key = (str(item.get("question") or "").strip(), str(item.get("sql_text") or "").strip())
        if key in seen_pairs:
            duplicate_count += 1
        seen_pairs.add(key)
    if duplicate_count > 0:
        errors.append(f"Golden SQL 中存在 {duplicate_count} 条重复样本，请去重后再保存。")

    return errors


def _build_quality_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    lld_documents = payload.get("lld_documents") or []
    data_dictionary = payload.get("data_dictionary") or []
    schema_definition = payload.get("schema_definition") or []
    golden_sql_samples = payload.get("golden_sql_samples") or []
    agent_prompts = payload.get("agent_prompts") or []
    common_questions = payload.get("common_questions") or []
    regression_cases = payload.get("regression_cases") or []

    valid_lld = [item for item in lld_documents if str(item.get("content") or "").strip()]
    valid_schema = [item for item in schema_definition if str(item.get("table_name") or "").strip() and str(item.get("ddl_sql") or "").strip()]
    valid_dictionary = [
        item for item in data_dictionary
        if str(item.get("table_name") or "").strip()
        and str(item.get("column_name") or "").strip()
        and str(item.get("semantic_name") or "").strip()
    ]
    valid_golden = [
        item for item in golden_sql_samples
        if str(item.get("question") or "").strip() and str(item.get("sql_text") or "").strip()
    ]
    valid_common_questions = [item for item in common_questions if str(item.get("question_text") or "").strip()]
    valid_regression_cases = [item for item in regression_cases if str(item.get("question_text") or "").strip()]
    prompt_agents = {
        int(item.get("agent_no") or 0)
        for item in agent_prompts
        if int(item.get("agent_no") or 0) in (1, 2, 3, 4) and str(item.get("prompt_content") or "").strip()
    }

    schema_table_count = len({str(item.get("table_name") or "").strip() for item in valid_schema if str(item.get("table_name") or "").strip()})
    dictionary_table_count = len({str(item.get("table_name") or "").strip() for item in valid_dictionary if str(item.get("table_name") or "").strip()})

    checks = []

    def add_check(key: str, label: str, score: int, max_score: int, summary: str):
        status = "healthy" if score >= max_score * 0.8 else "warning" if score > 0 else "risk"
        checks.append(
            {
                "key": key,
                "label": label,
                "score": score,
                "max_score": max_score,
                "status": status,
                "summary": summary,
            }
        )

    lld_score = 15 if valid_lld else 0
    add_check("lld", "LLD 文档", lld_score, 15, f"有效 LLD {len(valid_lld)} 份")

    schema_score = 20 if valid_schema else 0
    add_check("schema", "DDL / 表结构", schema_score, 20, f"有效表定义 {len(valid_schema)} 张")

    dictionary_target = max(8, schema_table_count * 4)
    dictionary_score = min(20, int(round(min(1, len(valid_dictionary) / dictionary_target) * 20))) if dictionary_target > 0 else 0
    add_check(
        "dictionary",
        "数据字典",
        dictionary_score,
        20,
        f"有效字段语义 {len(valid_dictionary)} 条，覆盖表 {dictionary_table_count}/{schema_table_count or 0}",
    )

    golden_score = min(20, int(round(min(1, len(valid_golden) / 5) * 20)))
    add_check("golden_sql", "Golden SQL", golden_score, 20, f"有效样本 {len(valid_golden)} 条")

    prompt_score = min(15, int(round((len(prompt_agents) / 4) * 15)))
    add_check("prompts", "Agent Prompt", prompt_score, 15, f"已配置 Agent {len(prompt_agents)}/4")

    question_score = min(5, int(round(min(1, len(valid_common_questions) / 5) * 5)))
    add_check("common_questions", "常见问题", question_score, 5, f"有效常见问题 {len(valid_common_questions)} 条")

    regression_score = min(5, int(round(min(1, len(valid_regression_cases) / 4) * 5)))
    add_check("regression_cases", "标准题集", regression_score, 5, f"有效回归题 {len(valid_regression_cases)} 条")

    total_score = sum(item["score"] for item in checks)
    level = "healthy" if total_score >= 85 else "warning" if total_score >= 65 else "risk"
    label = "健康" if total_score >= 85 else "待补强" if total_score >= 65 else "风险较高"

    gaps: List[str] = []
    if not valid_lld:
        gaps.append("缺少有效 LLD 文档，Agent2/3/4 容易失去业务约束。")
    if not valid_schema:
        gaps.append("缺少带 DDL 的表定义，SQL 生成会明显变弱。")
    if valid_schema and len(valid_dictionary) < dictionary_target:
        gaps.append("数据字典覆盖偏低，字段语义不足会影响问数准确率。")
    if len(valid_golden) < 3:
        gaps.append("Golden SQL 少于 3 条，高质量样本不足。")
    if len(prompt_agents) < 4:
        gaps.append("Agent1-4 Prompt 未覆盖完整，部分 Agent 仍缺少专用提示词。")
    if len(valid_common_questions) < 3:
        gaps.append("常见问题样本过少，路由与口径识别信号偏弱。")
    if len(valid_regression_cases) < 4:
        gaps.append("标准题集不足，建议至少覆盖明细、汇总、趋势、口径确认四类问题。")

    return {
        "score": total_score,
        "level": level,
        "label": label,
        "checks": checks,
        "gaps": gaps,
        "stats": {
            "lld_count": len(valid_lld),
            "schema_count": len(valid_schema),
            "dictionary_count": len(valid_dictionary),
            "golden_sql_count": len(valid_golden),
            "agent_prompt_count": len(prompt_agents),
            "common_question_count": len(valid_common_questions),
            "regression_case_count": len(valid_regression_cases),
        },
    }


def _log_dataset_prompt_event(
    event_type: str,
    level: str,
    title: str,
    *,
    doc_text: str = "",
    source_id: Any = None,
    style_dataset_id: Any = None,
    dataset_meta: Dict[str, Any] | None = None,
    quality_summary: Dict[str, Any] | None = None,
    validation_errors: List[str] | None = None,
    error_message: str = "",
    duration_ms: int | None = None,
) -> None:
    try:
        details = {
            "event_name": title,
            "what_happened": title,
            "source_id": source_id,
            "style_dataset_id": style_dataset_id,
            "doc_chars": len(doc_text or ""),
            "dataset_meta": dataset_meta or {},
            "quality_summary": quality_summary or {},
            "validation_errors": validation_errors or [],
            "suggested_action": (
                "如果生成一直等待，先检查默认 AI 模型/API Key、模型服务可用性和大段提示词长度；"
                "如果保存失败，检查生成 payload 的 schema_definition、data_dictionary、golden_sql_samples、agent_prompts。"
            ),
            "code_hint": (
                "后端入口：backend/controllers/bookshelf.py::generate_bookshelf_dataset_from_prompt；"
                "AI 生成：backend/dataset_copilot/payload_generator.py；"
                "保存入口：backend/controllers/bookshelf.py::save_bookshelf_dataset_full。"
            ),
        }
        log_event(
            category="dataset_generation",
            event_type=event_type,
            level=level,
            title=title,
            user=get_current_user(),
            request_info=request_snapshot(request),
            status_code=None,
            duration_ms=duration_ms,
            error_message=error_message,
            details=details,
        )
    except Exception:
        pass


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
        ALTER TABLE bs_schema_definitions
        ADD COLUMN IF NOT EXISTS source_id BIGINT;
        """
    )


@bookshelf_bp.route("/api/bookshelves/health", methods=["GET"])
def bookshelf_health():
    try:
        repo.ensure_schema()
        return jsonify({"ready": repo.is_ready()})
    except Exception as exc:
        return jsonify({"ready": False, "error": str(exc)})


@bookshelf_bp.route("/api/bookshelves/datasets", methods=["GET"])
def list_bookshelf_datasets():
    try:
        repo.ensure_schema()
        user = get_current_user()
        include_inactive = (
            user.get("role") == "super_admin"
            and str(request.args.get("include_inactive", "")).lower() in ("1", "true", "yes")
        )
        with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            active_filter_sql = "" if include_inactive else "WHERE d.is_active = TRUE"
            cur.execute(
                f"""
                SELECT
                    d.id,
                    d.dataset_code,
                    d.dataset_name,
                    d.business_domain,
                    d.source_id,
                    d.description,
                    d.is_active,
                    d.updated_at,
                    COALESCE(s.synonym_count, 0) AS synonym_count,
                    COALESCE(g.sample_count, 0) AS golden_sql_count
                FROM bs_datasets d
                LEFT JOIN (
                    SELECT dataset_id, COUNT(*) AS synonym_count
                    FROM bs_dataset_synonyms
                    GROUP BY dataset_id
                ) s ON s.dataset_id = d.id
                LEFT JOIN (
                    SELECT dataset_id, COUNT(*) AS sample_count
                    FROM bs_golden_sql_samples
                    WHERE is_active = TRUE
                    GROUP BY dataset_id
                ) g ON g.dataset_id = d.id
                {active_filter_sql}
                ORDER BY d.id DESC;
                """
            )
            rows = [dict(row) for row in cur.fetchall()]
            permissions = load_data_permissions()
            visible_rows = []
            for row in rows:
                shaped = _dataset_permissions_for_row(row, user, permissions)
                if shaped["can_view"]:
                    visible_rows.append(shaped)
            return jsonify({"datasets": visible_rows})
    except BookshelfConfigurationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"list datasets failed: {exc}"}), 500


@bookshelf_bp.route("/api/bookshelves/datasets", methods=["POST"])
def create_bookshelf_dataset():
    try:
        user = get_current_user()
        if user.get("role") != "super_admin" and not feature_available("dataset_create", user):
            return jsonify({"error": "当前账号没有新建数据集权限。"}), 403
        repo.ensure_schema()
        payload = request.get_json() or {}
        dataset_code = (payload.get("dataset_code") or "").strip()
        dataset_name = (payload.get("dataset_name") or "").strip()
        business_domain = (payload.get("business_domain") or "").strip()
        source_id = payload.get("source_id")
        description = (payload.get("description") or "").strip()

        if not dataset_code or not dataset_name or not business_domain:
            return jsonify({"error": "dataset_code/dataset_name/business_domain are required."}), 400

        if source_id is None:
            default_source = get_default_datasource()
            if default_source:
                source_id = default_source.get("id")

        if source_id is None:
            return jsonify({"error": "source_id is required. Please create/select a datasource first."}), 400

        with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            _ensure_optional_tables(cur)
            cur.execute(
                """
                INSERT INTO bs_datasets(dataset_code, dataset_name, business_domain, source_id, description, is_active)
                VALUES (%s, %s, %s, %s, %s, TRUE)
                RETURNING id, dataset_code, dataset_name, business_domain, source_id, description, is_active, updated_at;
                """,
                (dataset_code, dataset_name, business_domain, int(source_id), description),
            )
            created = dict(cur.fetchone())
            return jsonify({"dataset": _dataset_permissions_for_row(created, user, load_data_permissions())}), 201
    except BookshelfConfigurationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"create dataset failed: {exc}"}), 500


@bookshelf_bp.route("/api/bookshelves/datasets/generate-from-prompt", methods=["POST"])
def generate_bookshelf_dataset_from_prompt():
    started_at = time.time()
    try:
        user = get_current_user()
        if user.get("role") != "super_admin" and not feature_available("dataset_prompt_generate", user):
            return jsonify({"error": "当前账号没有提示词生成数据集权限。"}), 403
        payload = request.get_json() or {}
        doc_text = str(payload.get("doc_text") or "").strip()
        if len(doc_text) < 80:
            return jsonify({"error": "请粘贴更完整的提示词、DDL、字段字典或业务口径，至少 80 字。"}), 400

        source_id = payload.get("source_id")
        style_dataset_id = payload.get("style_dataset_id")
        _log_dataset_prompt_event(
            "dataset_generate_from_prompt_started",
            "info",
            "开始根据提示词生成数据集",
            doc_text=doc_text,
            source_id=source_id,
            style_dataset_id=style_dataset_id,
        )
        style_reference = _build_style_reference(style_dataset_id)
        enriched_doc = doc_text
        if style_reference:
            enriched_doc = f"{doc_text}\n\n{style_reference}"

        meta = _infer_dataset_meta_from_prompt(doc_text, payload)
        dataset_meta = {
            "id": 0,
            "dataset_code": meta["dataset_code"],
            "dataset_name": meta["dataset_name"],
            "business_domain": meta["business_domain"],
            "source_id": source_id,
            "description": meta["description"],
        }
        try:
            use_json_mode = payload.get("use_json_mode")
            if use_json_mode is None:
                use_json_mode = True
            copilot = DatasetCopilot(
                model=payload.get("model") or None,
                base_url=payload.get("base_url") or None,
                api_key=payload.get("api_key") or None,
                max_tokens=int(payload.get("max_tokens") or 24576),
                use_json_mode=bool(use_json_mode),
            )
            generated = copilot.generate(
                dataset_meta=dataset_meta,
                doc_text=enriched_doc,
                sample_rows_text=str(payload.get("sample_rows_text") or ""),
                retries=int(payload.get("retries") or 2),
                doc_max_chars=int(payload.get("doc_max_chars") or 30000),
            )
        except CopilotError as exc:
            _log_dataset_prompt_event(
                "dataset_generate_from_prompt_failed",
                "error",
                "AI 生成数据集失败",
                doc_text=doc_text,
                source_id=source_id,
                style_dataset_id=style_dataset_id,
                dataset_meta=meta,
                error_message=str(exc),
                duration_ms=int((time.time() - started_at) * 1000),
            )
            return jsonify({
                "error": f"数据集生成失败: {exc}",
                "details": [
                    f"详细报错：{exc}",
                    "建议检查：默认 AI 模型/API Key、模型服务地址、提示词长度、模型返回是否是完整 JSON。",
                    "建议改代码位置：backend/dataset_copilot/payload_generator.py；接口入口在 backend/controllers/bookshelf.py::generate_bookshelf_dataset_from_prompt。",
                ],
            }), 500

        normalized_source_id = _optional_int(source_id)
        if normalized_source_id is not None:
            for item in generated.get("schema_definition") or []:
                if isinstance(item, dict):
                    item["source_id"] = normalized_source_id

        validation_errors = _validate_full_payload(generated)
        summary = _build_quality_summary(generated)
        _log_dataset_prompt_event(
            "dataset_generate_from_prompt_completed",
            "warning" if validation_errors else "info",
            "提示词生成数据集已返回结果",
            doc_text=doc_text,
            source_id=source_id,
            style_dataset_id=style_dataset_id,
            dataset_meta=meta,
            quality_summary=summary,
            validation_errors=validation_errors,
            duration_ms=int((time.time() - started_at) * 1000),
        )
        return jsonify({
            "dataset_meta": meta,
            "payload": generated,
            "quality_summary": summary,
            "validation_errors": validation_errors,
            "style_applied": bool(style_reference),
        })
    except Exception as exc:
        _log_dataset_prompt_event(
            "dataset_generate_from_prompt_error",
            "error",
            "提示词生成数据集接口异常",
            doc_text=locals().get("doc_text", ""),
            source_id=locals().get("source_id", None),
            style_dataset_id=locals().get("style_dataset_id", None),
            error_message=str(exc),
            duration_ms=int((time.time() - started_at) * 1000),
        )
        return jsonify({
            "error": f"generate dataset from prompt failed: {exc}",
            "details": [
                f"详细报错：{exc}",
                "建议检查：后端接口参数、参考样式数据集、source_id、AI 生成 payload 格式。",
                "建议改代码位置：backend/controllers/bookshelf.py::generate_bookshelf_dataset_from_prompt。",
            ],
        }), 500


@bookshelf_bp.route("/api/bookshelves/datasets/<int:dataset_id>", methods=["PUT"])
def update_bookshelf_dataset(dataset_id: int):
    try:
        error = _require_dataset_modify(dataset_id, "dataset_save")
        if error:
            return error
        repo.ensure_schema()
        payload = request.get_json() or {}
        fields = {
            "dataset_code": (payload.get("dataset_code") or "").strip(),
            "dataset_name": (payload.get("dataset_name") or "").strip(),
            "business_domain": (payload.get("business_domain") or "").strip(),
            "description": (payload.get("description") or "").strip(),
            "source_id": payload.get("source_id"),
            "is_active": payload.get("is_active"),
        }

        with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE bs_datasets
                SET
                    dataset_code = COALESCE(NULLIF(%s, ''), dataset_code),
                    dataset_name = COALESCE(NULLIF(%s, ''), dataset_name),
                    business_domain = COALESCE(NULLIF(%s, ''), business_domain),
                    description = %s,
                    source_id = COALESCE(%s, source_id),
                    is_active = COALESCE(%s, is_active),
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id, dataset_code, dataset_name, business_domain, source_id, description, is_active, updated_at;
                """,
                (
                    fields["dataset_code"],
                    fields["dataset_name"],
                    fields["business_domain"],
                    fields["description"],
                    int(fields["source_id"]) if fields["source_id"] is not None else None,
                    fields["is_active"],
                    dataset_id,
                ),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": f"dataset not found: {dataset_id}"}), 404
            return jsonify({"dataset": dict(row)})
    except BookshelfConfigurationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"update dataset failed: {exc}"}), 500


@bookshelf_bp.route("/api/bookshelves/datasets/<int:dataset_id>", methods=["DELETE"])
def delete_bookshelf_dataset(dataset_id: int):
    try:
        error = _require_dataset_modify(dataset_id, "dataset_delete")
        if error:
            return error
        repo.ensure_schema()
        with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE bs_datasets
                SET is_active = FALSE, updated_at = NOW()
                WHERE id = %s
                RETURNING id;
                """,
                (dataset_id,),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": f"dataset not found: {dataset_id}"}), 404
            return jsonify({"message": "dataset deactivated", "dataset_id": dataset_id})
    except BookshelfConfigurationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"delete dataset failed: {exc}"}), 500


@bookshelf_bp.route("/api/bookshelves/datasets/<int:dataset_id>/full", methods=["GET"])
def get_bookshelf_dataset_full(dataset_id: int):
    try:
        repo.ensure_schema()
        with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            _ensure_optional_tables(cur)
            cur.execute(
                """
                SELECT id, dataset_code, dataset_name, business_domain, source_id, description, is_active, updated_at
                FROM bs_datasets
                WHERE id = %s;
                """,
                (dataset_id,),
            )
            dataset = cur.fetchone()
            if not dataset:
                return jsonify({"error": f"dataset not found: {dataset_id}"}), 404
            access = dataset_access_summary(get_current_user(), dataset_id)
            if not access["can_view"]:
                return jsonify({"error": "当前账号没有访问该数据集的权限"}), 403

            cur.execute(
                """
                SELECT synonym, normalized_synonym, weight
                FROM bs_dataset_synonyms
                WHERE dataset_id = %s
                ORDER BY id;
                """,
                (dataset_id,),
            )
            synonyms = [dict(row) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT id, version, title, content, redline_rules, is_active, updated_at
                FROM bs_lld_documents
                WHERE dataset_id = %s
                ORDER BY version DESC, updated_at DESC;
                """,
                (dataset_id,),
            )
            lld_documents = [dict(row) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT id, table_name, column_name, jsonb_key, semantic_name, data_type, enum_mapping, extraction_rule, is_active
                FROM bs_data_dictionary_items
                WHERE dataset_id = %s
                ORDER BY table_name, column_name, id;
                """,
                (dataset_id,),
            )
            data_dictionary = [dict(row) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT id, table_name, ddl_sql, description, is_active, source_id
                FROM bs_schema_definitions
                WHERE dataset_id = %s
                ORDER BY table_name, id;
                """,
                (dataset_id,),
            )
            schema_definition = [dict(row) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT id, left_table, left_key, right_table, right_key, relation_type, description, is_active
                FROM bs_table_relations
                WHERE dataset_id = %s
                ORDER BY id;
                """,
                (dataset_id,),
            )
            table_relations = [dict(row) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT id, intent_type, question, sql_text, tags, quality_score, is_active, updated_at
                FROM bs_golden_sql_samples
                WHERE dataset_id = %s
                ORDER BY quality_score DESC, updated_at DESC;
                """,
                (dataset_id,),
            )
            golden_sql_samples = [dict(row) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT id, agent_no, prompt_key, prompt_content, is_active, updated_at
                FROM bs_agent_prompt_fragments
                WHERE dataset_id = %s
                ORDER BY agent_no, prompt_key, id;
                """,
                (dataset_id,),
            )
            agent_prompts = [dict(row) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT id, question_text, sort_order, is_active, updated_at
                FROM bs_common_questions
                WHERE dataset_id = %s
                ORDER BY sort_order ASC, id ASC;
                """,
                (dataset_id,),
            )
            common_questions = [dict(row) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT id, config_type, config_key, config_value, is_active, updated_at
                FROM bs_dataset_external_configs
                WHERE dataset_id = %s
                ORDER BY config_type, config_key, id;
                """,
                (dataset_id,),
            )
            external_configs = [dict(row) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT id, case_type, question_text, expected_focus, expected_intent, sort_order, is_active, updated_at
                FROM bs_regression_cases
                WHERE dataset_id = %s
                ORDER BY sort_order ASC, id ASC;
                """,
                (dataset_id,),
            )
            regression_cases = [dict(row) for row in cur.fetchall()]

            quality_summary = _build_quality_summary(
                {
                    "lld_documents": lld_documents,
                    "data_dictionary": data_dictionary,
                    "schema_definition": schema_definition,
                    "golden_sql_samples": golden_sql_samples,
                    "agent_prompts": agent_prompts,
                    "common_questions": common_questions,
                    "regression_cases": regression_cases,
                }
            )

            return jsonify(
                {
                    "dataset": _dataset_permissions_for_row(dict(dataset), get_current_user(), load_data_permissions()),
                    "synonyms": synonyms,
                    "lld_documents": lld_documents,
                    "data_dictionary": data_dictionary,
                    "schema_definition": schema_definition,
                    "table_relations": table_relations,
                    "golden_sql_samples": golden_sql_samples,
                    "agent_prompts": agent_prompts,
                    "common_questions": common_questions,
                    "external_configs": external_configs,
                    "regression_cases": regression_cases,
                    "quality_summary": quality_summary,
                }
            )
    except BookshelfConfigurationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"get dataset full failed: {exc}"}), 500


@bookshelf_bp.route("/api/bookshelves/datasets/<int:dataset_id>/sql-preview", methods=["POST"])
def preview_bookshelf_dataset_sql(dataset_id: int):
    try:
        repo.ensure_schema()
        user = get_current_user()
        if user.get("role") != "super_admin" and not feature_available("dataset_sql_preview_run", user):
            return jsonify({"error": "当前账号没有执行 SQL 测试权限。"}), 403
        payload = request.get_json() or {}
        sql_text = str(payload.get("sql") or "").strip()
        try:
            limit = int(payload.get("limit") or 100)
        except (TypeError, ValueError):
            limit = 100
        limit = max(1, min(limit, 10000))

        if not sql_text:
            return jsonify({"error": "SQL 不能为空。"}), 400
        if not _is_read_only_sql(sql_text):
            return jsonify({"error": "仅允许执行 SELECT / WITH 开头的只读 SQL。"}), 400

        with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, dataset_name, source_id
                FROM bs_datasets
                WHERE id = %s AND is_active = TRUE;
                """,
                (dataset_id,),
            )
            dataset = cur.fetchone()
        if not dataset:
            return jsonify({"error": f"dataset not found: {dataset_id}"}), 404
        if not dataset_access_summary(user, dataset_id)["can_view"]:
            return jsonify({"error": "当前账号没有访问该数据集的权限"}), 403
        if dataset.get("source_id") is None:
            return jsonify({"error": "当前数据集未绑定数据源，无法测试 SQL。"}), 400

        preview_sql = _wrap_preview_sql(sql_text, limit)
        dataframe = datasource_router.execute_sql_for_source(int(dataset["source_id"]), preview_sql)
        json_text = dataframe.to_json(orient="records", force_ascii=False, date_format="iso")
        import json

        records = json.loads(json_text)
        columns = [str(col) for col in dataframe.columns.tolist()]
        return jsonify({
            "dataset_id": dataset_id,
            "dataset_name": dataset.get("dataset_name"),
            "source_id": dataset.get("source_id"),
            "columns": columns,
            "rows": records,
            "row_count": len(records),
            "limit": limit,
            "preview_sql": preview_sql,
        })
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except BookshelfConfigurationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"SQL 测试失败: {exc}"}), 500


@bookshelf_bp.route("/api/bookshelves/datasets/<int:dataset_id>/full", methods=["PUT"])
def save_bookshelf_dataset_full(dataset_id: int):
    try:
        user = get_current_user()
        payload = request.get_json() or {}
        has_full_save = _can_modify_dataset(dataset_id, "dataset_save")
        payload_keys = {key for key in payload.keys() if not str(key).startswith("__")}
        common_questions_only = payload_keys.issubset({"common_questions"})
        partial_common_questions = not has_full_save and common_questions_only and _can_modify_common_questions(user, dataset_id)
        if not has_full_save and not partial_common_questions:
            return jsonify({"error": "当前账号没有该数据集的编辑权限，或未命中员工组织范围。"}), 403
        repo.ensure_schema()
        validation_errors = [] if partial_common_questions else _validate_full_payload(payload)
        if validation_errors:
            return jsonify({"error": "dataset validation failed", "details": validation_errors}), 400
        synonyms = payload.get("synonyms") or []
        lld_documents = payload.get("lld_documents") or []
        data_dictionary = payload.get("data_dictionary") or []
        schema_definition = payload.get("schema_definition") or []
        table_relations = payload.get("table_relations") or []
        golden_sql_samples = payload.get("golden_sql_samples") or []
        agent_prompts = payload.get("agent_prompts") or []
        common_questions = payload.get("common_questions") or []
        regression_cases = payload.get("regression_cases") or []
        external_configs = payload.get("external_configs") or []
        report_config = payload.get("report_config") or None

        with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            _ensure_optional_tables(cur)
            cur.execute("SELECT id FROM bs_datasets WHERE id = %s;", (dataset_id,))
            if not cur.fetchone():
                return jsonify({"error": f"dataset not found: {dataset_id}"}), 404

            # Keep import idempotent for repeated clicks.
            if not partial_common_questions:
                cur.execute(
                    "DELETE FROM bs_golden_sql_samples WHERE dataset_id = %s AND created_by = 'legacy-import';",
                    (dataset_id,),
                )
                cur.execute(
                    "DELETE FROM bs_agent_prompt_fragments WHERE dataset_id = %s AND created_by = 'legacy-import';",
                    (dataset_id,),
                )
                cur.execute(
                    """
                    DELETE FROM bs_dataset_external_configs
                    WHERE dataset_id = %s
                      AND (config_key LIKE 'legacy_sync_%%' OR config_key LIKE 'legacy_ai_model_%%');
                    """,
                    (dataset_id,),
                )

                cur.execute("DELETE FROM bs_dataset_synonyms WHERE dataset_id = %s;", (dataset_id,))
                for item in synonyms:
                    synonym = (item.get("synonym") or "").strip()
                    if not synonym:
                        continue
                    normalized = _normalize_synonym(item.get("normalized_synonym") or synonym)
                    weight = int(item.get("weight") or 1)
                    cur.execute(
                        """
                        INSERT INTO bs_dataset_synonyms(dataset_id, synonym, normalized_synonym, weight)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (dataset_id, normalized_synonym)
                        DO UPDATE SET synonym = EXCLUDED.synonym, weight = EXCLUDED.weight;
                        """,
                        (dataset_id, synonym, normalized, weight),
                    )

                cur.execute("DELETE FROM bs_lld_documents WHERE dataset_id = %s;", (dataset_id,))
                for idx, item in enumerate(lld_documents, start=1):
                    content = (item.get("content") or "").strip()
                    if not content:
                        continue
                    version = int(item.get("version") or idx)
                    title = (item.get("title") or f"LLD v{version}").strip()
                    redline_rules = _parse_json_like(item.get("redline_rules"), [])
                    cur.execute(
                        """
                        INSERT INTO bs_lld_documents(dataset_id, version, title, content, redline_rules, is_active, created_by)
                        VALUES (%s, %s, %s, %s, %s::jsonb, %s, 'ui')
                        ON CONFLICT (dataset_id, version)
                        DO UPDATE SET
                            title = EXCLUDED.title,
                            content = EXCLUDED.content,
                            redline_rules = EXCLUDED.redline_rules,
                            is_active = EXCLUDED.is_active,
                            updated_at = NOW();
                        """,
                        (dataset_id, version, title, content, json_dump(redline_rules), bool(item.get("is_active", True))),
                    )

                cur.execute("DELETE FROM bs_data_dictionary_items WHERE dataset_id = %s;", (dataset_id,))
                for item in data_dictionary:
                    table_name = (item.get("table_name") or "").strip()
                    column_name = (item.get("column_name") or "").strip()
                    semantic_name = (item.get("semantic_name") or "").strip()
                    if not table_name or not column_name or not semantic_name:
                        continue
                    cur.execute(
                        """
                        INSERT INTO bs_data_dictionary_items(
                            dataset_id, table_name, column_name, jsonb_key, semantic_name,
                            data_type, enum_mapping, extraction_rule, is_active
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s);
                        """,
                        (
                            dataset_id,
                            table_name,
                            column_name,
                            (item.get("jsonb_key") or "").strip() or None,
                            semantic_name,
                            (item.get("data_type") or "text").strip(),
                            json_dump(_parse_json_like(item.get("enum_mapping"), {})),
                            (item.get("extraction_rule") or "").strip(),
                            bool(item.get("is_active", True)),
                        ),
                    )

                cur.execute("DELETE FROM bs_schema_definitions WHERE dataset_id = %s;", (dataset_id,))
                for item in schema_definition:
                    table_name = (item.get("table_name") or "").strip()
                    ddl_sql = (item.get("ddl_sql") or "").strip()
                    if not table_name or not ddl_sql:
                        continue
                    source_id = item.get("source_id")
                    cur.execute(
                        """
                        INSERT INTO bs_schema_definitions(dataset_id, table_name, ddl_sql, description, is_active, source_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (dataset_id, table_name)
                        DO UPDATE SET
                            ddl_sql = EXCLUDED.ddl_sql,
                            description = EXCLUDED.description,
                            source_id = EXCLUDED.source_id,
                            is_active = EXCLUDED.is_active,
                            updated_at = NOW();
                        """,
                        (
                            dataset_id,
                            table_name,
                            ddl_sql,
                            (item.get("description") or "").strip(),
                            bool(item.get("is_active", True)),
                            _optional_int(source_id),
                        ),
                    )

                cur.execute("DELETE FROM bs_table_relations WHERE dataset_id = %s;", (dataset_id,))
                for item in table_relations:
                    left_table = (item.get("left_table") or "").strip()
                    left_key = (item.get("left_key") or "").strip()
                    right_table = (item.get("right_table") or "").strip()
                    right_key = (item.get("right_key") or "").strip()
                    if not left_table or not left_key or not right_table or not right_key:
                        continue
                    cur.execute(
                        """
                        INSERT INTO bs_table_relations(
                            dataset_id, left_table, left_key, right_table, right_key,
                            relation_type, description, is_active
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            dataset_id,
                            left_table,
                            left_key,
                            right_table,
                            right_key,
                            (item.get("relation_type") or "inner").strip(),
                            (item.get("description") or "").strip(),
                            bool(item.get("is_active", True)),
                        ),
                    )

                cur.execute("DELETE FROM bs_golden_sql_samples WHERE dataset_id = %s;", (dataset_id,))
                for item in golden_sql_samples:
                    question = (item.get("question") or "").strip()
                    sql_text = (item.get("sql_text") or "").strip()
                    if not question or not sql_text:
                        continue
                    cur.execute(
                        """
                        INSERT INTO bs_golden_sql_samples(
                            dataset_id, intent_type, question, sql_text, tags, quality_score, is_active, created_by
                        )
                        VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, 'ui');
                        """,
                        (
                            dataset_id,
                            (item.get("intent_type") or "detail").strip(),
                            question,
                            sql_text,
                            json_dump(_parse_json_like(item.get("tags"), [])),
                            int(item.get("quality_score") or 80),
                            bool(item.get("is_active", True)),
                        ),
                    )

                cur.execute("DELETE FROM bs_agent_prompt_fragments WHERE dataset_id = %s;", (dataset_id,))
                for item in agent_prompts:
                    agent_no = int(item.get("agent_no") or 0)
                    prompt_content = (item.get("prompt_content") or "").strip()
                    if agent_no not in (1, 2, 3, 4) or not prompt_content:
                        continue
                    cur.execute(
                        """
                        INSERT INTO bs_agent_prompt_fragments(
                            dataset_id, agent_no, prompt_key, prompt_content, is_active, created_by
                        )
                        VALUES (%s, %s, %s, %s, %s, 'ui')
                        ON CONFLICT (dataset_id, agent_no, prompt_key)
                        DO UPDATE SET
                            prompt_content = EXCLUDED.prompt_content,
                            is_active = EXCLUDED.is_active,
                            updated_at = NOW();
                        """,
                        (
                            dataset_id,
                            agent_no,
                            (item.get("prompt_key") or "default").strip(),
                            prompt_content,
                            bool(item.get("is_active", True)),
                        ),
                    )

            if partial_common_questions:
                can_create_question = feature_available("dataset_question_create", user)
                can_update_question = feature_available("dataset_question_update", user)
                can_delete_question = feature_available("dataset_question_delete", user)
                cur.execute(
                    """
                    SELECT id, question_text, sort_order, is_active
                    FROM bs_common_questions
                    WHERE dataset_id = %s;
                    """,
                    (dataset_id,),
                )
                existing_questions = {int(row["id"]): dict(row) for row in cur.fetchall()}
                incoming_existing_ids = set()
                for item in common_questions:
                    raw_id = item.get("id")
                    try:
                        question_id = int(raw_id) if raw_id is not None else 0
                    except (TypeError, ValueError):
                        question_id = 0
                    if question_id and question_id in existing_questions:
                        incoming_existing_ids.add(question_id)
                        existing = existing_questions[question_id]
                        changed = (
                            str(item.get("question_text") or "").strip() != str(existing.get("question_text") or "").strip()
                            or int(item.get("sort_order") or 0) != int(existing.get("sort_order") or 0)
                            or bool(item.get("is_active", True)) != bool(existing.get("is_active", True))
                        )
                        if changed and not can_update_question:
                            return jsonify({"error": "当前账号没有编辑常见问题权限"}), 403
                    elif str(item.get("question_text") or "").strip() and not can_create_question:
                        return jsonify({"error": "当前账号没有新增常见问题权限"}), 403
                if set(existing_questions.keys()) - incoming_existing_ids and not can_delete_question:
                    return jsonify({"error": "当前账号没有删除常见问题权限"}), 403
            cur.execute("DELETE FROM bs_common_questions WHERE dataset_id = %s;", (dataset_id,))
            for idx, item in enumerate(common_questions, start=1):
                question_text = (item.get("question_text") or "").strip()
                if not question_text:
                    continue
                cur.execute(
                    """
                    INSERT INTO bs_common_questions(dataset_id, question_text, sort_order, is_active)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (
                        dataset_id,
                        question_text,
                        int(item.get("sort_order") or idx * 10),
                        bool(item.get("is_active", True)),
                    ),
                )

            if not partial_common_questions:
                cur.execute("DELETE FROM bs_dataset_external_configs WHERE dataset_id = %s;", (dataset_id,))
                for item in external_configs:
                    config_type = (item.get("config_type") or "").strip()
                    config_key = (item.get("config_key") or "").strip()
                    config_value = _parse_json_like(item.get("config_value"), {})
                    if not config_type or not config_key:
                        continue
                    cur.execute(
                        """
                        INSERT INTO bs_dataset_external_configs(
                            dataset_id, config_type, config_key, config_value, is_active
                        )
                        VALUES (%s, %s, %s, %s::jsonb, %s)
                        ON CONFLICT (dataset_id, config_type, config_key)
                        DO UPDATE SET
                            config_value = EXCLUDED.config_value,
                            is_active = EXCLUDED.is_active,
                            updated_at = NOW();
                        """,
                        (
                            dataset_id,
                            config_type,
                            config_key,
                            json_dump(config_value),
                            bool(item.get("is_active", True)),
                        ),
                    )

                cur.execute("DELETE FROM bs_regression_cases WHERE dataset_id = %s;", (dataset_id,))
                for idx, item in enumerate(regression_cases, start=1):
                    question_text = (item.get("question_text") or "").strip()
                    if not question_text:
                        continue
                    cur.execute(
                        """
                        INSERT INTO bs_regression_cases(
                            dataset_id, case_type, question_text, expected_focus, expected_intent, sort_order, is_active
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            dataset_id,
                            (item.get("case_type") or "summary").strip(),
                            question_text,
                            (item.get("expected_focus") or "").strip(),
                            (item.get("expected_intent") or "generate_sql").strip(),
                            int(item.get("sort_order") or idx * 10),
                            bool(item.get("is_active", True)),
                        ),
                    )

            cur.execute("UPDATE bs_datasets SET updated_at = NOW() WHERE id = %s;", (dataset_id,))

        if not partial_common_questions and isinstance(report_config, dict) and report_config:
            report_config_store.upsert_config(dataset_id, report_config)

        return jsonify({"message": "bookshelf content saved", "dataset_id": dataset_id})
    except BookshelfConfigurationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify(
            {
                "error": (
                    "save dataset full failed. "
                    f"If agent_no=1 failed, run migration backend/migrations/20260330_bookshelf_agent1_prompt_upgrade.sql. detail={exc}"
                ),
                "details": [
                    f"详细报错：{exc}",
                    "建议检查：schema_definition.source_id 是否为空字符串或非数字；agent_prompts 是否包含 Agent1-4；golden_sql_samples 是否至少 3 条。",
                    "建议改代码位置：backend/controllers/bookshelf.py::save_bookshelf_dataset_full；保存前校验在 _validate_full_payload。",
                ],
            }
        ), 500


@bookshelf_bp.route("/api/bookshelves/common-questions", methods=["GET"])
def list_common_questions():
    try:
        repo.ensure_schema()
        dataset_id = request.args.get("dataset_id", type=int)
        random_batch = str(request.args.get("random") or "").lower() in {"1", "true", "yes"}
        batch_size = max(1, min(request.args.get("limit", default=4, type=int) or 4, 12))
        user = get_current_user()
        if dataset_id and not dataset_access_summary(user, dataset_id)["can_view"]:
            return jsonify({"common_questions": []})
        allowed_dataset_ids = []
        if not dataset_id:
            with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id FROM bs_datasets WHERE is_active = TRUE ORDER BY updated_at DESC, id DESC;")
                dataset_rows = [dict(row) for row in cur.fetchall()]
            allowed_dataset_ids = [
                int(row["id"])
                for row in filter_dataset_rows_for_user(dataset_rows, user)
                if row.get("id")
            ]
            if not allowed_dataset_ids:
                return jsonify({"common_questions": [], "questions": [], "mode": "random_batch" if random_batch else "list"})
        with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            _ensure_optional_tables(cur)
            if dataset_id:
                cur.execute(
                    """
                    SELECT
                        q.id,
                        q.question_text,
                        q.sort_order,
                        q.dataset_id,
                        d.dataset_name,
                        d.dataset_code,
                        d.business_domain
                    FROM bs_common_questions q
                    JOIN bs_datasets d ON d.id = q.dataset_id
                    WHERE q.dataset_id = %s
                      AND q.is_active = TRUE
                      AND d.is_active = TRUE
                    ORDER BY q.sort_order ASC, q.id ASC
                    LIMIT 50;
                    """,
                    (dataset_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        q.id,
                        q.question_text,
                        q.sort_order,
                        q.dataset_id,
                        d.dataset_name,
                        d.dataset_code,
                        d.business_domain
                    FROM bs_common_questions q
                    JOIN bs_datasets d ON d.id = q.dataset_id
                    WHERE q.is_active = TRUE
                      AND d.is_active = TRUE
                      AND q.dataset_id = ANY(%s::int[])
                    ORDER BY q.updated_at DESC, q.sort_order ASC, q.id ASC
                    LIMIT 200;
                    """,
                    (allowed_dataset_ids,),
                )
            rows = [dict(row) for row in cur.fetchall()]
            shaped_rows = [_shape_common_question(row) for row in rows]
            if random_batch and not dataset_id:
                shaped_rows = [_shape_common_question(row) for row in _pick_random_common_questions(rows, batch_size)]
            else:
                shaped_rows = shaped_rows[:batch_size] if random_batch else shaped_rows
            return jsonify({
                "common_questions": shaped_rows,
                "questions": shaped_rows,
                "mode": "random_batch" if random_batch and not dataset_id else "dataset" if dataset_id else "list",
            })
    except BookshelfConfigurationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"list common questions failed: {exc}"}), 500


@bookshelf_bp.route("/api/bookshelves/datasets/<int:dataset_id>/import-legacy", methods=["POST"])
def import_legacy_to_dataset(dataset_id: int):
    return jsonify({"error": "legacy import has been removed"}), 410


@bookshelf_bp.route("/api/bookshelves/datasets/<int:dataset_id>/cleanup-legacy", methods=["POST"])
def cleanup_legacy_dataset_data(dataset_id: int):
    try:
        repo.ensure_schema()
        payload = request.get_json() or {}
        clear_common_questions = bool(payload.get("clear_common_questions", False))

        cleaned = {
            "golden_sql_samples": 0,
            "common_questions": 0,
            "external_configs": 0,
            "agent_prompts": 0,
        }

        with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            _ensure_optional_tables(cur)
            cur.execute("SELECT id FROM bs_datasets WHERE id = %s;", (dataset_id,))
            if not cur.fetchone():
                return jsonify({"error": f"dataset not found: {dataset_id}"}), 404

            cur.execute("SELECT COUNT(*) AS count FROM bs_golden_sql_samples WHERE dataset_id = %s AND created_by = 'legacy-import';", (dataset_id,))
            cleaned["golden_sql_samples"] = int(cur.fetchone()["count"])
            cur.execute("DELETE FROM bs_golden_sql_samples WHERE dataset_id = %s AND created_by = 'legacy-import';", (dataset_id,))

            cur.execute("SELECT COUNT(*) AS count FROM bs_agent_prompt_fragments WHERE dataset_id = %s AND created_by = 'legacy-import';", (dataset_id,))
            cleaned["agent_prompts"] = int(cur.fetchone()["count"])
            cur.execute("DELETE FROM bs_agent_prompt_fragments WHERE dataset_id = %s AND created_by = 'legacy-import';", (dataset_id,))

            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM bs_dataset_external_configs
                WHERE dataset_id = %s
                  AND (config_key LIKE 'legacy_sync_%%' OR config_key LIKE 'legacy_ai_model_%%');
                """,
                (dataset_id,),
            )
            cleaned["external_configs"] = int(cur.fetchone()["count"])
            cur.execute(
                """
                DELETE FROM bs_dataset_external_configs
                WHERE dataset_id = %s
                  AND (config_key LIKE 'legacy_sync_%%' OR config_key LIKE 'legacy_ai_model_%%');
                """,
                (dataset_id,),
            )

            if clear_common_questions:
                cur.execute("SELECT COUNT(*) AS count FROM bs_common_questions WHERE dataset_id = %s;", (dataset_id,))
                cleaned["common_questions"] = int(cur.fetchone()["count"])
                cur.execute("DELETE FROM bs_common_questions WHERE dataset_id = %s;", (dataset_id,))

            cur.execute("UPDATE bs_datasets SET updated_at = NOW() WHERE id = %s;", (dataset_id,))

        return jsonify({"message": "legacy data cleaned", "dataset_id": dataset_id, "cleaned": cleaned})
    except BookshelfConfigurationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"cleanup legacy failed: {exc}"}), 500


def json_dump(obj: Any) -> str:
    return __import__("json").dumps(obj, ensure_ascii=False)


@bookshelf_bp.route("/api/bookshelves/source-tables", methods=["GET"])
def list_source_tables():
    try:
        source_id = request.args.get("source_id", type=int)
        if not source_id:
            return jsonify({"error": "source_id is required."}), 400

        ds = get_datasource_by_id(source_id)
        if not ds:
            return jsonify({"error": f"datasource not found: {source_id}"}), 404

        ds_type = (ds.get("type") or "").lower()
        if ds_type == "postgresql":
            with psycopg2.connect(
                host=ds.get("host", "localhost"),
                port=int(ds.get("port", 5432) or 5432),
                database=ds.get("database_name", ""),
                user=ds.get("username", ""),
                password=ds.get("password", ""),
                connect_timeout=8,
            ) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_type = 'BASE TABLE'
                      AND table_schema NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY table_schema, table_name;
                    """
                )
                rows = cur.fetchall()
                items: List[Dict[str, Any]] = []
                for row in rows:
                    schema = row["table_schema"]
                    table = row["table_name"]
                    cur.execute(
                        """
                        SELECT column_name, data_type
                        FROM information_schema.columns
                        WHERE table_schema=%s AND table_name=%s
                        ORDER BY ordinal_position;
                        """,
                        (schema, table),
                    )
                    cols = cur.fetchall()
                    ddl_lines = [f'"{c["column_name"]}" {c["data_type"]}' for c in cols]
                    ddl_sql = f'CREATE TABLE "{schema}"."{table}" (\n  ' + ",\n  ".join(ddl_lines) + "\n);"
                    items.append(
                        {
                            "table_schema": schema,
                            "table_name": table,
                            "full_table_name": f"{schema}.{table}",
                            "column_count": len(cols),
                            "ddl_sql": ddl_sql,
                        }
                    )
                return jsonify({"tables": items, "source_id": source_id})

        if ds_type == "sqlite":
            sqlite_path = ds.get("sqlite_path") or ""
            if not sqlite_path:
                return jsonify({"error": "sqlite_path is empty for this datasource."}), 400
            with sqlite3.connect(sqlite_path) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT name AS table_name, sql AS ddl_sql
                    FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name;
                    """
                )
                rows = cur.fetchall()
                items = []
                for row in rows:
                    table = row["table_name"]
                    cur.execute(f'PRAGMA table_info("{table}")')
                    cols = cur.fetchall()
                    items.append(
                        {
                            "table_schema": "main",
                            "table_name": table,
                            "full_table_name": f"main.{table}",
                            "column_count": len(cols),
                            "ddl_sql": row["ddl_sql"] or "",
                        }
                    )
                return jsonify({"tables": items, "source_id": source_id})

        return jsonify({"error": f"unsupported datasource type for table scan: {ds_type}"}), 400
    except Exception as exc:
        return jsonify({"error": f"list source tables failed: {exc}"}), 500
