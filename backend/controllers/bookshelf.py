"""
Bookshelf management controller (dataset-isolated knowledge + prompts + golden SQL).
"""

from flask import Blueprint, jsonify, request
import os
import sys
import sqlite3
from typing import Any, Dict, List

import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bookshelf_repository import BookshelfConfigurationError, BookshelfRepository
from config_manager import get_default_datasource, get_datasource_by_id, read_json


bookshelf_bp = Blueprint("bookshelf", __name__)
repo = BookshelfRepository()


def _normalize_synonym(value: str) -> str:
    return (value or "").strip().lower()


def _parse_json_like(value: Any, default: Any):
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    return default


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
        include_inactive = str(request.args.get("include_inactive", "")).lower() in ("1", "true", "yes")
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
            return jsonify({"datasets": [dict(row) for row in cur.fetchall()]})
    except BookshelfConfigurationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"list datasets failed: {exc}"}), 500


@bookshelf_bp.route("/api/bookshelves/datasets", methods=["POST"])
def create_bookshelf_dataset():
    try:
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
            return jsonify({"dataset": created}), 201
    except BookshelfConfigurationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"create dataset failed: {exc}"}), 500


@bookshelf_bp.route("/api/bookshelves/datasets/<int:dataset_id>", methods=["PUT"])
def update_bookshelf_dataset(dataset_id: int):
    try:
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
                    "dataset": dict(dataset),
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


@bookshelf_bp.route("/api/bookshelves/datasets/<int:dataset_id>/full", methods=["PUT"])
def save_bookshelf_dataset_full(dataset_id: int):
    try:
        repo.ensure_schema()
        payload = request.get_json() or {}
        validation_errors = _validate_full_payload(payload)
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

        with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            _ensure_optional_tables(cur)
            cur.execute("SELECT id FROM bs_datasets WHERE id = %s;", (dataset_id,))
            if not cur.fetchone():
                return jsonify({"error": f"dataset not found: {dataset_id}"}), 404

            # Keep import idempotent for repeated clicks.
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
                        int(source_id) if source_id is not None else None,
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

        return jsonify({"message": "bookshelf content saved", "dataset_id": dataset_id})
    except BookshelfConfigurationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify(
            {
                "error": (
                    "save dataset full failed. "
                    f"If agent_no=1 failed, run migration backend/migrations/20260330_bookshelf_agent1_prompt_upgrade.sql. detail={exc}"
                )
            }
        ), 500


@bookshelf_bp.route("/api/bookshelves/common-questions", methods=["GET"])
def list_common_questions():
    try:
        repo.ensure_schema()
        dataset_id = request.args.get("dataset_id", type=int)
        with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            _ensure_optional_tables(cur)
            if dataset_id:
                cur.execute(
                    """
                    SELECT question_text, sort_order, dataset_id
                    FROM bs_common_questions
                    WHERE dataset_id = %s AND is_active = TRUE
                    ORDER BY sort_order ASC, id ASC
                    LIMIT 50;
                    """,
                    (dataset_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT question_text, sort_order, dataset_id
                    FROM bs_common_questions
                    WHERE is_active = TRUE
                    ORDER BY updated_at DESC, sort_order ASC
                    LIMIT 80;
                    """
                )
            return jsonify({"common_questions": [dict(row) for row in cur.fetchall()]})
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
