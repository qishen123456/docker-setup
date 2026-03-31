"""
Populate Bookshelf dataset for 商用事业部 with four-agent prompts and DDL context.

Run:
  py -3.11 fill_syyb_dataset.py
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from app import app
from config_manager import get_datasource_by_id, get_datasources, get_default_datasource


DATASET_CODE = "angel_business_2026"
DATASET_NAME = "商用事业部"
BUSINESS_DOMAIN = "安吉尔商用事业部销售业绩分析"


AGENT1_PROMPT = """
你是 Agent1（语义路由与口径守卫）。
任务：识别用户问题对应的数据集与统计口径，必要时触发老板确认。

硬性规则：
1. 仅围绕 angel_group_data（2026年）语义做判断。
2. 如果问题包含“分公司/代表处/业务部/业务代表/条线”且可能产生歧义，必须进入确认流程。
3. 统计上级层级时，必须强调“不含下级明细行”的口径。
4. 涉及“当前年/最新年/本年”统一按 2026。
5. 输出偏好：若样本命中高，优先 direct_execute，否则 generate_sql。
6. 若用户明确指定“东部分公司”，保留该过滤意图并透传给下游Agent。
""".strip()


AGENT2_PROMPT = """
你是 Agent2（SQL生成专家），专门处理飞书多维表格落库到 PostgreSQL 的 JSONB 数据。
只允许输出只读 SQL（SELECT/WITH/SHOW），禁止增删改。

固定上下文：
1. 当前数据库：{database_name}（PostgreSQL）。
2. 仅使用 angel_group_data 表（字段 fields 为 JSONB）。
3. 年份口径固定：2026。

强制生成规则：
1. 必须使用 WITH 结构：字段提取 -> 基础数据 -> 维度汇总。
2. 字段提取必须兼容 JSONB 数组/文本：
   CASE WHEN jsonb_typeof(fields->'字段')='array' THEN fields->'字段'->0->>'text' ELSE fields->>'字段' END
3. 金额字段必须清洗：
   COALESCE(NULLIF(regexp_replace(金额原始,'[^0-9.-]','','g'),''),'0')::NUMERIC
4. 年份过滤必须写死：
   WHERE 当前年 = '2026'
5. 层级隔离必须执行：
   - 代表处统计：代表处<>'' AND (业务代表 IS NULL OR 业务代表='')
   - 分公司/业务部统计：(代表处 IS NULL OR 代表处='') AND (业务代表 IS NULL OR 业务代表='')
   - 业务代表统计：业务代表<>''
6. UNION ALL 合并顺序必须是：
   代表处 -> 分公司 -> 业务代表 -> 业务部 -> 事业部
7. 东部分公司统一过滤：
   WHERE 上级名称='东部分公司' OR 节点名称='东部分公司'
8. 指标算法：
   - 达成率：CASE WHEN SUM(任务)>0 THEN ROUND(SUM(开单)/SUM(任务)*100,2) ELSE 0 END
   - 剩余任务：ROUND(SUM(任务)-SUM(开单),2)
9. 默认排序：
   ORDER BY 条线 DESC, 层级 DESC, 上级名称
10. 必须 LIMIT 100。

字段中文键：
事业部、分公司、代表处、业务代表、当前年、总任务（金额）、年度开单金额

输出要求：
1. SQL 使用中文别名。
2. 不要解释，不要Markdown，不要代码块，只输出SQL正文。
""".strip()


AGENT3_PROMPT = """
你是 Agent3（SQL复核官）。
你要对 Agent2 SQL 进行口径、安全、可执行性复核，并在必要时修正 SQL。

复核清单（全部必须满足）：
1. 只读安全：仅 SELECT/WITH/SHOW。
2. 仅使用 angel_group_data。
3. JSONB 提取是否使用 jsonb_typeof + ->> 兼容数组/文本。
4. 金额是否使用 regexp_replace 清洗非数字字符。
5. 是否包含 当前年='2026' 过滤。
6. 层级隔离是否正确（上级不含下级明细）。
7. UNION ALL 顺序是否符合：
   代表处 -> 分公司 -> 业务代表 -> 业务部 -> 事业部。
8. 达成率、剩余任务金额计算是否正确且避免除零。
9. 是否具备 LIMIT 100。
10. 涉及东部分公司时，过滤条件是否统一：
    上级名称='东部分公司' OR 节点名称='东部分公司'

若发现问题，直接修正为可执行SQL并返回 final_sql。
""".strip()


AGENT4_PROMPT = """
你是 Agent4（业务解读官），面向商用事业部管理层输出结论。

