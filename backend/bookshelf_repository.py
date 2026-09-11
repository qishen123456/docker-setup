import os
import re
from typing import Any, Dict, List

import psycopg2
from psycopg2.extras import RealDictCursor

try:
    from .config_manager import decode_secret, get_default_datasource, get_datasources
except ImportError:
    from config_manager import decode_secret, get_default_datasource, get_datasources


class BookshelfConfigurationError(Exception):
    pass


class BookshelfRepository:
    """Load dataset-isolated Bookshelf metadata from PostgreSQL."""

    def __init__(self):
        pass

    @staticmethod
    def _pick_metadata_datasource() -> Dict[str, Any]:
        default_ds = get_default_datasource()
        if default_ds and default_ds.get("type") == "postgresql":
            return default_ds

        for item in get_datasources():
            if item.get("is_active") and item.get("type") == "postgresql":
                return {
                    **item,
                    "password": item.get("password") or decode_secret(item.get("password_b64", "")),
                }

        raise BookshelfConfigurationError(
            "No active PostgreSQL datasource found. Please configure one in 数据源管理 and set it active."
        )

    def _connect(self):
        datasource = self._pick_metadata_datasource()
        try:
            return psycopg2.connect(
                host=datasource.get("host", "localhost"),
                port=int(datasource.get("port", 5432) or 5432),
                database=datasource.get("database_name", ""),
                user=datasource.get("username", ""),
                password=datasource.get("password", ""),
                connect_timeout=8,
            )
        except UnicodeDecodeError as exc:
            raise BookshelfConfigurationError(
                "PostgreSQL connection failed. Please confirm PostgreSQL service is started and "
                "the datasource host/port/user/password are correct."
            ) from exc
        except Exception as exc:
            raise BookshelfConfigurationError(f"PostgreSQL connection failed: {exc}") from exc

    def ensure_schema(self) -> None:
        migration_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "migrations",
            "20260330_bookshelf_schema.sql",
        )
        if not os.path.exists(migration_path):
            raise BookshelfConfigurationError(f"Migration file not found: {migration_path}")

        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT to_regclass('public.bs_datasets') AS table_name;")
                row = cur.fetchone()
                if row and row.get("table_name"):
                    return

            # End the implicit transaction opened by the existence probe before
            # toggling autocommit for multi-statement schema bootstrap.
            conn.rollback()
            conn.autocommit = True
            with conn.cursor() as cur:
                with open(migration_path, "r", encoding="utf-8") as file:
                    raw_sql = file.read()
                sql_lines = []
                for line in raw_sql.splitlines():
                    marker = line.strip().upper()
                    if marker in ("BEGIN;", "COMMIT;"):
                        continue
                    sql_lines.append(line)
                cur.execute("\n".join(sql_lines))

    def is_ready(self) -> bool:
        sql = """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'bs_datasets'
        ) AS exists;
        """
        try:
            with self._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                row = cur.fetchone()
                return bool(row and row["exists"])
        except Exception:
            return False

    def get_agent1_catalog(self) -> List[Dict[str, Any]]:
        sql = """
        SELECT
            d.id,
            d.dataset_code,
            d.dataset_name,
            d.business_domain,
            d.source_id,
            d.description,
            COALESCE(
                ARRAY_AGG(s.synonym) FILTER (WHERE s.synonym IS NOT NULL),
                ARRAY[]::TEXT[]
            ) AS synonyms
        FROM bs_datasets d
        LEFT JOIN bs_dataset_synonyms s ON s.dataset_id = d.id
        WHERE d.is_active = TRUE
        GROUP BY d.id
        ORDER BY d.id;
        """
        with self._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

    def get_dataset_context(
        self, dataset_id: int, question: str, top_k_samples: int = 5
    ) -> Dict[str, Any]:
        with self._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, dataset_code, dataset_name, business_domain, source_id, description
                FROM bs_datasets
                WHERE id = %s AND is_active = TRUE;
                """,
                (dataset_id,),
            )
            dataset = cur.fetchone()
            if not dataset:
                raise ValueError(f"Dataset not found or inactive: {dataset_id}")

            cur.execute(
                """
                SELECT id, version, title, content, redline_rules
                FROM bs_lld_documents
                WHERE dataset_id = %s AND is_active = TRUE
                ORDER BY version DESC, updated_at DESC
                LIMIT 1;
                """,
                (dataset_id,),
            )
            lld = cur.fetchone() or {}

            cur.execute(
                """
                SELECT table_name, column_name, jsonb_key, semantic_name, data_type, enum_mapping, extraction_rule
                FROM bs_data_dictionary_items
                WHERE dataset_id = %s AND is_active = TRUE
                ORDER BY table_name, column_name;
                """,
                (dataset_id,),
            )
            dictionary_items = [dict(row) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT table_name, ddl_sql, description
                FROM bs_schema_definitions
                WHERE dataset_id = %s AND is_active = TRUE
                ORDER BY table_name;
                """,
                (dataset_id,),
            )
            schema_definitions = [dict(row) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT left_table, left_key, right_table, right_key, relation_type, description
                FROM bs_table_relations
                WHERE dataset_id = %s AND is_active = TRUE
                ORDER BY left_table, right_table;
                """,
                (dataset_id,),
            )
            table_relations = [dict(row) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT id, intent_type, question, sql_text, tags, quality_score, updated_at
                FROM bs_golden_sql_samples
                WHERE dataset_id = %s AND is_active = TRUE
                ORDER BY quality_score DESC, updated_at DESC
                LIMIT 80;
                """,
                (dataset_id,),
            )
            all_samples = [dict(row) for row in cur.fetchall()]
            selected_samples = self._rank_samples(question, all_samples, top_k_samples)

            cur.execute(
                """
                SELECT agent_no, prompt_key, prompt_content
                FROM bs_agent_prompt_fragments
                WHERE dataset_id = %s AND is_active = TRUE
                ORDER BY agent_no, prompt_key;
                """,
                (dataset_id,),
            )
            prompt_rows = [dict(row) for row in cur.fetchall()]

            prompts: Dict[int, List[Dict[str, str]]] = {1: [], 2: [], 3: [], 4: []}
            for item in prompt_rows:
                agent_no = int(item["agent_no"])
                if agent_no not in prompts:
                    prompts[agent_no] = []
                prompts[agent_no].append(
                    {"prompt_key": item["prompt_key"], "prompt_content": item["prompt_content"]}
                )

            cur.execute(
                """
                SELECT question_text, sort_order
                FROM bs_common_questions
                WHERE dataset_id = %s AND is_active = TRUE
                ORDER BY sort_order ASC, id ASC
                LIMIT 30;
                """,
                (dataset_id,),
            )
            common_questions = [dict(row) for row in cur.fetchall()]

            return {
                "dataset": dict(dataset),
                "lld_document": dict(lld),
                "data_dictionary": dictionary_items,
                "schema_definition": schema_definitions,
                "table_relations": table_relations,
                "golden_sql_samples": selected_samples,
                "agent_prompts": prompts,
                "common_questions": common_questions,
            }

    def _rank_samples(
        self, question: str, samples: List[Dict[str, Any]], top_k_samples: int
    ) -> List[Dict[str, Any]]:
        tokens = self._tokenize(question)
        if not samples:
            return []

        if not tokens:
            return samples[:top_k_samples]

        def question_key(value: Any) -> str:
            text = re.sub(r"[\s？?。.!！,，、：:；;（）()]+", "", str(value or "").lower())
            text = re.sub(r"^(请问|帮我|帮忙|麻烦|查一下|看一下|查询|分析一下|我想知道)+", "", text)
            text = re.sub(r"(呢|啊|呀|吗|么|吧)$", "", text)
            # 助词"的"不影响问法同一性（与 four_agent_ask._select_sql_strategy 同口径）
            text = text.replace("的", "")
            text = text.replace("消费者事业部", "").replace("消费事业部", "").replace("消费者", "")
            text = text.replace("商用事业部", "").replace("商用", "")
            return text

        query_key = question_key(question)

        def score(sample: Dict[str, Any]) -> int:
            text_parts = [
                sample.get("question", ""),
                " ".join(sample.get("tags", []) or []),
                sample.get("intent_type", ""),
            ]
            sample_tokens = self._tokenize(" ".join(text_parts))
            overlap = len(tokens.intersection(sample_tokens))
            sample_key = question_key(sample.get("question"))
            exact_hit = 1 if self._normalize_question_key(question) == self._normalize_question_key(sample.get("question")) else 0
            normalized_hit = 1 if sample_key and query_key and sample_key == query_key else 0
            contains_hit = 1 if sample_key and query_key and sample_key != query_key and (sample_key in query_key or query_key in sample_key) else 0
            quality = int(sample.get("quality_score") or 0) // 10
            sql_bonus = self._score_sql_shape(question, sample.get("sql_text") or "")
            coverage = len(sample_tokens) or 1
            overlap_ratio = int((overlap / coverage) * 20)
            return overlap * 12 + overlap_ratio + quality + sql_bonus + exact_hit * 50 + normalized_hit * 90 + contains_hit * 60

        ranked = sorted(samples, key=score, reverse=True)
        selected = []
        for sample in ranked[:top_k_samples]:
            item = dict(sample)
            item["match_score"] = score(sample)
            selected.append(item)
        return selected

    @staticmethod
    def _tokenize(text: str) -> set:
        parts = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{1,4}", (text or "").lower())
        return {item for item in parts if item.strip()}

    @staticmethod
    def _normalize_question_key(text: Any) -> str:
        return re.sub(r"[\s？?。.!！,，、：:；;（）()]+", "", str(text or "").lower())

    @staticmethod
    def _score_sql_shape(question: str, sql_text: str) -> int:
        text = f"{question or ''} {(sql_text or '').lower()}"
        score = 0
        if re.search(r"(趋势|变化|按月|按日|时间|日期)", question or "") and re.search(r"(date|time|month|day)", sql_text or "", re.IGNORECASE):
            score += 8
        if re.search(r"(占比|分布|构成|比例)", question or "") and re.search(r"(group\s+by|count\s*\(|sum\s*\()", sql_text or "", re.IGNORECASE):
            score += 8
        if re.search(r"(top|排名|前\d+|最高|最低|最好|最差|最佳|完成好|完成最好)", question or "", re.IGNORECASE) and re.search(r"(order\s+by|limit|top\s+\d+|row_number|rank\s*\()", sql_text or "", re.IGNORECASE):
            score += 8
        if re.search(r"(明细|列表|记录)", question or "") and re.search(r"select\s+.+from", sql_text or "", re.IGNORECASE):
            score += 4
        if "where" in text:
            score += 2
        return score