解读要求：
1. 先给结论：目标达成情况、风险层级、优先动作。
2. 分层说明：事业部 -> 条线 -> 分公司/业务部 -> 代表处/业务代表。
3. 重点关注：
   - 达成率偏低节点
   - 剩余任务金额高的节点
   - 东部分公司专项表现
4. 明确给出 2-3 条“可执行动作建议”，语言简洁，避免空话。
5. 所有结论均基于查询结果，不编造数据。
""".strip()


def _pick_postgres_source_id() -> int:
    default_ds = get_default_datasource()
    if default_ds and default_ds.get("type") == "postgresql":
        return int(default_ds["id"])

    for ds in get_datasources():
        if ds.get("is_active") and ds.get("type") == "postgresql":
            return int(ds["id"])

    raise RuntimeError("No active PostgreSQL datasource found.")


def _build_ddl_for_table(source_id: int, table_name: str) -> str:
    ds = get_datasource_by_id(source_id)
    if not ds:
        raise RuntimeError(f"Datasource not found: {source_id}")

    if (ds.get("type") or "").lower() != "postgresql":
        return (
            "CREATE TABLE angel_group_data (\n"
            "  id BIGINT,\n"
            "  fields JSONB\n"
            ");"
        )

    try:
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
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position;
                """,
                (table_name,),
            )
            rows = cur.fetchall()
            if not rows:
                return (
                    "CREATE TABLE angel_group_data (\n"
                    "  id BIGINT,\n"
                    "  fields JSONB\n"
                    ");"
                )

            cols = [f'"{row["column_name"]}" {row["data_type"]}' for row in rows]
            return "CREATE TABLE angel_group_data (\n  " + ",\n  ".join(cols) + "\n);"
    except Exception:
        return (
            "CREATE TABLE angel_group_data (\n"
            "  id BIGINT,\n"
            "  fields JSONB\n"
            ");"
        )


def _dataset_payload(source_id: int, ddl_sql: str) -> Dict:
    return {
        "common_questions": [
            {"question_text": "商用事业部当前年整体达成率是多少？", "sort_order": 10, "is_active": True},
            {"question_text": "东部分公司当前年达成率和剩余任务是多少？", "sort_order": 20, "is_active": True},
            {"question_text": "哪些代表处达成率最低？", "sort_order": 30, "is_active": True},
            {"question_text": "各业务部当前年开单金额排名", "sort_order": 40, "is_active": True},
        ],
        "synonyms": [
            {"synonym": "商用事业部", "normalized_synonym": "商用事业部", "weight": 10},
            {"synonym": "安吉尔商用", "normalized_synonym": "安吉尔商用", "weight": 9},
            {"synonym": "销售业绩", "normalized_synonym": "销售业绩", "weight": 8},
            {"synonym": "东部分公司", "normalized_synonym": "东部分公司", "weight": 8},
        ],
        "lld_documents": [
            {
                "version": 1,
                "title": "飞书多维表格 -> PostgreSQL 智能SQL生成规范（商用事业部）",
                "content": (
                    "核心约束：全中文命名、层级数据隔离（统计上级时不含下级明细）、自动清洗金额、2026年过滤。"
                    "适用场景：安吉尔商用事业部销售业绩分析、层级隔离取数、任务达成率/剩余任务统计。"
                    "主表：angel_group_data，JSONB字段：fields。"
                ),
                "redline_rules": [
                    "必须只读SQL",
                    "必须使用2026年份过滤",
                    "必须执行层级隔离",
                    "必须限制LIMIT 100",
                ],
                "is_active": True,
            }
        ],
        "data_dictionary": [
            {
                "table_name": "angel_group_data",
                "column_name": "fields",
                "jsonb_key": "事业部",
                "semantic_name": "事业部",
                "data_type": "text",
                "enum_mapping": {},
                "extraction_rule": "CASE WHEN jsonb_typeof(fields->'事业部')='array' THEN fields->'事业部'->0->>'text' ELSE fields->>'事业部' END",
                "is_active": True,
            },
            {
                "table_name": "angel_group_data",
                "column_name": "fields",
                "jsonb_key": "分公司",
                "semantic_name": "分公司",
                "data_type": "text",
                "enum_mapping": {},
                "extraction_rule": "CASE WHEN jsonb_typeof(fields->'分公司')='array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END",
                "is_active": True,
            },
            {
                "table_name": "angel_group_data",
                "column_name": "fields",
                "jsonb_key": "代表处",
                "semantic_name": "代表处",
                "data_type": "text",
                "enum_mapping": {},
                "extraction_rule": "CASE WHEN jsonb_typeof(fields->'代表处')='array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END",
                "is_active": True,
            },
            {
                "table_name": "angel_group_data",
                "column_name": "fields",
                "jsonb_key": "业务代表",
                "semantic_name": "业务代表",
                "data_type": "text",
                "enum_mapping": {},
                "extraction_rule": "CASE WHEN jsonb_typeof(fields->'业务代表')='array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END",
                "is_active": True,
            },
            {
                "table_name": "angel_group_data",
                "column_name": "fields",
                "jsonb_key": "当前年",
                "semantic_name": "当前年",
                "data_type": "text",
                "enum_mapping": {},
                "extraction_rule": "CASE WHEN jsonb_typeof(fields->'当前年')='array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END",
                "is_active": True,
            },
            {
                "table_name": "angel_group_data",
                "column_name": "fields",
                "jsonb_key": "总任务（金额）",
                "semantic_name": "总任务金额",
                "data_type": "numeric",
                "enum_mapping": {},
                "extraction_rule": "COALESCE(NULLIF(regexp_replace(CASE WHEN jsonb_typeof(fields->'总任务（金额）')='array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END,'[^0-9.-]','','g'),''),'0')::NUMERIC",
                "is_active": True,
            },
            {
                "table_name": "angel_group_data",
                "column_name": "fields",
                "jsonb_key": "年度开单金额",
                "semantic_name": "年度开单金额",
                "data_type": "numeric",
                "enum_mapping": {},
                "extraction_rule": "COALESCE(NULLIF(regexp_replace(CASE WHEN jsonb_typeof(fields->'年度开单金额')='array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END,'[^0-9.-]','','g'),''),'0')::NUMERIC",
                "is_active": True,
            },
        ],
        "schema_definition": [
            {
                "table_name": "angel_group_data",
                "ddl_sql": ddl_sql,
                "description": "飞书多维表格落库主表，业务字段位于 fields(JSONB)。",
                "is_active": True,
                "source_id": source_id,
            }
        ],
        "table_relations": [],
        "golden_sql_samples": [
            {
                "intent_type": "summary",
                "question": "商用事业部全维度业绩分析（含层级隔离）",
                "sql_text": (
                    "WITH 字段提取 AS ("
                    " SELECT "
                    "CASE WHEN jsonb_typeof(fields->'分公司')='array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END AS 分公司,"
                    "CASE WHEN jsonb_typeof(fields->'代表处')='array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END AS 代表处,"
                    "CASE WHEN jsonb_typeof(fields->'业务代表')='array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END AS 业务代表,"
                    "CASE WHEN jsonb_typeof(fields->'总任务（金额）')='array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END AS 任务原始,"
                    "CASE WHEN jsonb_typeof(fields->'年度开单金额')='array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END AS 开单原始,"
                    "CASE WHEN jsonb_typeof(fields->'当前年')='array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END AS 当前年 "
                    "FROM angel_group_data"
                    "), 基础数据 AS ("
                    " SELECT 分公司,代表处,业务代表,"
                    "COALESCE(NULLIF(regexp_replace(任务原始,'[^0-9.-]','','g'),''),'0')::NUMERIC AS 任务金额,"
                    "COALESCE(NULLIF(regexp_replace(开单原始,'[^0-9.-]','','g'),''),'0')::NUMERIC AS 开单金额,"
                    "CASE WHEN 分公司 LIKE '%分公司' THEN '区域条线' WHEN 分公司 LIKE '%业务部' THEN '行业条线' ELSE '事业部层级' END AS 条线 "
                    "FROM 字段提取 WHERE 当前年='2026'"
                    "), 维度汇总 AS ("
                    " SELECT '区域条线' AS 条线,分公司 AS 上级名称,代表处 AS 节点名称,'代表处' AS 层级,任务金额,开单金额 "
                    "FROM 基础数据 WHERE 代表处<>'' AND (业务代表 IS NULL OR 业务代表='')"
                    " UNION ALL "
                    "SELECT '区域条线','商用事业部',分公司,'分公司',任务金额,开单金额 "
                    "FROM 基础数据 WHERE 分公司 LIKE '%分公司' AND (代表处 IS NULL OR 代表处='') AND (业务代表 IS NULL OR 业务代表='')"
                    " UNION ALL "
                    "SELECT '行业条线',分公司,业务代表,'业务代表',任务金额,开单金额 "
                    "FROM 基础数据 WHERE 业务代表<>''"
                    " UNION ALL "
                    "SELECT '行业条线','商用事业部',分公司,'业务部',任务金额,开单金额 "
                    "FROM 基础数据 WHERE 分公司 LIKE '%业务部' AND (代表处 IS NULL OR 代表处='') AND (业务代表 IS NULL OR 业务代表='')"
                    ") "
                    "SELECT 条线,层级,节点名称,上级名称,"
                    "SUM(任务金额) AS 总任务金额,SUM(开单金额) AS 年度开单金额,"
                    "CASE WHEN SUM(任务金额)>0 THEN ROUND(SUM(开单金额)/SUM(任务金额)*100,2) ELSE 0 END AS 达成率,"
                    "ROUND(SUM(任务金额)-SUM(开单金额),2) AS 剩余任务金额 "
                    "FROM 维度汇总 "
                    "GROUP BY 条线,层级,节点名称,上级名称 "
                    "ORDER BY 条线 DESC,层级 DESC,上级名称 "
                    "LIMIT 100"
                ),
                "tags": ["商用事业部", "层级隔离", "达成率", "UNION ALL"],
                "quality_score": 95,
                "is_active": True,
            }
        ],
        "agent_prompts": [
            {"agent_no": 1, "prompt_key": "default", "prompt_content": AGENT1_PROMPT, "is_active": True},
            {"agent_no": 2, "prompt_key": "default", "prompt_content": AGENT2_PROMPT, "is_active": True},
            {"agent_no": 3, "prompt_key": "default", "prompt_content": AGENT3_PROMPT, "is_active": True},
            {"agent_no": 4, "prompt_key": "default", "prompt_content": AGENT4_PROMPT, "is_active": True},
        ],
        "external_configs": [
            {
                "config_type": "dataset_meta",
                "config_key": "sql_generation_profile",
                "config_value": {
                    "year_fixed": "2026",
                    "main_table": "angel_group_data",
                    "db_type": "postgresql",
                    "jsonb_column": "fields",
                    "readonly": True,
                },
                "is_active": True,
            }
        ],
    }


def _get_or_create_dataset_id(source_id: int) -> int:
    client = app.test_client()
    list_resp = client.get("/api/bookshelves/datasets")
    if list_resp.status_code != 200:
        raise RuntimeError(f"List datasets failed: {list_resp.status_code} {list_resp.get_json()}")

    datasets = (list_resp.get_json() or {}).get("datasets", [])
    for item in datasets:
        if (item.get("dataset_code") or "").strip() == DATASET_CODE:
            update_resp = client.put(
                f"/api/bookshelves/datasets/{item['id']}",
                json={
                    "dataset_name": DATASET_NAME,
                    "business_domain": BUSINESS_DOMAIN,
                    "source_id": source_id,
                    "description": "商用事业部（飞书多维表格）四Agent模板",
                    "is_active": True,
                },
            )
            if update_resp.status_code not in (200, 201):
                raise RuntimeError(f"Update dataset failed: {update_resp.status_code} {update_resp.get_json()}")
            return int(item["id"])

    create_resp = client.post(
        "/api/bookshelves/datasets",
        json={
            "dataset_code": DATASET_CODE,
            "dataset_name": DATASET_NAME,
            "business_domain": BUSINESS_DOMAIN,
            "source_id": source_id,
            "description": "商用事业部（飞书多维表格）四Agent模板",
        },
    )
    if create_resp.status_code not in (200, 201):
        raise RuntimeError(f"Create dataset failed: {create_resp.status_code} {create_resp.get_json()}")
    return int((create_resp.get_json() or {}).get("dataset", {}).get("id"))


def main() -> None:
    source_id = _pick_postgres_source_id()
    dataset_id = _get_or_create_dataset_id(source_id)
    ddl_sql = _build_ddl_for_table(source_id, "angel_group_data")

    payload = _dataset_payload(source_id, ddl_sql)
    client = app.test_client()
    save_resp = client.put(f"/api/bookshelves/datasets/{dataset_id}/full", json=payload)
    if save_resp.status_code not in (200, 201):
        raise RuntimeError(f"Save dataset full failed: {save_resp.status_code} {save_resp.get_json()}")

    print(json.dumps({"ok": True, "dataset_id": dataset_id, "dataset_code": DATASET_CODE}, ensure_ascii=False))


if __name__ == "__main__":
    main()

